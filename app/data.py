"""Dummy data for the Skills Hub UI prototype.

Shapes deliberately mirror what the real scanner will produce later:
  - sources            <- sources.yml        (name, path, root, remote, untrusted)
  - skills             <- skills/<cat>/<skill>/SKILL.md frontmatter
  - projects           <- .link-roots + each project's .roo/skills.lock
  - local skills       <- real (non-.hub) directories in .roo/skills/

Swap this module for a real scanner and the API stays identical.
When the real wiring lands, this file becomes data_real.py's fallback.
"""

import hashlib

HUB_REMOTE = "git@github.com:evoya-ai/skills-hub.git"


def _commit(seed):
    """Stable pseudo commit hash per skill id — dummy variety (m6)."""
    return hashlib.sha1(seed.encode()).hexdigest()[:7]


def _markdown(source, category, name, desc):
    """Dummy SKILL.md body — exercises headings, lists, tables, code, quotes."""
    fm = (
        "---\n"
        f"name: {name}\n"
        f"description: >-\n  {desc.split('.')[0]}.\n"
        "---\n\n"
    )
    when = [
        "the task matches the description above, not just the keywords",
        "you would otherwise re-explain the same setup from scratch",
        "the conventions below matter more than personal preference",
    ]
    code_flavored = any(
        k in category for k in ("pegasus", "camunda", "tools", "infrastructure", "engineering", "data")
    )
    # hero in the UI already shows name + description; don't repeat them in the body
    body = "## When to use\n\n"
    body += "".join(f"- {w}\n" for w in when)
    if code_flavored:
        body += (
            "\n## How it works\n\n"
            "Wire it in once, then let the conventions carry the weight:\n\n"
            "```python\n"
            "from skills import registry\n\n"
            f"registry.register({name!r})(\n"
            "    requires=[],               # declare dependencies, never import-hidden state\n"
            "    idempotent=True,           # re-runs must be safe\n"
            ")\n"
            "```\n\n"
            "> Edit through the link, not around it: change it in one project and\n"
            "> every consumer gets it — then commit in the hub repo.\n\n"
            "## Options\n\n"
            "| Option | Default | Notes |\n"
            "|---|---|---|\n"
            "| `strict` | `false` | fail on warnings instead of continuing |\n"
            "| `dry_run` | `false` | print the plan, touch nothing |\n"
            "| `context` | `.` | root the relative paths here |\n\n"
            "## Checklist before you ship\n\n"
            "1. Run with `dry_run` first.\n"
            "2. Read the diff — the tool is opinionated, you are the taste.\n"
            "3. Commit in the *hub* repo so history keeps up.\n"
        )
    else:
        body += (
            "\n## The loop\n\n"
            "1. **Diagnose** — skim the material and mark what actually matters.\n"
            "2. **Draft** — produce the artifact, unpolished but complete.\n"
            "3. **Cut** — remove everything that does not earn its place.\n"
            "4. **Check** — run the self-check below before handing it over.\n\n"
            "## Self-check\n\n"
            "| Signal | You are done when… |\n"
            "|---|---|\n"
            "| Focus | one read tells the whole story |\n"
            "| Tone | sounds like a person, not a template |\n"
            "| Length | nothing left to cut without losing meaning |\n\n"
            "> The checklist is the control, not the goal. If everything passes\n"
            "> but it still reads wrong, it is wrong.\n\n"
            "```text\n"
            "common failure: treating step 3 as optional\n"
            "```\n\n"
            "---\n\n"
            "Promoted from a project-local copy; the hub version is canonical.\n"
        )
    return fm + body

# ---------------------------------------------------------------------------
# Skills: source -> category -> [skill dict]
# ---------------------------------------------------------------------------

