# Spec — Lazy shared repos & `skill-repo attach`

- Date: 2026-09-14
- Status: proposed (pending approval)
- Files in scope: `bin/skill-repo`, `sources.template.yml`, `meta/skill-hub-handling/SKILL.md`, `README.md`, `tests/test-skill-repo.sh` (new), `.gitignore`
- Source: dev feedback (evaluated and confirmed) + gap list from the evaluation

## 1. Problem

`setup` eagerly scaffolds `shared/evoya` via the `DEFAULT_SHARED` fallback and
`sources.template.yml` ships evoya as an active entry. The scaffold is a git repo
with one unrelated commit (`init: skills repo scaffold`) and no origin. When the
real remote is registered later:

- the agent flow ("Register a repo from a URL") hits the "existing local repo +
  existing remote refs → STOP and ask" branch, and
- `update`'s `pull --ff-only` can never reconcile the unrelated history — the only
  remedies are a manual `git reset --hard` or re-clone.

The hub must be organization-agnostic: evoya is one possible shared repo, not a
default.

## 2. Goals / Non-goals

**Goals**

1. `setup` scaffolds `personal/` only, unless a shared repo is explicitly requested
   (`--shared <name>[=<url>]`).
2. New command `attach <name> <url>` wires a source dir to its real remote
   (trusted, no `untrusted` flag): clone if missing, adopt an untouched scaffold,
   refuse real content without side effects.
3. Close the evaluated gaps: README/usage docs, `remote:` recorded at
   registration, clean-tree guard, branch-name following, name-collision guard,
   migration notes, `attach` usable for registered sources (incl. `personal`).
4. Bash test suite covering the acceptance criteria and the guards.

**Non-goals**

- No changes to `app/` (web UI).
- No push, merge or rebase operations anywhere in `attach`.
- No auto-pruning of `sources.yml` entries (stays a documented manual edit).
- No interactive prompts in the CLI.

## 3. Changes

### 3.1 `bin/skill-repo` — setup: personal/ only by default

- Delete `DEFAULT_SHARED="evoya"` and the fallback
  `if [ "${#shared_specs[@]}" -eq 0 ]; then shared_specs=("$DEFAULT_SHARED"); fi`.
- `ensure_repo` stays as is (clone with URL, scaffold without).
- The `--team` legacy alias keeps working (still appends to `shared_specs`).

### 3.2 `sources.template.yml` — evoya becomes a commented example

```yaml
sources:
  - name: personal
    path: personal
    root: skills
  # shared repos = more sources (created via `setup --shared <name>[=<url>]`
  # or wired later via `skill-repo attach <name> <url>`):
  # - name: evoya
  #   path: shared/evoya
  #   root: skills
  #   remote: ssh://git@example.com/evoya/evoya-skills
  # - name: insign
  #   path: shared/insign
  #   root: skills
  ...external examples unchanged...
```

Consequence (verified): the template-merge loop in `cmd_setup` no longer
re-registers evoya on machines that removed it; `build_index` stops warning about
a missing `shared/evoya`.

### 3.3 `bin/skill-repo` — `registry_append` gains `remote` (gap 2)

- `registry_append <name> <path> [remote]` writes an optional
  `    remote: <url>` line after `root:`.
- `cmd_setup` passes the URL for `--shared name=url` specs, so a one-step clone is
  fully registered AND `update` actually pulls it (`cmd_update` skips sources
  without `remote:`).

### 3.4 `bin/skill-repo` — new command `attach <name> <url>`

Usage: `skill-repo attach <name> <url>` (run in the hub). Trusted shared/own
repos — never writes `untrusted: true`, never pushes.

**Name/path resolution**

