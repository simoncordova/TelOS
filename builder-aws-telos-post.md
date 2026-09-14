# Building Telos: A Build Journey for AWS Agents for Humans

Before writing a single prompt, I looked into why this needed to exist at
all. In Peru, where I'm building from, 40% of people aged 18-24 report
clinical-level mental health difficulties (Sapien Labs' Global Mind
Project), only 25% of workers are engaged with their jobs (Gallup's State
of the Global Workplace), and 8 out of 10 people with a diagnosable mental
health condition never receive treatment — there's fewer than 1
psychiatrist per 100,000 people against a WHO-recommended 5. That's not a
gap a chatbot should try to fill with therapy. It's a gap where a
well-scoped, self-guided tool can genuinely help someone find and act on a
sense of purpose, as long as it's honest about what it is and isn't.

I spent the last stretch of the **AWS Agents for Humans** hackathon (Everyday
Agents track) building **Telos** — a conversational agent that walks someone
from "I don't really know what I'm working toward" to a concrete life purpose
and a small, sustainable weekly system for living it. Five agents, one
conversation, no dashboards pretending to know you better than you know
yourself.

This is the story of how it got built: the architecture, the AWS services
that ended up doing the real work, and the bugs that only showed up once a
real person sat down and actually used it.

## What Telos does

Telos runs a person through four fixed phases and a fifth, ongoing one:

1. **Explorer** — open-ended conversation to surface what actually matters to
   the person, not a personality quiz.
2. **Synthesizer** — turns that conversation into 2-3 concrete purpose
   candidates, presented as real UI cards, not a wall of prose.
3. **Validation Coach** — pressure-tests the chosen purpose against real past
   evidence before anyone commits to it.
4. **Systems Strategist** — converts an abstract purpose into a 4-question
   actionable system (what, when/where, how you'll know, what gets in the
   way).
5. **Follow-up** — lightweight, recurring check-ins once the system exists.

Routing between phases is 100% deterministic code, never an LLM deciding
where to send someone next. The agents only handle the conversation; a plain
orchestrator decides what happens after.

## The architecture

- **Strands Agents SDK** (Python) for all five agents, each its own `Agent`
  with its own system prompt, running on **Amazon Bedrock** (Claude Sonnet
  4.5).
- **Amazon Bedrock AgentCore Memory** for persistence — both the structured
  "ficha" (purpose + system, versioned, never overwritten) and full
  turn-by-turn conversational history, so a session that drops mid-phase can
  resume with real context instead of just a summary.
- **Amazon Cognito** (Hosted UI) for login — no public self-signup, three
  vetted test accounts for the demo.
- **Amazon EC2 + Amazon CloudFront** hosting a FastAPI backend and a
  Next.js/TypeScript frontend behind one HTTPS domain, no CORS.
- **Amazon EventBridge** (Rule + API destination) + a scheduled job hitting a
  protected API endpoint for real browser push reminders, delivered via a
  Service Worker and `pywebpush`.
- **AWS CDK** (Python) for all of the above as code, plus an `AWS::Budgets::Budget`
  with email alarms as a last line of defense.

## The guardrail had to be real, not a sentence in a prompt

Given the subject matter, a crisis-detection guardrail wasn't optional, and it
couldn't live as a paragraph in a system prompt hoping the model behaves. It's
a small, deterministic, non-LLM function the orchestrator runs on *every*
turn, before any agent sees the message:

```python
# tools/crisis.py
def detectar_señal_crisis(texto: str) -> dict:
    """Returns {"disparado": bool, "categoria": str | None}."""
```

It checks curated pattern lists in **both** languages the app supports,
regardless of which language the UI is currently set to — because that's a
safety property, not a preference, and it should fire the same way whether
someone writes something serious in their selected language or not. Later,
when I added Amazon Bedrock Guardrails as a second layer (denied topics +
content filters, to keep the app inside its actual purpose), I checked
first whether its content filter categories overlapped with self-harm
detection — they don't, so the two layers stay genuinely independent instead
of one silently subsuming the other.

## Five agents that don't know they're five agents

An early real-user test surfaced something I hadn't designed for: the agents
were *narrating their own handoffs* — "now I'll pass you to the Synthesizer,"
"let me shift roles." The routing itself was already 100% deterministic code
and had been from day one; the actual bug was that the prompts kept
describing that routing out loud. It broke the illusion of one continuous
conversation. The fix was a shared rule across all five prompts forbidding
any agent from naming another agent, another phase, or a "handoff" — even
implicitly. It had to feel like talking to one person the whole way through.