_S = {
    "personal": {
        "writing": [
            ("human-writing-en",
             "Helps agents write human-sounding English text and avoid typical AI phrasings, "
             "sentence rhythms, and structures. Use whenever the user asks to write, rewrite, "
             "draft, polish, edit, proofread, humanize, or 'de-AI' English text such as emails, "
             "messages, blog posts, articles, reports, or replies. Also use when the user says "
             "text 'sounds like AI', 'sounds robotic', 'too ChatGPT', or wants it more natural, "
             "direct, or human. Provides a diagnostic checklist, a suspicious-phrase watchlist, "
             "rewrite recipes, before/after examples, and a final self-check.",
             "12cd463"),
            ("human-writing-de",
             "Hilft Agenten, menschenähnliche deutsche Texte zu schreiben und typische "
             "KI-Formulierungen, Satzrhythmen und -strukturen zu vermeiden. Verwenden, wenn der "
             "Nutzer bittet, deutsche Texte zu schreiben, umzuschreiben, zu entwerfen, zu polieren "
             "oder menschlicher zu machen — etwa E-Mails, Nachrichten, Blogbeiträge oder Berichte.",
             "12cd463"),
        ],
        "design": [
            ("ui-demo",
             "Scaffold a static UI prototype with dummy content, iterate via Playwright and a "
             "vision-model review loop, then present the URL to the user before any real "
             "implementation begins.",
             "3c0aa17"),
            ("a4-factsheet",
             "Lay out a one-page A4 factsheet (print CSS, bleed-safe margins) from structured "
             "content. Includes typography scale and a checklist for print-ready PDF export.",
             "7da02d4"),
            ("a4-explainer-infographic",
             "Design an explainer infographic: pick a visual metaphor, structure the story in "
             "three acts, keep labels legible at thumbnail size.",
             "7da02d4"),
        ],
        "marketing": [
            ("marketing-campaign-execution",
             "Plan and execute a multi-channel marketing campaign end to end. Knows the stale-step "
             "pitfalls: audience defined twice, channels drifting from the brief, and follow-up "
             "sequences nobody owns.",
             "2f3f089"),
            ("crm-campaign-handling",
             "Create and scope campaigns inside a CRM: team scoping, contact filters, and "
             "guardrails so a campaign never leaks across teams. v1.3 team-scoping rewrite.",
             "2f3f089"),
            ("email-outreach-automation",
             "Automate personalized cold-outreach sequences with placeholder-safe templates. "
             "All example addresses are @example.com placeholders — never real inboxes.",
             "7da02d4"),
        ],
        "seo": [
            ("seo",
             "Core SEO workflow: keyword research, intent mapping, and content briefs that "
             "survive contact with an actual editorial calendar.",
             "541e5f1"),
            ("seo-audit",
             "Full technical + content audit of a site. Produces a prioritized findings list "
             "with effort/impact ratings instead of a 40-page PDF nobody reads.",
             "541e5f1"),
            ("seo-cluster",
             "Build topic clusters: pillar page, supporting articles, and an internal linking "
             "plan with anchor text that doesn't repeat itself into spam.",
             "541e5f1"),
            ("seo-content-brief",
             "Turn one keyword into an editor-ready brief: SERP intent, outline, word count "
             "range, entities to cover, and internal link targets.",
             "541e5f1"),
            ("seo-drift",
             "Detect content drift: pages whose rankings decay because the SERP moved on. "
             "Flags refresh candidates and proposes the minimal edit that fixes intent gaps.",
             "541e5f1"),
            ("seo-technical",
             "Technical SEO checklists for crawlers: render-blocking, canonical hygiene, "
             "sitemap freshness, log-file spot checks, and Core Web Vitals triage.",
             "541e5f1"),
        ],
        "testing": [
            ("ui-acceptance-testing",
             "Exploratory, human-perspective acceptance testing of a running web app from the "
             "UI layer only — no source access. Hunts empty states, broken flows, JS errors, "
             "and layout inconsistencies a spec-driven test would call 'passing'.",
             "541e5f1"),
        ],
        "tools": [
            ("android-emulator-lab",
             "Manage Android emulators headlessly: create thin snapshots, rotate profiles, and "
             "scrape logcat without a desktop.",
             "7da02d4"),
            ("implement-hubspot-mcp-tool",
             "Wrap a HubSpot operation as an MCP tool: auth via env, rate-limit backoff, and "
             "typed request/response schemas.",
             "7da02d4"),
        ],
        "data": [
            ("data-analysis",
             "Frame a vague business question as a concrete data problem, pick features and "
             "splits without leakage, and AutoGluon the baseline before anyone argues about "
             "models.",
             "8b6a714"),
        ],
    },
    "evoya": {
        "saas-pegasus": [
            ("data-table",
             "Ship a production-grade data table: AND-filtering with chips, sort arrows, "
             "sticky header, and URL-encoded filter state. The evolved variant with column "
             "choosers; adopted 1:1 by every pegasus consumer.",
             "b77e6248"),
            ("django-pegasus-models",
             "Scaffold Django models the pegasus way: UUID pks, soft-delete mixin, audit "
             "fields, and admin registration with list filters.",
             "38957c0"),
            ("create-pegasus-page",
             "Generate a full CRUD page (list + detail + form) from a model definition, "
             "matching the pegasus component conventions.",
             "38957c0"),
            ("architect-feature-flow",
             "Plan a feature as an architect: break it into tasks, name the risks, and write "
             "the mermaid diagram before any code exists.",
             "13425b6"),
            ("refactor-django-models",
             "Refactor Django models safely: split migrations, squash history, and keep the "
             "admin working at every step.",
             "13425b6"),
            ("django-multisite",
             "Run one Django deployment for many tenants: SITE_ID switching, per-site static "
             "and media roots, and the settings pattern that keeps it testable.",
             "13425b6"),
            ("django-pwa-push",
             "Add PWA push notifications to a Django site: service worker, VAPID keys, and a "
             "subscription model that tolerates expired tokens.",
             "13425b6"),
            ("remove-team-slugs-from-navigation",
             "Clean hardcoded team slugs out of navigation templates and replace them with "
             "reverse() lookups — one sweep, zero dangling links.",
             "13425b6"),
        ],
        "cib-seven-camunda": [
            ("camunda-element-templates",
             "Author Camunda element templates with proper input schemas so modelers get "
             "validation instead of booleans-in-strings.",
             "13425b6"),
            ("cibseven-camunda-integration",
             "Integrate CIB seven with Camunda: process deployment, external task workers, "
             "and the retry semantics that don't lose documents.",
             "38957c0"),
        ],
        "design": [
            ("app-design",
             "Design app UIs with a component-first mindset. Includes the DaisyUI v4 pitfalls "
             "list: class conflicts, plugin ordering, and theme variables that silently "
             "cascade.",
             "38957c0"),
            ("design-create-images",
             "Create images for design work: prompt structure, aspect-ratio planning, and a "
             "brand-consistency checklist. The generic variant — no hardcoded site paths.",
             "196c0c8"),
        ],
        "productivity": [
            ("clickup-evoya-handling",
             "Drive ClickUp the Evoya way: spaces/folders/lists conventions, task types, and "
             "when a doc beats a task. Keeps naming schemes boring on purpose.",
             "7da02d4"),
        ],
        "infrastructure": [
            ("mailservice-setup",
             "Set up the Mailbux mailservice: DNS records, DKIM alignment, and the suspension "
             "notice workflow from 2026-09. Includes rollback notes.",
             "0ab9c25"),
        ],
    },
    "awesome-roo": {
        "engineering": [
            ("create-mcp-server",
             "Scaffold an MCP server with typed tools, stdio + HTTP transports, and a test "
             "harness that mocks the client side.",
             "f0110ba"),
            ("git-workflow",
             "Opinionated git workflow: feature branches, rebase-only history, and commit "
             "messages that answer 'why', not 'what'.",
             "f0110ba"),
            ("api-integration",
             "Integrate a third-party REST API: client with retries, typed models, and a "
             "recorder fixture for offline tests.",
             "e93aa21"),
        ],
    },
}

