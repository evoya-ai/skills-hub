# Spec: Meta skill deployment v3 — symlink + generated path file

- Date: 2026-09-15
- Status: implemented + tested (124/124), deployed on the origin machine
- Supersedes: the interim render + post-merge-hook approach built earlier today
  (rendered copy in `~/.roo/skills`, `setup --meta-only`, `install_post_merge_hook`)

## Decision

- `~/.roo/skills/skill-hub-handling` is a **symlink** into `<hub>/meta/skill-hub-handling`
  again (original design): skill content always tracks the repo, no hooks, no staleness
  on pulls or template edits.
- The machine-local hub path lives in **one generated file inside the skill dir**:
  `<hub>/meta/skill-hub-handling/resources/skill-hub-path.txt` (absolute path, one
  line). Because the skill dir is reached through the symlink, the SKILL.md references
  it **relatively** — Agent-Skills-convention for supporting files — so no client- or
  location-specific bootstrap is needed.
- The path file is machine-local: gitignored in the hub repo (same class of file as
  `sources.yml`, `.link-roots`), rewritten on every `setup` run. It only goes stale
  when the hub moves — which requires re-running setup anyway.

## Changes

### 1. `bin/skill-repo`

- Rewrite `install_meta_skill()`:
  1. `mkdir -p <hub>/meta/skill-hub-handling/resources`
  2. write `printf '%s\n' "$HUB" > resources/skill-hub-path.txt` (idempotent rewrite)
  3. `ensure_hub_gitignore 'meta/skill-hub-handling/resources/skill-hub-path.txt'`
  4. symlink `~/.roo/skills/skill-hub-handling` → hub dir (relative target via
     `realpath --relative-to`, as the original code did), with:
     - existing symlink → `ln -sfn` refresh
     - existing dir containing our `.rendered-by-skill-repo` marker (interim build
       migration) → `rm -rf` + symlink
     - anything else foreign → warn, skip unless `--force` moves it aside
- Add tiny helper `ensure_hub_gitignore()`: touch `.gitignore`, append the line if
  `grep -qxF` misses; no-op when the hub is not a git repo (test fixtures).
- Delete: `install_post_merge_hook()` + its call, the `--meta-only` flag and its
  short-circuit in `cmd_setup`, and restore the `usage()` setup line.

### 2. `meta/skill-hub-handling/SKILL.md`

- Intro becomes the bootstrap instruction: the hub root is recorded in
  `resources/skill-hub-path.txt` next to this SKILL.md; read it first; commands below
  write it as `$SKILL_HUB`.
- All `{{SKILL_HUB_ROOT}}/bin/skill-repo …` occurrences become
  `$SKILL_HUB/bin/skill-repo …` (and the `git -C {{SKILL_HUB_ROOT}}/personal` one).
- Replace the "This copy is generated" section with a short "Hub location" note:
  path file written by `setup`; missing/stale (hub moved) → re-run setup in the hub.

### 3. `README.md`

- Setup block: renders → "installs the global skill-hub-handling skill as a symlink
  and records the local hub path in its resources/skill-hub-path.txt".
- Layout tree: meta line → "the ONE global skill — symlinked into ~/.roo/skills;
  its resources/skill-hub-path.txt (gitignored) pins the local hub path".
- Requirements: GNU `realpath` needed for `setup`/`link` again (relative symlink
  target) — revert the earlier narrowing.
- Drop the post-merge-hook paragraph.

### 4. `tests/test-skill-repo.sh`

- Header comment: rendered copy → symlink + path file.
- `t22` rewritten: symlink deployed (not a dir), path file contains `$HUB`,
  SKILL.md references `resources/skill-hub-path.txt`, template edits are visible
  through the deployed symlink WITHOUT re-running setup, and a pre-existing rendered
  copy (marker dir) migrates to a symlink.
- `t23` unchanged (foreign-dir guard still applies to the symlink installer).
- `t24` new: with the fixture hub as a git repo, `.gitignore` gains exactly one line
  for the path file, idempotent across setups; without git (plain fixture), no
  `.gitignore` is created; path file rewritten on re-setup after manual corruption.
- Remove `t25`/`t26` (hook tests — the hook no longer exists).

### 5. Verification

1. `bash -n bin/skill-repo`
2. full suite green
3. run `bash bin/skill-repo setup` on this machine: rendered copy → symlink,
   path file written, `.gitignore` line added
4. sanity: `ls -la ~/.roo/skills/skill-hub-handling`, `cat <hub>/meta/.../resources/skill-hub-path.txt`,
   `cat` the file through the deployed symlink

## Compatibility (Linux + macOS, KISS)

- Only portable primitives: `ln -sfn`, `printf`, `grep -qxF`, `mv`, `touch`.
- `realpath --relative-to` is the one GNU-ism — pre-existing, documented requirement
  (macOS: coreutils), same as `link`.
- No hooks, no `sed -i`, no `mktemp` staging; bash ≥ 3.2 safe (no bash-4 syntax).
