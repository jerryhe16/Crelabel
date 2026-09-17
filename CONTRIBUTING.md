# Contributing to Crelabel

Please read `AGENTS.md` and `HANDOFF.md` before making changes. Those files are the shared contract for humans, Codex, Grok, and other coding agents.

## Workflow

1. Create a branch from the latest `main`: `codex/<task>`, `grok/<task>`, or `feature/<task>`.
2. Record the task owner, scope, and expected files in `HANDOFF.md`.
3. Keep each change focused and add or update regression coverage.
4. Run the checks listed in `AGENTS.md`.
5. Open a Pull Request containing the change summary, test evidence, and anything not physically verified.

Do not commit installers, printer drivers, compiled output, Feishu caches, access tokens, local configuration, customer data, or print records. Never publish an installer or update the Feishu release document without the user's explicit confirmation.