- Validate `name` against `^[a-z0-9][a-z0-9._-]*$` (no slashes → no path escape;
  same spirit as `add-remote`'s sanitization).
- If `name` is registered in `sources.yml` → use its registered `path`
  (this makes `attach personal <url>` work — gap 7). If that entry already has a
  `remote:` → `die "source '<name>' already attached to <remote>"` (gap 5).
- If not registered → path defaults to `shared/<name>`.

**Branch: dir missing**

- Registered name + missing dir → `die` with hint (fix or remove the
  `sources.yml` entry).
- Unregistered name → `git clone <url> "$HUB/shared/<name>"`; root detection like
  `add-remote` (`skills/` exists → `root: skills`, else `root: .`); append entry
  `name, path: shared/<name>, root, remote: <url>` (trusted).

**Branch: dir exists — must be a git repo, else `die`.**

- If it already has ANY remote (`git remote` non-empty) → `die` (already wired).

**Scaffold predicate `is_untouched_scaffold <dir>`** (all must hold):

1. no remotes at all (`git -C <dir> remote` empty),
2. clean working tree (`git status --porcelain` empty) — gap 3,
3. exactly one commit (`git rev-list --count HEAD` == 1),
4. its subject is `init: skills repo scaffold` (the message becomes a behavioral
   contract — add a code comment at `ensure_repo` saying so),
5. no `SKILL.md` anywhere under the dir (excluding `.git`) — `skills/` empty.

**Wire case (predicate passes) — nothing to lose, no confirmation:**

```bash
git -C "$dir" remote add origin "$url"
git -C "$dir" fetch origin            # failure → die, report origin was added
git -C "$dir" remote set-head origin --auto 2>/dev/null || true
# default branch resolution:
#   1) symbolic-ref refs/remotes/origin/HEAD
#   2) exactly one refs/remotes/origin/* branch
#   3) origin/main, then origin/master
#   4) else die, listing available branches
git -C "$dir" branch -m "$default_branch"        # rename local branch if it differs
git -C "$dir" reset --hard "origin/$default_branch"
git -C "$dir" branch --set-upstream-to="origin/$default_branch" "$default_branch"
```

- Empty remote (fetch ok, no refs) → `die "remote has no refs — nothing to
  attach; pushing a local repo to a fresh remote is a manual, user-confirmed
  step"`. Report that `origin` was already added.
- Registry: registered entry → insert `    remote: <url>` after its `root:` line
  (awk rewrite via temp file; re-validate with `parse_sources` afterwards);
  unregistered → append the full entry.
- Print a summary: branch, HEAD sha, upstream, registry state.

**Refusal case (predicate fails): real content/history**

- `die` (exit 1, non-zero per feedback), touch nothing. Message offers the
  manual remedies (`git remote add origin … && git fetch && git reset --hard
  origin/<branch>`, or re-clone) — this is the only case that remains a genuine
  stop-and-ask in the skill flow.

### 3.5 `bin/skill-repo` — `usage()`

Add: `attach <name> <url>   (in hub) wire a shared/own repo to its real remote —
clone if missing, adopt an untouched scaffold, refuse real content`.

### 3.6 `meta/skill-hub-handling/SKILL.md` — "Register a repo from a URL"

Replace the own/team bullet with (third-party `add-remote` part unchanged):

```markdown
- **Own/team content repo** (the user presents it as theirs):
  `~/workspaces/skill-hub/bin/skill-repo attach <name> <url>` — one command:
  - no local repo yet → clones into `shared/<name>/` and registers it (trusted),
  - untouched scaffold → wires it to the remote (fetch, reset, upstream),
  - real local content/history → refuses and touches nothing. THIS is the only
    genuine conflict: STOP and ask how to reconcile (reset --hard, push, re-clone).
  Attach never pushes; a remote with no refs is refused — pushing to a fresh
  remote stays a manual, user-confirmed step (persistence rule).
```

### 3.7 `README.md`

- Setup section: drop "scaffolds personal/ + shared/evoya/"; document the
  one-line team onboarding `./bin/skill-repo setup --shared evoya=ssh://…`
  (clone + register) and `--shared <name>` (empty scaffold), plus `attach`.
- Command table: add `attach <name> <url>` row; refresh the `setup` row.
- Migration note (gap 6): machines that ran the old setup keep a scaffolded
  `shared/<name>` + registry entry — `skill-repo attach <name> <url>` converts
  it; a registered entry whose dir was deleted is removed by editing
  `sources.yml` by hand (no auto-pruning by design).

### 3.8 Tests — `tests/test-skill-repo.sh` (new)

- Pure bash, `set -euo pipefail`; helper `check <cond> <label>` + failure count.
- Fixture hub per test group: copy `bin/skill-repo`, `sources.template.yml`,
  `meta/` into `tests/.tmp/<case>/hub/`; `HOME` overridden to the fixture (so the
  global-skill symlink lands there). No network: remotes are `file://` bare repos
  seeded from a work repo.
- Temp space lives under `tests/.tmp/` (add to `.gitignore`); script cleans up
  via `trap` (any leftovers are removed with a printed command, not silently).

Test matrix:

| # | Scenario | Expectation |
|---|---|---|
| T1 | fresh `setup` | `personal/` exists, `shared/` absent, sources.yml lists only personal, `search foo` prints no warnings |
| T2 | `setup --shared evoya=file://…` (remote has content) | cloned; sources.yml entry has `remote:`; skill found by search; `update` succeeds |
| T3 | `setup --shared demo` (scaffold) then `attach demo file://…` | origin set; HEAD sha == origin/main sha; upstream set; sources.yml has `remote:`; `update` succeeds (ff-only) |
| T4 | `attach` on repo with real local commits | non-zero exit; no origin added; sources.yml unchanged |
| T5 | `attach` on dirty scaffold (uncommitted edit) | non-zero exit; nothing changed |
| T6 | remote default branch is `trunk` | local branch follows; HEAD == origin/trunk |
| T7 | `attach` for a name already registered WITH remote | non-zero exit, no side effects |
| T8 | `attach personal file://…` (scaffold + registered + remote has refs) | personal wired (gap 7) |
| T9 | `attach newname file://…`, dir missing | clone + full registry entry incl. `remote:` |
| T10 | `attach` to empty remote (bare, no commits) | non-zero exit; message points at push flow |
| T11 | registered name but dir missing | non-zero exit; hint about sources.yml |
| T12 | `usage` / `--help` | lists `attach` |
| T13 | template after change | `parse_sources` on template yields only `personal` |

## 4. Gap closure map

| Gap | Closed by |
|---|---|
| 1 README/usage stale | 3.5, 3.7 |
| 2 `remote:` not recorded on clone-time registration | 3.3 |
| 3 dirty scaffold destroyed by reset | predicate item 2 (3.4) |
| 4 branch-name mismatch | default-branch resolution + `branch -m` (3.4) |
| 5 name collision / double attach | registry guard in name resolution (3.4) |
| 6 migration of existing machines | README note (3.7); scaffold → `attach` |
| 7 `attach personal` (second machine) | registered-name path resolution (3.4) |

## 5. Acceptance criteria

Original feedback, verbatim intent:

1. Fresh hub: `setup` creates `personal/` only; sources.yml lists only personal;
   search/link run warning-free.
2. `setup --shared evoya=ssh://…` clones and registers evoya in one step —
   **including `remote:`** so `update` pulls it.
3. Scaffolded dir + `attach evoya ssh://…` → local == `origin/main`, upstream
   set, `remote:` recorded, `skill-repo update` succeeds (still ff-only).
4. `attach` against a repo with real local commits fails without side effects.

Extended by the gap closures: T1–T13 green; docs (README, SKILL.md, usage)
consistent with behavior.

## 6. Decisions & rationale

- **D1** `attach` resolves the dir from the registry when the name is registered,
  else `shared/<name>` — one mechanism covers shared repos and `personal`.
- **D2** `attach` never pushes (clone/fetch/reset are local or read-only remote
  ops) — remote writes stay under the ask-first persistence rule.
- **D3** Tests use `file://` remotes and a fixture hub with overridden `HOME`;
  everything stays under the project root (`tests/.tmp/`, gitignored).
- **D4** Refusals are plain `die` (exit 1, non-zero); no interactivity.
- **D5** The scaffold commit message `init: skills repo scaffold` is now a
  behavioral contract consumed by `is_untouched_scaffold` — documented in code.

## 7. Migration notes (out of implementation scope, documented only)

- Machines with an old scaffolded `shared/evoya`: run `attach evoya <url>`.
- This machine still has the legacy `teams/evoya` directory (pre-`shared/`
  layout); converting it is a manual, user-driven step, not part of this change.