## The bug that looked like Bedrock being flaky

For a while, agents would occasionally return empty text, and I was treating
it as Bedrock being probabilistic — retry once, fall back to a static
message if it happened again. It worked, but it was masking the real cause:
every prompt instructs the agent to "write your message, *then* call the
tool." When it does exactly that, Strands produces two assistant messages in
a single invocation — the real text plus the tool call, and then a second
message after the tool result that's almost always empty because the model
already said everything it needed to. `str(result)` in Strands returns only
the *last* generated message by design — which meant the real, well-formed
text from a step earlier was getting silently discarded every time an agent
followed the exact order the prompt asked for. The fix was to stop trusting
`str(result)` and instead walk `Agent.messages` and concatenate every
assistant message from that invocation.

## AgentCore Memory's eventual consistency, twice

Two separate bugs traced back to the same root cause. First: a phase would
close cleanly, the agent would say it saved, and the app would just... sit
there, because the orchestrator re-reads the ficha right after saving to
decide whether to advance, and that read can land before AgentCore Memory's
own write is visible yet. With the local JSON backend this never happened
(synchronous disk write), which is exactly why it hadn't shown up earlier.
Fix: a short bounded retry loop on the re-read, verified against a fake
backend that deliberately returns stale data for the first two reads.

Second, related but distinct: "the model said it saved" isn't the same fact
as "the tool that saves actually ran." I now stamp a real save from inside
the tool body itself into a per-turn container, and if the generated text
*sounds* like a closing confirmation but that stamp never got set, the
orchestrator forces a retry with an unambiguous instruction instead of
trusting the prose.

## When a Python dict isn't a payload

A `TypeError: string indices must be integers` on the very first phase
transition, traced to `create_blob_event` accepting whatever object you hand
it — I was passing a raw Python dict, assuming the SDK serialized it.
AgentCore Memory stores it fine either way, but `list_events` gives you back
a plain string on read, not a dict, so indexing it like one blows up one
step later. `tools/ficha_agentcore.py` now serializes to JSON before writing
and parses on read, with a fallback for the handful of records that had
already been written the wrong way before the fix landed.

## Protecting real AWS spend on a demo app

Before pointing this at real user traffic, the question that mattered most
wasn't "does it work" — it was "what happens if a test account (or a leaked
password) sends messages without limit." Four independent layers, because no
single one felt sufficient on its own: a per-user daily invocation cap
enforced in code before Bedrock is ever touched; the compute layer capped at
a single running instance with no autoscaling to abuse; the Bedrock IAM
policy scoped to the three specific statements AWS documents for
cross-region inference profiles on the exact model in use, not a wildcard
`resources=["*"]`; and an `AWS::Budgets::Budget` with an email alarm as the
backstop if everything else somehow failed.

## The hosting pivot nobody plans for

The first real `cdk deploy` against the account failed creating the App
Runner service: `"The AWS Access Key Id needs a subscription for the
service"`. Not an IAM problem, not a CDK problem — App Runner has no free
tier, and the account was still on Free Tier credits without a verified
payment method. Rather than open an AWS Support case and wait, I moved
hosting to a `t3.micro` EC2 instance (genuinely free-tier) behind
CloudFront for automatic HTTPS — required because Cognito's hosted login
won't accept a plain HTTP callback URL. CloudFront here isn't fronting an S3
bucket the way a typical SPA setup would; Telos is a stateful Python server,
not static files, so CloudFront's job is purely to terminate TLS in front of
EC2.

That same instance later resurfaced a second, unrelated infra lesson: EC2
user data only runs on first boot, so updating a CloudFormation parameter
(like the real callback URL) doesn't make an already-running instance pick
it up — Cognito had the new value, the container kept serving the old one.
Setting `user_data_causes_replacement=True` made any user-data change force
an instance replacement, so the two always stay in sync on the same deploy.

## EventBridge Scheduler's fine print

Building real push notifications meant a genuinely scheduled job, and this
is where `cdk synth` couldn't have caught the problem — the generated
CloudFormation was syntactically valid, but `AWS::Scheduler::Schedule`
rejected it at creation time with `"Provided Arn is not in correct
format"`. EventBridge Scheduler's own docs on "universal targets" read as
though an API destination is a valid direct target; in practice it isn't.
The working pattern is the older, plainer one: a classic EventBridge
`Rule` with an `ApiDestination` target, which turned out simpler anyway —
the L2 construct generates and attaches the invocation role itself instead
of it being hand-assembled.

