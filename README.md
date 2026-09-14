# Skills Hub

One place for every agent skill you own. Instead of copies drifting through
project after project, each skill lives here once, and projects borrow it by
symlink.

The audit that started this found **161 copies of 73 skills** on one machine.
Same skills, slightly different versions, none of them aware of the others.
That is how a fix made in one project quietly never reaches the other five.

The hub ends that. Edit a skill once, every project that links it gets the
change. Commit, and you also get a history of what changed and when.

It is client-independent: a skill is just a directory with a `SKILL.md`, and
the hub links it into whatever convention your agent client reads. Zoo Code
(formerly Roo Code) is the first — links land in `.roo/skills/`, which is why
that path shows up below. OpenCode is the likely next one; adding a client
means pointing it at the same directories, not forking the hub.

## How it works

Two directions, one loop:

- **Down:** a project declares what it needs in `.roo/skills.yml`, and
  `skill-repo link` turns each entry into a symlink. The lockfile
  (`.roo/skills.lock`) records which exact state of the hub you got.
- **Up:** when you improve a skill inside a project, `skill-repo promote`
  copies it back into the hub, scans it for secrets and stray personal data,
  and stages it for commit.

You will rarely type these yourself. The global `skill-hub-handling` skill
teaches your agent the whole loop — search, link, promote, review — including
the checklist it must run before promoting anything across a trust boundary.
You say "we need a data-table skill here" or "push this improvement back",
the agent drives.

The commands, for the record:

| Command | Purpose |
|---|---|
| `search <term>` | find skills across all registered sources |
| `link [--prune] [--force]` | manifest → symlinks + lockfile (idempotent) |
| `promote [--force] <ref\|path> <source>/<category>` | copy a skill into a content repo, scan + stage it — commit is yours |
| `where [<id>] [--prune]` | reverse lookup: which projects link a skill |
| `list` / `verify` | this project's links, drift, frontmatter sanity |
| `setup` / `update` / `add-remote` | hub bootstrap, ff-only pulls, register external collections |

## Setup

```bash
git clone <hub-url> ~/workspaces/skill-hub
cd ~/workspaces/skill-hub
./bin/skill-repo setup          # scaffolds personal/ + teams/evoya/, writes sources.yml,
                                # installs the global skill-hub-handling skill. Idempotent.
```

Per project, commit a manifest and link once:

```yaml
# <project>/.roo/skills.yml  (commit this file)
source: evoya                  # optional default for unqualified entries
categories:
  - evoya/saas-pegasus         # link a whole category
skills:
  - data-table                 # single skill (must be unique, or qualify)
  - personal/design/ui-demo    # source-qualified
exclude:
  - seo/seo-drift              # subtract from the selection
```

```bash
~/workspaces/skill-hub/bin/skill-repo link
```

Recommended per-project `.gitignore`: `.roo/skills/` and `.roo/skills.lock`
(links and lockfile are machine state; the manifest is the source of truth).

## Layout

```
skill-hub/                    # this repo (bootstrap: docs, CLI, templates)
├── bin/skill-repo            # the CLI (bash, no dependencies)
├── meta/skill-hub-handling/  # the ONE global skill (symlinked into ~/.roo/skills)
├── sources.template.yml      # registry template
├── sources.yml               # machine-local registry (gitignored)
├── personal/                 # your private skills repo (gitignored here, own git)
├── teams/<team>/             # one shared skills repo per team (gitignored here)
└── external/<collection>/    # clones of third-party skill repos (gitignored)
```

Content repos are independent git repositories, deliberately invisible to
this one. Skills live at `skills/<category>/<skill>/SKILL.md`; the scanner
also handles foreign layouts for external collections.

## Trust rules, in short

- `personal/` never leaves your machine unless you give it a private remote.
- `teams/<team>/` is shared via that team's own remote. Anything crossing
  personal → team passes a review first: secrets, real emails, company terms,
  machine-specific paths. The promote checklist in `skill-hub-handling` is
  the control; the agent operating it owns that check.
- `external/*` is untrusted prompt content. Bulk-linking from it is refused;
  individual skills only, and only after a human said yes.

## One warning worth its own heading

Do not run `git clean -fdX` in this repo. The content repos live in gitignored
paths, and that command will delete them without asking. Recovery is possible
only via remotes and backups — better to never need either.
