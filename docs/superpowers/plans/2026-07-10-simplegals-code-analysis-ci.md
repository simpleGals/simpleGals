# simpleGals Code-Analysis CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Initial plan (baked from a supervisory assessment of bitmath's code-analysis setup). Four shaping decisions are locked (see Locked Decisions), plus a fix-first suppression policy (see Suppression Policy). Tooling config lands first (Task 1), then the baseline run drives code *fixes* (Task 2), then the resulting conventions are written into `CLAUDE.md` (Task 3).

**Goal:** Bring bitmath's code-analysis discipline into simpleGals: add Bandit (SAST) and pip-audit (SCA) security workflows, add pylint and pycodestyle linting, and update the existing pytest invocation to match bitmath's coverage args. Adopt bitmath's *toolchain and discipline* while explicitly dropping the settings that only exist because bitmath is an old single-file module.

**Architecture:** Additive only, except that Task 2 edits `simplegals/` source to *fix* lint findings rather than suppress them. Config lands in `pyproject.toml` (dev deps + `[tool.pylint.*]`) and the `Makefile` (new `lint` / `security` targets, updated `test` args). Two new SHA-pinned workflow files (`bandit.yml`, `sca.yml`) join the existing set, `ci.yml` gains an advisory `lint` job plus updated pytest args, and `CLAUDE.md` gains a code-style section so future agents write lint-clean code by default.

**Tech Stack:** Python >= 3.10; pylint, pycodestyle, bandit, pip-audit (new dev deps); pytest + pytest-cov (existing). CI on GitHub Actions.

## Locked Decisions

Decided with the user before this plan was written; do not revisit without asking:

