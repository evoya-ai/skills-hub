# Skills Hub

One clone → all your Roo skills, selected per project, from **personal**,
**team**, and **external** sources. Each project declares which skills it
needs in `.roo/skills.yml` and gets them as symlinks — no more skill copies
drifting across `.roo` folders, and no prompt pollution from skills a
project doesn't use.

## Layout

```
skill-hub/                    # this repo (bootstrap: docs, CLI, templates)
├── bin/skill-repo            # the CLI
├── meta/skill-hub-handling/   # the ONE global skill (symlinked into ~/.roo/skills by setup)
├── sources.template.yml      # registry template
├── sources.yml               # machine-local registry (gitignored, created by setup)
├── personal/                 # your private skills repo (gitignored here, own git repo)
├── teams/<team>/             # one shared skills repo per team (gitignored here, own git repo)
└── external/<collection>/    # clones of third-party skill repos (gitignored here)
```

The content repos (`personal/`, `teams/*`, `external/*`) are independent git
repositories, deliberately gitignored by this repo. Skills live at
`skills/<category>/<skill>/SKILL.md` inside each content repo; the scanner
also handles foreign layouts (any category depth) for external collections.

## Quickstart

```bash
git clone git@github.com:evoya-ai/skills-hub.git ~/workspaces/skill-hub
cd ~/workspaces/skill-hub
./bin/skill-repo setup          # scaffolds personal/ + teams/evoya/, writes sources.yml,
                                # installs the global skill-hub-handling skill. Idempotent.
```

Per project:

```yaml
# <project>/.roo/skills.yml  (commit this file)
source: evoya                  # optional default source for unqualified entries
categories:
  - evoya/saas-pegasus         # link a whole category
skills:
  - data-table                 # single skill (unqualified: must be unique)
  - external/awesome/code-review as ext-code-review   # alias on collision
exclude:
  - seo/seo-drift              # subtract from selection
```

```bash
~/workspaces/skill-hub/bin/skill-repo link        # creates .roo/skills/<name> symlinks + .roo/skills.lock
```

Recommended per-project `.gitignore`: `.roo/skills/` and `.roo/skills.lock`
(commit only the manifest).

## CLI

| Command | Purpose |
|---|---|
| `setup [--personal <url>] [--team <name>[=<url>]]` | scaffold/clone content repos, seed `sources.yml`, install skill-hub-handling |
| `link [--prune] [--force] [--allow-untrusted]` | manifest → symlinks (idempotent; `--prune` removes stale hub links) |
| `search <term>` | find skills across all registered sources |
| `list` | show this project's links + drift vs manifest |
| `verify` | check registry, links, frontmatter uniqueness |
| `update` | fetch + ff-only pull for sources with a `remote` |
| `add-remote <url> [--name N] [--root P]` | register an external collection (marked untrusted) |
| `promote [--force] <ref\|path> <source>/<category>` | copy a skill (any dir with `SKILL.md`, or a hub ref) into a content repo: literal content scan, staged via git (never commits); `--force` replaces via git history (disk backup only for uncommitted changes) |

## Trust classes

- `personal/` — private, never leaves your machine unless you choose a
  private remote.
- `teams/<team>/` — shared via the team's own git remote. Moving a skill
  personal → team crosses a trust boundary: **review for secrets, tokens
  and machine-specific absolute paths before pushing.**
- `external/*` — untrusted third-party prompt content. `link` refuses bulk
  category selection from untrusted sources (individual skills only, unless
  `--allow-untrusted`).

## ⚠ Read this before running git clean

**`git clean -fdX` (or `-fdx`) inside this repo deletes ALL ignored content —
including `personal/` and `teams/*` clones, with uncommitted work.** Recovery
is only via the content repos' remotes and your backups. Never `git add -f`
inside this repo either.

## Status

Phase 2 done (2026-09-13): scaffold + CLI v1 smoke-tested, content repos
seeded. Skill migration (phase 3) is in progress; its local, gitignored
working area lives in `migration/` (handoff doc, spec, audit report) —
start at `migration/HANDOFF.md` if that folder exists on this machine.
The spec will be promoted into `meta/` once stabilized.
