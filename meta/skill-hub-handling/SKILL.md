---
name: skill-hub-handling
description: Manage skills from the skills hub — find and link missing capabilities into this project, and promote improved skills back into the hub. Use when a needed skill is missing, or after improving a skill worth sharing.
---

# Skill hub handling

The skills hub lives at `~/workspaces/skill-hub`. Its sources (personal,
teams, external collections) are listed in its `sources.yml`.

## Read path: find and link a skill

When the user asks for a capability and no loaded skill covers it:

1. **Search** — `~/workspaces/skill-hub/bin/skill-repo search <term>`
   (matches skill ids, category paths and descriptions across ALL
   registered sources; read-only).
2. **Propose** — if a match fits, add its reference to this project's
   `.roo/skills.yml`:
   - whole category: `categories: [evoya/saas-pegasus]`
   - single skill: `skills: [data-table]` (qualify with the source name
     when ambiguous, e.g. `evoya/data-table`; optional alias:
     `external/code-review as ext-code-review`)
3. **Link** — run `~/workspaces/skill-hub/bin/skill-repo link` and confirm
   the skill now loads (it must appear in the available skills of the next
   task / after a Roo restart).
4. **External caution** — sources marked `untrusted: true` are third-party
   prompt content: link them only individually and only after the user
   approved.

Never hand-create a skill in a project when the hub already has one.

## Reverse lookup: who consumes a skill?

`~/workspaces/skill-hub/bin/skill-repo where [<id>]` — every project that
links the skill (with source and commit), or the full consumer map without
an id. Projects self-register at `link` time. Run it BEFORE `promote
--force` to know the blast radius of a replacement, and when auditing who
is affected by a skill change.

## Write path: promote a skill into the hub

Skills are improved where they are used (in projects) and flow back:

`~/workspaces/skill-hub/bin/skill-repo promote [--force] <ref|path> <source>/<category>`

- `<ref|path>`: the skill dir to move up — a project path
  (`.roo/skills/foo`) or a hub ref (`personal/marketing/foo`).
- promote **copies real files** into the hub content repo and stages them.
  Copy (not symlink) is deliberate: the hub must be self-contained so
  content survives archived/deleted projects and works for every clone.
  The reverse direction is the symlink: projects link back to the hub.
- promote prints content findings (credential literals, real emails,
  public IPs, `/home/` paths) and the commit command. It never commits.

### Mandatory review before promote — YOU are the control

The user trusts the agent operating this tool; there is no later human
review step doing the checking for you. Before promoting — especially
across a trust boundary (personal→team, external→anything):

1. **Address every finding promote prints.** Fix or scrub, re-run until
   findings are zero or each one is consciously justified. Never promote
   over unexplained findings.
2. **Review semantically — the built-in scan is literal-only and cannot
   see meaning.** Check for:
   - real person names, personas, role names, and real email addresses
     (replace with generic roles like `writer`/`scanner` and
     `user@example.com`)
   - company/team terms that do not belong in the TARGET repo — one
     team's or person's company words must never leak into another
     team's repo
   - project-specific paths, domains, hostnames, ports, or repo names
     hardcoded from the source project — genericize or refuse
   - secrets of any shape: tokens, API keys, connection strings, `.env`
     content, private URLs with credentials
3. **Qualitative gate — is this worth hub space?**
   - **Generic and reusable:** would the skill make sense in a DIFFERENT
     project without edits? Project-specific workflows (one repo's
     pipeline, one client's process) stay in their project.
   - **Clean of project-specifics:** paths, domains, URLs, file layouts,
     Makefile targets and conventions from the source project must be
     genericized — or the skill is not ready for the hub.
   - **Metadata properly set:** `description` present, meaningful and
     specific (it is the search index); frontmatter `name` equals the
     directory id; version bumped if overwriting; author field sane for
     the TARGET repo (no other team's or person's company name).
4. **When in doubt, promote to `personal/` first** and tell the user what
     you found; let them decide about team promotion.
5. **Commit** the staged change with a message naming what was promoted
     and any scrubbing you did. The git history is the audit trail.

### Editing a linked skill (write-through)

A project link IS the hub directory (symlink). Editing anything through
it — SKILL.md, a script in `references/` or `assets/` — modifies the
single shared copy: the change lands as an UNCOMMITTED modification in
the content repo and is instantly visible to every project linking that
skill. Nothing is committed automatically.

After editing through a link:
1. Commit the change in the content repo
   (`git -C ~/workspaces/skill-hub/personal …` or `…/teams/<team>`),
   applying the same review discipline as promote when the content is
   sensitive.
2. Re-run `~/workspaces/skill-hub/bin/skill-repo link` in the project to
   refresh the lockfile's commit SHAs (a link made while a skill dir is
   dirty records a `-dirty` commit).

### The loop

promote up (copy into hub) → link down (symlink into project). Once a
project-local skill is promoted, delete the local copy and reference the
hub skill in `.roo/skills.yml` instead — one source of truth.