1. **Line length: enforce 120.** Set `max-line-length = 120` in pylint and `--max-line-length=120` on pycodestyle. Do NOT port bitmath's blanket `--ignore=E501` / module-wide `line-too-long` disable (its single biggest legacy crutch).
2. **Lint gate: advisory first.** The pylint/pycodestyle job runs with `continue-on-error: true` so it is visible but non-blocking. A follow-up (out of scope here) flips it to a hard gate once findings are triaged.
3. **SCA scope: runtime + dev.** pip-audit audits the real resolved dependency set via an editable install plus `local: true`, not a dev-tools-only `requirements.txt` (bitmath's pattern, which would miss `pillow`, `jinja2`, `piexif`, `term-image`, `urwid`).
4. **Action pinning: SHA-pin the new security workflows.** Every action in `bandit.yml` and `sca.yml` is pinned to a full commit SHA with a `# vX.Y.Z` comment, matching bitmath. Retrofitting the existing `ci.yml`/`publish.yml` floating tags is a separate, out-of-scope follow-up.

## Suppression Policy (fix-first)

This is the core operating rule for Task 2 and overrides the "add narrow commented disables" pattern bitmath uses.

- **Default: fix the code.** For every pylint / pycodestyle / bandit finding, change the code so the check passes cleanly. This is the strongly preferred path.
- **Do NOT pre-seed suppressions.** We start with an empty pylint `disable` list and zero inline `# pylint: disable` / `# noqa` / `# nosec` in the source. simpleGals currently has zero suppressions and we keep it that way as far as is reasonable.
- **Escape hatch (last resort only):** where a fix would "shit everything up unreasonably" (mangle otherwise-clean code, force an unnatural restructure, or fight an opinionated check with no real defect behind it), prefer a single, documented, project-level `[tool.pylint.messages_control]` disable with a one-line reason comment over scattering per-line suppressions. Each such disable is exceptional and must state why fixing was unreasonable. Raise these to the user rather than deciding unilaterally on anything non-obvious.
- **Then teach the memory.** Whatever conventions the fixes establish (line length, no builtin shadowing, argument-count limits, docstring expectations, and so on), write them into `CLAUDE.md` (Task 3) so future agents produce lint-clean code and do not reintroduce the patterns we just cleaned up.

## Global Constraints

- Python >= 3.10. No new *runtime* dependencies; only dev/test additions.
- The full existing suite (~205 tests) must stay green after every Task 2 fix. Fixes are code changes, so re-run tests after each cluster of edits.
- Do NOT port bitmath's legacy-only settings: `max-module-lines = 2000`, the `line-too-long` / `E501` blanket disable, the `good-names` unit-conversion regexes, the Windows/ctypes platform disables, `py-version = "3.12"`, and the dead `pragma: ${PYVER} no cover` coverage line. Rationale: these exist because bitmath is a single ~1,950-line legacy module; simpleGals is a clean multi-module package with zero existing suppressions.
- New workflow files trigger on `main` (not bitmath's `master`), target `simplegals/ tests/` (not `bitmath/`), and omit the `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` shim (simpleGals already runs Node24-native actions).
- `VERSION` is a bare PEP 440 string, no `v` prefix, no trailing newline; this work does not bump it (it is tooling, not a release feature).
- Commits use conventional-commit prefixes (`ci:`, `chore:`, `build:`, `refactor:`, `test:`, `docs:`) to match repo history. Do NOT add any `Co-Authored-By` trailer or Claude/generated-by credit to any commit, PR, or issue.
- Work on a dedicated branch (suggested: `ci/code-analysis`), not `main`.

## Reference: bitmath source, verbatim

Known-good SHA pins observed in bitmath (reuse these where the action matches; resolve `actions/checkout`/`actions/setup-python` to the versions simpleGals already uses if you prefer consistency with the current `ci.yml`, which floats `checkout@v7` / `setup-python@v6`):

- `PyCQA/bandit-action@67a458d90fa11fb1463e91e7f4c8f068b5863c7f` # v1.0.1
- `pypa/gh-action-pip-audit@1220774d901786e6f652ae159f7b6bc8fea6d266` # v1.1.0
- `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd` # v6.0.2
- `actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1` # v6.3.0

bitmath's pytest args (the pattern to match): `pytest -v --cov=bitmath --cov-report term-missing --cov-report term:skip-covered --cov-report xml:coverage.xml tests`

## File Structure

- `pyproject.toml` (modify): add 4 dev deps; add `[tool.pylint.main]` and `[tool.pylint.format]`. A `[tool.pylint.messages_control]` disable table is added ONLY if Task 2's escape hatch is genuinely triggered.
- `simplegals/**` (modify, Task 2): code fixes for lint findings. Scope depends on the baseline run.
- `CLAUDE.md` (modify, Task 3): new code-style section codifying the conventions the fixes establish.
- `Makefile` (modify): add `lint` and `security` targets; update `test` args; extend `.PHONY`.
- `.github/workflows/bandit.yml` (new): SHA-pinned Bandit SAST.
- `.github/workflows/sca.yml` (new): SHA-pinned pip-audit SCA (runtime + dev).
- `.github/workflows/ci.yml` (modify): add an advisory `lint` job; update the test step's pytest args.

---

### Task 1: pyproject.toml dev deps and pylint config (no disables)

**Files:**
- Modify: `pyproject.toml` (dev extras at lines 41-46; add tool tables after the existing `[tool.hatch.*]` tables)

**Interfaces:**
- Produces: `pip install -e ".[dev]"` installs the linters; `pylint simplegals/` and `pycodestyle --max-line-length=120 ...` read a consistent 120-char limit and target 3.10.

- [ ] **Step 1: Add dev dependencies**

Update `[project.optional-dependencies].dev` to:

```toml
dev = [
    "pytest",
    "pytest-cov",
    "build",
    "twine",
    "pylint",
    "pycodestyle",
    "bandit",
    "pip-audit",
]
```

- [ ] **Step 2: Add adapted pylint config (empty disable list)**

Append to `pyproject.toml`. `py-version` matches simpleGals' real floor (3.10, NOT bitmath's 3.12). `max-line-length` is enforced at 120. `max-module-lines` is deliberately omitted so oversized-file signal is preserved. There is NO `[tool.pylint.messages_control]` disable table at this point (fix-first policy):

```toml
[tool.pylint.main]
py-version = "3.10"

[tool.pylint.format]
max-line-length = 120
```

Note: pycodestyle does not read `pyproject.toml`; its `--max-line-length=120` lives on the CLI in the Makefile and workflow (Tasks 4 and 7). Intentional: one line-length value (120) in both tools.

- [ ] **Step 3: Install and confirm the config loads**

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/pylint --help >/dev/null   # config parses without error
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build: add pylint/pycodestyle/bandit/pip-audit dev deps and pylint config"
```

---

### Task 2: Baseline run and fix findings (fix-first)

**Goal:** simpleGals has zero existing suppressions, so run each tool once against HEAD and *fix* what fires. Do not add suppressions as the first move (see Suppression Policy). The escape hatch is a last resort only, and any use of it is surfaced to the user.

**Files:**
- Modify: `simplegals/**` (code fixes)
- Modify (last resort only): `pyproject.toml` `[tool.pylint.messages_control]`

- [ ] **Step 1: Capture the baseline**

```bash
.venv/bin/pylint simplegals/ | tee /tmp/sg-pylint.txt
.venv/bin/pycodestyle --max-line-length=120 simplegals/ tests/ | tee /tmp/sg-pycodestyle.txt
.venv/bin/bandit -r simplegals/ tests/ | tee /tmp/sg-bandit.txt
.venv/bin/pip-audit | tee /tmp/sg-pip-audit.txt
```

- [ ] **Step 2: Fix the findings**

Work through the findings and change the code so each check passes. Likely simpleGals-specific classes to watch for (confirm against the actual output, do not assume): over-120 lines, `redefined-builtin` where an identifier shadows a builtin (for example `format` or `id`), `too-many-arguments` / `too-many-instance-attributes` on TUI widgets, missing docstrings, unused imports/variables, and any Bandit hits on the Jinja2 / EXIF / subprocess / filesystem surface. Fix in small clusters and re-run the relevant tool plus the test suite after each cluster:

```bash
make test      # or: .venv/bin/pytest tests/
```

For any finding where a clean fix is genuinely unreasonable (mangles otherwise-fine code, or an opinionated check with no real defect), STOP and raise it to the user with the specific finding and why. Only then, if agreed, add a single documented project-level disable:

```toml
# [tool.pylint.messages_control]
# disable = [
#     "some-check",  # reason a fix would be unreasonable
# ]
```

- [ ] **Step 3: Confirm clean (or clean-with-documented-exceptions)**

```bash
.venv/bin/pylint simplegals/
.venv/bin/pycodestyle --max-line-length=120 simplegals/ tests/
.venv/bin/bandit -r simplegals/ tests/
make test
```

Expected: pylint and pycodestyle exit 0 on `simplegals/`, Bandit reports no issues (or only user-approved exceptions), and the full suite stays green.

- [ ] **Step 4: Commit (one or more focused commits)**

```bash
git add -A
git commit -m "refactor: resolve pylint/pycodestyle/bandit findings across simplegals"
```

Record the list of finding classes you fixed; Task 3 turns them into `CLAUDE.md` guidance.

---

### Task 3: Codify conventions in CLAUDE.md

**Goal:** So future agents (and future us) write lint-clean code by default and do not reintroduce the patterns Task 2 just cleaned up.

**Files:**
- Modify: `CLAUDE.md` (add a code-style section)

- [ ] **Step 1: Add a "Code Style and Linting" section**

Derive the bullets from what Task 2 actually fixed. Keep it short and concrete. Template:

```markdown
## Code Style and Linting

Code must pass `make lint` (pylint + pycodestyle) and `make security` (bandit + pip-audit)
before commit. The lint job in CI is currently advisory; treat it as a gate anyway.

Conventions (enforced by pylint/pycodestyle, so agents should follow them up front):
- Max line length is 120 characters.
- Do not shadow Python builtins with parameter or variable names (for example `format`, `id`, `type`).
- <add each convention Task 2 established, for example argument-count limits, docstring expectations>

Prefer fixing a lint finding over suppressing it. Do not add `# pylint: disable`, `# noqa`,
or `# nosec` comments, and do not add entries to pyproject's pylint `disable` list, without
explicit sign-off; simpleGals intentionally ships with zero inline suppressions.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add code-style and linting conventions to CLAUDE.md"
```

---

### Task 4: Makefile lint, security, and updated test targets

**Files:**
- Modify: `Makefile`

**Interfaces:**
- Produces: `make lint`, `make security`, and a `make test` whose args match bitmath's coverage pattern. Local runs mirror CI (bitmath's `ci-*` discipline).

- [ ] **Step 1: Extend `.PHONY` and add targets**

Update the `.PHONY` line to include `lint security` and add:

```make
lint:
	$(VENV)/bin/pycodestyle --max-line-length=120 simplegals/ tests/
	$(VENV)/bin/pylint simplegals/

security:
	$(VENV)/bin/bandit -r simplegals/ tests/
	$(VENV)/bin/pip-audit
```

- [ ] **Step 2: Update the `test` target args to match bitmath**

Replace the `test` recipe with:

```make
test:
	$(VENV)/bin/pytest -v --cov=simplegals --cov-report term-missing --cov-report term:skip-covered --cov-report xml:coverage.xml tests
```

- [ ] **Step 3: Verify locally (should be clean after Task 2)**

```bash
make test
make lint
make security
```

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "chore: add lint/security make targets and match bitmath pytest args"
```

---

### Task 5: Bandit SAST workflow

**Files:**
- New: `.github/workflows/bandit.yml`

- [ ] **Step 1: Create the workflow (SHA-pinned, targets `main` and `simplegals/ tests/`)**

```yaml
---
name: Bandit Security Scan

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]
  schedule:
    - cron: "0 0 * * 0"
  workflow_dispatch:

permissions: read-all

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - name: Checkout code
        uses: actions/checkout@<SHA> # v7.x  (resolve to the version ci.yml uses)

      - name: Perform Bandit Analysis
        uses: PyCQA/bandit-action@67a458d90fa11fb1463e91e7f4c8f068b5863c7f # v1.0.1
        with:
          targets: "simplegals/ tests/"
```

Notes:
- `PyCQA/bandit-action` uploads SARIF to GitHub code scanning itself; `security-events: write` is required. Code scanning is already enabled on this repo (the existing `codeql.yml` uploads SARIF), so the upload will succeed.
- If Task 2 surfaced test-only Bandit noise (for example `assert` usage in `tests/`) that was addressed differently than production code, decide whether to keep `tests/` in `targets` or scan `simplegals/` only. Record the choice.

- [ ] **Step 2: Verify SHA pins resolve, then commit**

```bash
git add .github/workflows/bandit.yml
git commit -m "ci: add SHA-pinned Bandit SAST workflow"
```

---

### Task 6: pip-audit SCA workflow

**Files:**
- New: `.github/workflows/sca.yml`

- [ ] **Step 1: Create the workflow (audits runtime + dev via editable install + local mode)**

```yaml
---
name: SCA Security Scan

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]
  schedule:
    - cron: "0 0 * * 0"
  workflow_dispatch:

permissions: read-all

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@<SHA> # v7.x  (resolve to the version ci.yml uses)

      - name: Set up Python
        uses: actions/setup-python@<SHA> # v6.x  (resolve to the version ci.yml uses)
        with:
          python-version: "3.12"

      - name: Install project (runtime + dev)
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Audit installed dependencies with pip-audit
        uses: pypa/gh-action-pip-audit@1220774d901786e6f652ae159f7b6bc8fea6d266 # v1.1.0
        with:
          local: true
```

Notes:
- `local: true` audits the current environment, so the editable install of `.[dev]` means the resolved set (runtime `pillow`/`jinja2`/`piexif`/`term-image`/`urwid`/`bitmath` plus the dev toolchain) is what gets audited. This directly implements the runtime + dev decision, unlike bitmath's `inputs: requirements.txt`.
- No ignore list is configured, so a single flagged transitive dep hard-fails the job. If the weekly scheduled run later trips on a dev-only advisory, add a documented `ignore-vulns` entry rather than removing the gate.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/sca.yml
git commit -m "ci: add SHA-pinned pip-audit SCA workflow"
```

---

### Task 7: Advisory lint job in ci.yml and pytest arg update

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: a non-blocking `lint` check on every push/PR, and a test step whose coverage args match bitmath.

- [ ] **Step 1: Update the existing test step args**

Replace the `Run tests` step's `run:` (line 21) with:

```yaml
      - name: Run tests
        run: pytest -v --cov=simplegals --cov-report term-missing --cov-report term:skip-covered --cov-report xml:coverage.xml tests
```

- [ ] **Step 2: Add an advisory lint job**

Add a third job (alongside `test` and `docs`). `continue-on-error: true` makes it visible but non-blocking (the advisory decision); a later follow-up removes that line to make it a hard gate. After Task 2 the code is already clean, so this should pass, but we keep it advisory per the locked decision until the gate is formally flipped:

```yaml
  lint:
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - name: Install package and dev dependencies
        run: pip install -e ".[dev]"
      - name: pycodestyle
        run: pycodestyle --max-line-length=120 simplegals/ tests/
      - name: pylint
        run: pylint simplegals/
```

Note: `ci.yml` keeps its floating tags (`@v7`, `@v6`) for internal consistency; SHA-pinning is scoped to the new security workflows only (locked decision 4).

- [ ] **Step 3: Verify YAML and commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add advisory lint job and match bitmath pytest args"
```

---

### Task 8: Verify end-to-end

- [ ] **Step 1: Push the branch and open a draft PR to `main`**

- [ ] **Step 2: Confirm in the Actions tab**
  - "Bandit Security Scan" runs, scans `simplegals/ tests/`, completes clean.
  - "SCA Security Scan" log lists the runtime packages (`pillow`, `jinja2`, `piexif`, `term-image`, `urwid`, `bitmath`), proving it audited the intended set.
  - CI's `lint` job appears and passes (it is advisory, so non-blocking either way), and the `test` job shows the new coverage reports.
  - `push`/`pull_request` triggers actually fired on `main` (not silently dead from a stale `master` filter).

- [ ] **Step 3: Confirm the memory landed** so the "flip to hard gate" follow-up starts from a documented, lint-clean baseline: `make lint` is green and `CLAUDE.md` describes the conventions.

---

## Out of scope (follow-ups)

- Flipping the lint job from advisory to a hard gate (remove `continue-on-error`), now backed by a lint-clean baseline and documented conventions.
- Retrofitting SHA pins onto the existing `ci.yml` / `publish.yml`.
- Adding a coverage fail-under threshold or a `[tool.coverage.*]` / `.coveragerc` exclusion set for the interactive `sgui` entry point (bitmath's analog to `# pragma: no cover` on `cli_script`). Worth doing, but not requested here.
- Type checking (mypy/pyright): bitmath has none; it would be net-new config, not a port.
- OSSF Scorecard (`scorecard.yml`): bitmath has one; optional to add later.
