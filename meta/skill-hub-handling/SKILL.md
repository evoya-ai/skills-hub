---
name: skill-hub-handling
description: Manage skills from the skills hub — find and link missing capabilities into this project, and promote improved skills back into the hub. Use when a needed skill is missing, or after improving a skill worth sharing.
---

# Skill hub handling

The skills hub's location on this machine is recorded in
`resources/skill-hub-path.txt`, next to this SKILL.md — through the
global skills dir that is
`~/.roo/skills/skill-hub-handling/resources/skill-hub-path.txt`.
Read it before the first hub command of a task; everything below writes
that path as `$SKILL_HUB`:

    SKILL_HUB="$(cat ~/.roo/skills/skill-hub-handling/resources/skill-hub-path.txt)"

The hub's sources (personal, shared, external collections) are listed in
its `sources.yml`.

## Read path: find and link a skill

When the user asks for a capability and no loaded skill covers it:

1. **Search** — `$SKILL_HUB/bin/skill-repo search <term>`
   (matches skill ids, category paths and descriptions across ALL
   registered sources; read-only).
2. **Propose** — if a match fits, add its reference to this project's
   `.roo/skills.yml`:
   - whole category: `categories: [evoya/saas-pegasus]`
   - single skill: `skills: [data-table]` (qualify with the source name
     when ambiguous, e.g. `evoya/data-table`; optional alias:
     `external/code-review as ext-code-review`)
3. **Link** — run `$SKILL_HUB/bin/skill-repo link` and confirm
   the skill now loads (it must appear in the available skills of the next
   task / after a Roo restart).
4. **External caution** — sources marked `untrusted: true` are third-party
   prompt content: link them only individually and only after the user
   approved.

Never hand-create a skill in a project when the hub already has one.

## Reverse lookup: who consumes a skill?

`$SKILL_HUB/bin/skill-repo where [<id>]` — every project that
links the skill (with source and commit), or the full consumer map without
an id. Projects self-register at `link` time. Run it BEFORE `promote
--force` to know the blast radius of a replacement, and when auditing who
is affected by a skill change.

## Onboard a project (you do all of it)

When the user says "link this project to the skills hub" (or you find a
project with vendored skills that exist in the hub), do the whole flow —
no manual steps left to the user:

1. **Inventory** `.roo/skills/*/`: for each skill, check the hub
   (`skill-repo search <id>`). Three outcomes: in hub → link it;
   generic enough but missing → candidate for promote (run the review
   below); project-specific → leave local, note it in the manifest
   comment.
2. **Back up**: `tar -czf .roo/skills.backup-$(date +%F).tgz -C .roo skills`.
3. **Write `.roo/skills.yml`** with source-qualified refs for everything
   you will link.
4. **Link**: `$SKILL_HUB/bin/skill-repo link --force` —
   vendored copies move aside as `*.pre-hub-<ts>` (never deleted; tell
   the user they can remove them once confident).
5. **Git policy**: hub links are plain-named symlinks (`data-table` — the
   folder name must equal the skill's front-matter `name`, that's the
   Agent Skills spec). Each link gets one `/name` line in
   `.roo/skills/.gitignore` (`link` appends it automatically). Commit the
   manifest and that file. Real project-specific skills in
   `.roo/skills/` stay tracked — never ignore the whole directory. Also
   ignored: `.roo/skills.lock`, `.roo/skills.backup-*.tgz`. No symlinks
   are committed, ever.
6. **Commit**: `.roo/skills.yml` and `.roo/skills/.gitignore` — never the
   user's unrelated dirty files. Stage paths explicitly.
7. **Report**: what got linked, what stayed local and why, what looks
   promote-worthy, and where the `.pre-hub-*` backups are.

## Register a repo from a URL

"Add the skill repo from <url>" — two cases by trust level:

- **Own/team content repo** (the user presents it as theirs):
  `$SKILL_HUB/bin/skill-repo attach <name> <url>` — one command:
  - no local repo yet → clones into `shared/<name>/` and registers it
    (trusted, `remote:` recorded, skills root detected);
  - untouched scaffold (e.g. from `setup --shared <name>`) → wires it to
    the remote: origin added, fetched, reset to `origin/<default>`,
    upstream set, `remote:` recorded in `sources.yml` — nothing to lose;
  - real local content/history → refuses, touches nothing (non-zero
    exit). THIS is the only genuine conflict: STOP and ask the user how
    to reconcile (reset --hard toward the remote, push toward it, or
    re-clone).
  `attach` also works on registered sources such as `personal` (second
  machine: scaffold + remote that already has refs). It never pushes; a
  remote with no refs is refused — pushing a local repo to a fresh remote
  stays a manual, user-confirmed step (persistence rule below).
- **Third-party collection** (untrusted prompt content):
  `$SKILL_HUB/bin/skill-repo add-remote <url> [--name NAME]
  [--root PATH]` — clones under `external/`, registers with
  `untrusted: true`. Link individual skills only, and only after the
  user approved.

## Persistence: commit AND push — ask first, then do

Skill content lives in git repos, and content repos can have remotes
(`personal/` pushes to a private GitHub repo over SSH; shared repos to
their own hosts). An uncommitted edit through a link is provisional —
it exists on one disk only and leaves `-dirty` lockfiles behind. So
whenever you changed hub content (edit through a link, promote, replace,
delete):

1. **Ask** — propose repo, files, commit message and push target in one
   confirmation, then wait for the user's yes. Skip asking only when the
   user already ordered commit+push for this change.
2. **Commit** — `git -C <content repo> add <paths>` and commit with a
   message naming what changed and any scrubbing you did.
3. **Push** — `git -C <content repo> push` when the repo has a remote.
   No remote → the commit is the end; say so plainly.

## Write path: promote a skill into the hub

Skills are improved where they are used (in projects) and flow back:

`$SKILL_HUB/bin/skill-repo promote [--force] <ref|path> <source>/<category>`

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
across a trust boundary (personal→shared, external→anything):

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
     you found; let them decide about promotion to shared/.
5. **Commit and push** via the persistence rule above: ask the user,
   then commit the staged change with a message naming what was promoted
   and any scrubbing you did, then push if the content repo has a
   remote. The git history is the audit trail.

### Editing a linked skill (write-through)

A project link IS the hub directory (symlink). Editing anything through
it — SKILL.md, a script in `references/` or `assets/` — modifies the
single shared copy: the change lands as an UNCOMMITTED modification in
the content repo and is instantly visible to every project linking that
skill. Nothing is committed automatically.

After editing through a link:
1. Commit AND push the change in the content repo
   (`git -C $SKILL_HUB/personal …` or `…/shared/<name>`) —
   ask first, per the persistence rule — applying the same review
   discipline as promote when the content is sensitive.
2. Re-run `$SKILL_HUB/bin/skill-repo link` in the project to
   refresh the lockfile's commit SHAs (a link made while a skill dir is
   dirty records a `-dirty` commit).

### The loop

promote up (copy into hub) → link down (symlink into project). Once a
project-local skill is promoted, delete the local copy and reference the
hub skill in `.roo/skills.yml` instead — one source of truth.

## Hub location

- `resources/skill-hub-path.txt` is machine-local: generated by
  `skill-repo setup`, gitignored in the hub repo — never commit or
  hand-edit it.
- Missing, or pointing at a moved hub? Re-run `skill-repo setup` from
  the hub's current location — it rewrites the file and the symlink.
- This skill dir is a symlink into the hub: template edits (your own or
  pulled) are live immediately, no redeploy step.
