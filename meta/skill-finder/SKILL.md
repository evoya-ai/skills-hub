---
name: skill-finder
description: Find and install Roo skills from the skills hub for this project. Use when a needed capability or skill is missing in the current Zoo.
---

# Skill finder

The skills hub lives at `~/workspaces/skill-hub`. Its sources (personal,
teams, external collections) are listed in its `sources.yml`.

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

Never hand-create a skill in a project when the hub already has one, and
never edit hub content from a project Zoo — edit it in the hub's content
repos instead.
