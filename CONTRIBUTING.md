# Contributing / Build process

This repo is advanced incrementally by an automated builder that:

1. Reads `ROADMAP.md` top-to-bottom.
2. Finds the **first unchecked `- [ ]` item**.
3. Implements exactly that one item, matching the conventions of the target project folder.
4. Runs the project's tests (`pytest -q`) and linter (`ruff check .`).
5. Checks the item off in `ROADMAP.md` and opens a PR.

One item per PR. Never push to `main` directly. Never merge without human review.
