import { TEXTOS } from "@/lib/i18n";
import type { Idioma } from "@/lib/types";

// Port de la pantalla previa al login en ui/app.py (st.link_button +
// radio de idioma en la sidebar) -- acá el idioma se elige ANTES de
// entrar a Cognito (queda en el link de login), no después, porque no
// hay session_state de servidor donde guardarlo mientras se espera el
// round-trip -- Next.js no necesita ese truco: el idioma vuelve intacto
// como ?idioma= en el redirect de api/main.py::callback.
export function LoginScreen({ idioma }: { idioma: Idioma }) {
  const t = TEXTOS[idioma];

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8 text-center">
      <div>
        <h1 className="text-3xl font-semibold text-primary">Telos</h1>
        <p className="mt-1 text-sm text-foreground/70">{t.caption}</p>
      </div>

      <div className="flex gap-2 text-sm">
        {(["en", "es"] as const).map((opcion) => (
          <a
            key={opcion}
            href={`?idioma=${opcion}`}
            className={`rounded-full px-3 py-1 ${idioma === opcion ? "bg-primary text-primary-foreground" : "bg-surface"}`}
          >
            {opcion === "es" ? "Español" : "English"}
          </a>
        ))}
      </div>

      <a
        href={`/api/auth/login?idioma=${idioma}`}
        className="rounded-full bg-primary px-6 py-2 text-sm font-medium text-primary-foreground"
      >
        {t.login_button}
      </a>
    </main>
  );
}