# Source metadata (mirrors sources.yml fields)
_SOURCES = [
    {
        "name": "personal",
        "kind": "personal",
        "path": "personal",
        "root": "skills",
        "remote": None,
        "untrusted": False,
        "note": "local git only — never leaves this machine",
    },
    {
        "name": "evoya",
        "kind": "shared",
        "path": "shared/evoya",
        "root": "skills",
        "remote": "git@gitlab.evoya.io:skills/evoya.git",
        "untrusted": False,
        "note": "shared repo — remote on Evoya GitLab",
    },
    {
        "name": "awesome-roo",
        "kind": "external",
        "path": "external/awesome-roo",
        "root": ".",
        "remote": "https://github.com/example/awesome-roo",
        "untrusted": True,
        "note": "third-party collection — link individually, after a human says yes",
    },
]

# ---------------------------------------------------------------------------
# Projects: name, path, linked skill ids, local skills (mirrors skills.lock +
# non-.hub entries in .roo/skills/)
# ---------------------------------------------------------------------------

_PROJECTS = [
    {
        "name": "websites",
        "path": "~/workspaces/cursor/websites",
        "linked": [
            "personal/seo/seo",
            "personal/seo/seo-audit",
            "personal/seo/seo-drift",
            "personal/seo/seo-technical",
            "evoya/saas-pegasus/data-table",
            "personal/writing/human-writing-en",
        ],
        "local": [
            ("design-create-images-fork",
             "v2.1 fork hardcoding evoya.ai paths — stays project-local (decision 5)"),
            ("brand-tone-checklist",
             "Voice rules for the sites brand; too project-specific to promote"),
        ],
    },
    {
        "name": "directories-app",
        "path": "~/workspaces/lumatic/directories/app",
        "linked": [
            "evoya/saas-pegasus/data-table",
            "evoya/saas-pegasus/create-pegasus-page",
            "evoya/saas-pegasus/django-pegasus-models",
            "evoya/saas-pegasus/django-multisite",
            "evoya/saas-pegasus/django-pwa-push",
            "evoya/saas-pegasus/remove-team-slugs-from-navigation",
            "evoya/cib-seven-camunda/camunda-element-templates",
            "evoya/cib-seven-camunda/cibseven-camunda-integration",
        ],
        "local": [
            ("tenant-theme-overrides",
             "Per-tenant CSS variables layered on the shared theme"),
        ],
    },
    {
        "name": "ticketing-system",
        "path": "~/workspaces/lumatic/ticketing-system",
        "linked": [
            "personal/testing/ui-acceptance-testing",
            "evoya/saas-pegasus/data-table",
            "evoya/design/app-design",
        ],
        "local": [
            ("sla-escalation-flow",
             "Escalation ladder rules specific to this product's SLAs"),
        ],
    },
    {
        "name": "avaia",
        "path": "~/workspaces/avaia",
        "linked": [
            "evoya/productivity/clickup-evoya-handling",
            "personal/writing/human-writing-de",
            "personal/writing/human-writing-en",
            "personal/data/data-analysis",
        ],
        "local": [
            ("create-avaia-tool",
             "Creates an Avaia tool scaffold — project-specific"),
            ("test-avaia-implementation",
             "Runs the Avaia implementation test suite"),
            ("debug-prod-avaia",
             "Prod debugging playbook (contains prod IP — stays in-project)"),
        ],
    },
    {
        "name": "sysadmin-bachi",
        "path": "~/workspaces/sysadmin-bachi",
        "linked": [
            "evoya/infrastructure/mailservice-setup",
            "personal/tools/android-emulator-lab",
        ],
        "local": [
            ("encfs-restore",
             "Encfs restore runbook — machine-specific, stays out of the hub"),
        ],
    },
    {
        "name": "blitz-crm",
        "path": "~/workspaces/blitz-crm",
        "linked": [
            "evoya/saas-pegasus/data-table",
            "personal/marketing/email-outreach-automation",
            "personal/marketing/crm-campaign-handling",
            "personal/tools/implement-hubspot-mcp-tool",
        ],
        "local": [
            ("enrich-pipeline",
             "Google enrichment pipeline for BlitzCRM leads — project-specific"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Derived views (this is the shape the real scanner will return)
# ---------------------------------------------------------------------------

def _skill_id(source, category, name):
    return f"{source}/{category}/{name}"


def hub():
    """Hub structure: sources -> categories -> skills (with linked_by)."""
    linked_by = {}
    for proj in _PROJECTS:
        for sid in proj["linked"]:
            linked_by.setdefault(sid, []).append(proj["name"])

    sources = []
    for meta in _SOURCES:
        cats = []
        for cat, skills in _S[meta["name"]].items():
            cat_skills = []
            for name, desc, commit in skills:
                sid = _skill_id(meta["name"], cat, name)
                cat_skills.append({
                    "id": sid,
                    "name": name,
                    "description": desc,
                    "commit": _commit(sid),
                    "markdown": _markdown(meta["name"], cat, name, desc),
                    "linked_by": sorted(linked_by.get(sid, [])),
                })
            cats.append({"name": cat, "skills": cat_skills})
        sources.append({**meta, "categories": cats})

    n_skills = sum(len(c["skills"]) for s in sources for c in s["categories"])
    return {
        "meta": {
            "title": "Skills Hub",
            "remote": HUB_REMOTE,
            "note": "PROTOTYPE — dummy data",
            "skill_count": n_skills,
            "source_count": len(sources),
            "project_count": len(_PROJECTS),
            "link_count": sum(len(p["linked"]) for p in _PROJECTS),
        },
        "sources": sources,
    }


def projects():
    """Projects with resolved linked skills + local skills."""
    index = {}
    for meta in _SOURCES:
        for cat, skills in _S[meta["name"]].items():
            for name, desc, commit in skills:
                index[_skill_id(meta["name"], cat, name)] = {
                    "id": _skill_id(meta["name"], cat, name),
                    "name": name,
                    "source": meta["name"],
                    "category": cat,
                    "commit": commit,
                }

    out = []
    for proj in _PROJECTS:
        out.append({
            "name": proj["name"],
            "path": proj["path"],
            "linked": [index[sid] for sid in proj["linked"]],
            "local": [{"name": n, "description": d} for n, d in proj["local"]],
        })
    return {"projects": out}
