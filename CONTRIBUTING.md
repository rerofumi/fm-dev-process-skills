# Contributing to FM Dev Process Skills

Thank you for your interest in improving FM Dev Process. Contributions that make the workflow clearer, more grounded, and easier to verify are welcome.

## Before making a change

- For a behavior change, open an issue or discussion first when practical. Describe the problem, the affected roles and workflow stages, and the intended outcome.
- Check the current development-source documents in [`docs/develop_document/`](docs/develop_document/00_index.md) and the packaged skills in [`skills/`](skills/).
- Keep proposals scoped to the reported problem. Do not introduce mandatory quality targets, workflow stages, or tools without a clear rationale.

## Keep sources and packaged skills aligned

The development documents describe the process; the `skills/` tree is the packaged, runnable instruction set. When changing a rule:

1. Identify every affected role and shared reference.
2. Update the source document and corresponding packaged skill/reference where applicable.
3. Check internal Markdown links and confirm that every referenced file is included.
4. Review the relevant `SKILL.md` frontmatter and agent metadata for consistency with the role.
5. Update [`docs/develop_document/UPDATE.md`](docs/develop_document/UPDATE.md) when the change belongs in the process history.

Do not turn optional utilities into prerequisites for the core skills unless that requirement is explicitly designed and documented.

## Validation and pull requests

- Run checks relevant to the files you changed. For the optional Python helper, exercise the affected command paths and report the exact commands and observed results; do not claim tests that were not run.
- For workflow changes, include concrete scenarios covering the affected roles, expected handoffs, saved records, and failure or blocked paths where relevant.
- In the pull request, summarize the motivation, behavioral change, affected files/roles, validation performed, and any known limitations.
- Preserve the distinction between implemented work, observed evidence, and independent acceptance.

Japanese and English contributions are welcome. Please keep technical identifiers, file names, and state values exact.

## Scope

This repository provides skills and process guidance. It does not guarantee that every agent runtime supports subagents, shared files, or the same skill-discovery conventions. Document runtime-specific assumptions and limitations rather than presenting them as universal behavior.