Push notifications were also the actual reason Telos left Streamlit for a
FastAPI + Next.js stack at all — not aesthetics, but a hard technical wall:
Streamlit can't register a Service Worker (a long-open, unresolved issue
upstream), and without one there's no way to deliver a browser push
notification, period.

## Finding bugs that only exist in a real browser

Running the new frontend in an actual browser for the first time (not
`curl`, which never executes client-side JS) turned up something no earlier
test could have: without an explicit rewrite of `/api/*` to the backend,
every fetch call from the Next.js dev server in local development was
hitting the dev server itself instead of the API — 404 across the board.
In production CloudFront quietly resolves this by routing paths correctly,
so it had been masking a genuinely broken local dev experience for anyone
testing outside a terminal. Small fix in `next.config.ts`; the kind of bug
that only surfaces once you stop trusting a passing test suite as proof the
app actually works.

## The Synthesizer guard: structured output isn't negotiable

Post-launch, real users exposed a gap: the Synthesizer's instructions to
call `presentar_candidatos_proposito` weren't always being followed, even
though the prompt was explicit. The model would write three purpose
candidates as prose in the chat message, but skip the tool call — leaving
the card UI selector empty, since it needs structured data to render. The
fix was a production guard in the orchestrator: detect empty candidates
after the first attempt, then retry the Synthesizer with
`structured_output_model=ListaCandidatosProposito`, which forces Bedrock's
own tool-call machinery into play. The retry handles both cases — direct
tool calls that now succeed, and structured output captured as a fallback
— so the UI always gets the data it needs. The guard includes detailed
logging to distinguish "tool call succeeded" from "fallback to structured
output," making it auditable in production logs.

A related one, found from container logs instead of guessing from
screenshots: a streaming endpoint sent its final "done" event from a
`finally` block, without distinguishing "the turn actually finished" from
"the client disconnected mid-stream." Python won't let you send data while a
generator is closing that way — in practice, a per-user lock meant to
serialize a person's own requests stayed held until garbage collection
eventually got to it, silently hanging every subsequent request from that
same user until a proxy timeout fired.

## Refining the purpose-selector UI: constraints force clarity

Once the Synthesizer started reliably delivering structured candidates,
user feedback revealed that long explanatory text was overwhelming in a
card-based UI. Each candidate had three fields (phrase, explanation,
example), and users were drowning in prose before they could click. The
fix came from enforcing hard length limits: phrase ≤15 words, explanation
≤100 characters, example ≤120 characters. This forced the Synthesizer's
prompts to be rewritten into four explicit steps (read ficha, build
candidates, call tool, write frame), with each step's scope clearly marked
and length budgets unmissable. The UI followed: smaller fonts, reduced
padding, truncation with ellipsis, and visual hierarchy that makes each
field scannable in two seconds. The constraint wasn't aesthetic — it was
cognitive. Shorter fields meant each card became a quick, legible choice
instead of a reading task.

## What I'd tell another builder

- **Test against a real browser, a real account, and real people as early as
  possible.** Nearly every serious bug in this project — the streaming
  deadlock, the eventual-consistency race, the CloudFront timeout, the
  narrated handoffs — was invisible to unit tests and only showed up once a
  real person clicked through the actual flow.
- **`cdk synth` proves your CloudFormation is valid, not that the service
  will accept it.** Two separate AWS services (App Runner, EventBridge
  Scheduler) only revealed their real constraints at `cdk deploy` time,
  against the account, not before.
- **A guardrail that lives only in a prompt isn't a guardrail.** Anything
  safety-critical — crisis detection, spend limits, per-user rate limits —
  went into deterministic code the model can't talk its way around. The same
  principle applies to agentic guarantees: a Synthesizer that "should" call
  a tool isn't reliable without a production guard that forces it, retry
  with structured output if needed.
- **When you already picked a managed AWS service, look for the native
  feature before reaching for a new one.** AgentCore Memory's event API was
  already the right tool for resumable conversation history; reaching for a
  DynamoDB table alongside it would have been reinventing something already
  built in.
- **Constraints in prompts aren't just nice-to-have instructions.** When
  length budgets, step breakdowns, and field limits are explicit in the
  prompt, the model and the UI can both rely on them. Short fields don't
  just look better — they force the Synthesizer's reasoning itself to be
  concise and grounded.

Telos is still evolving — persistence and the follow-up agent moved from
"nice to have" to P0/P1 priorities mid-build, and there's a public,
build-in-public changelog tracking every milestone as it lands. If you're
building for **AWS Agents for Humans** too, I hope some of these traps save
you a night of log-diving.
