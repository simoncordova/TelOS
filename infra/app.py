#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.telos_stack import TelosStack

app = cdk.App()
TelosStack(app, "TelosStack")
app.synth()
