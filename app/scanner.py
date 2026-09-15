"""Real-data scanner for the Skills Hub UI — stdlib only.

Reads the same truth the CLI trusts:
  - sources.yml        (constrained block-YAML, grammar mirrors bin/skill-repo)
  - skills/<cat>/<skill>/SKILL.md   (frontmatter + full markdown)
  - .link-roots        (hints: which projects ever linked from this hub)
  - <project>/.roo/skills.lock      (truth: which skills a project links)
  - <project>/.roo/skills/*         (non-symlink entries = project-local skills)

Output shape is identical to app/data.py (the dummy module), so the
frontend does not care which one is behind the API.

A scan is cached for SCAN_TTL seconds; the trade-off is documented in
the server banner (reload picks up changes within a few seconds).
"""

import re
import subprocess
import time
from pathlib import Path

SCAN_TTL = 10.0
_CACHE = {"ts": 0.0, "data": None, "root": None}

EXTERNAL_NOTE = "third-party collection — link individually, after a human says yes"
PERSONAL_NOTE = "local git only — never leaves this machine unless you give it a private remote"


def _git(repo, *args):
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=15, check=True,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


# ---------------------------------------------------------------- sources.yml

def parse_sources(yml_path):
    """Constrained block-YAML parser, mirroring parse_sources in bin/skill-repo."""
    sources = []
    try:
        lines = Path(yml_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return sources

    cur = None
    in_sources = False
    for line in lines:
        if re.match(r"^sources:\s*$", line):
            in_sources = True
            continue
        if in_sources and line and not line[0].isspace() and not line.startswith("#"):
            in_sources = False  # first top-level key after the list ends it
        if not in_sources:
            continue
        clean = re.sub(r"\s+#.*$", "", line).rstrip()
        if not clean.strip():
            continue
        m = re.match(r"^\s*-\s*name:\s*(.*)$", clean)
        if m:
            cur = {"name": m.group(1).strip(), "path": "", "root": ".",
                   "remote": "", "untrusted": False}
            sources.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^\s+path:\s*(.*)$", clean)
        if m:
            cur["path"] = m.group(1).strip()
            continue
        m = re.match(r"^\s+root:\s*(.*)$", clean)
        if m:
            cur["root"] = m.group(1).strip() or "."
            continue
        m = re.match(r"^\s+remote:\s*(.*)$", clean)
        if m:
            cur["remote"] = m.group(1).strip()
            continue
        m = re.match(r"^\s+untrusted:\s*(.*)$", clean)
        if m:
            cur["untrusted"] = m.group(1).strip().lower().startswith("t")
    return [s for s in sources if s["name"]]


# ---------------------------------------------------------------- frontmatter

def parse_frontmatter(text):
    """Minimal YAML frontmatter: top-level `key: value` + folded (>-) scalars.

    Returns (meta, rest_of_text).
    """
    meta = {}
    rest = text
    if text.startswith("---"):
        m = re.match(r"^---[ \t]*\n(.*?)[ \t]*\n---[ \t]*(?:\n|$)(.*)$", text, re.S)
        if m:
            block, rest = m.group(1), m.group(2)
            key = None
            for line in block.splitlines():
                top = re.match(r"^([A-Za-z0-9_][\w-]*):\s*(.*)$", line)
                if top:
                    key = top.group(1)
                    val = top.group(2).strip()
                    meta[key] = ""
                    if val and val[0] not in ">|":
                        meta[key] = val
                        key = None
                elif key is not None and line[:1] in (" ", "\t"):
                    meta[key] = (meta[key] + " " + line.strip()).strip()
    return meta, rest


def first_paragraph(rest):
    """Fallback description: first non-heading, non-table paragraph, one line."""
    rest = re.sub(r"```.*?```", "", rest, flags=re.S)  # fenced blocks make poor descriptions
    for block in re.split(r"\n\s*\n", rest.strip()):
        if block.lstrip().startswith("|"):
            continue  # tables make poor descriptions too
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        text_lines = [l for l in lines if not l.startswith("#")]
        if text_lines:
            para = " ".join(text_lines)
            para = re.sub(r"[*_`>\[\]()#]", "", para)
            return para.strip()
    return ""


# ---------------------------------------------------------------- skills scan

def scan_source_skills(hub, src):
    """Walk <path>/<root> for SKILL.md files.

    Returns (skills_by_hubrelpath, categories) where categories is an
    ordered {category: [skill, ...]} dict.
    """
    root_dir = (hub / src["path"] / src["root"]).resolve()
    repo_dir = hub / src["path"]
    skills = {}
    cats = {}
    if not root_dir.is_dir():
        return skills, cats

    for sk_md in sorted(root_dir.rglob("SKILL.md")):
        skill_dir = sk_md.parent
        hub_rel = skill_dir.relative_to(hub).as_posix()
        repo_rel = skill_dir.relative_to(repo_dir).as_posix()
        category = skill_dir.relative_to(root_dir).parent.as_posix()
        if category == ".":
            category = "."
        try:
            text = sk_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        meta, rest = parse_frontmatter(text)
        desc = (meta.get("description") or "").strip()
        if not desc:
            desc = first_paragraph(rest)
        if not desc:
            desc = "No description"

        commit = _git(repo_dir, "log", "-1", "--format=%h", "--", repo_rel) or "-"
        sid = f'{src["name"]}/{name_of(src, category, skill_dir.name)}'
        skill = {
            "id": sid,
            "name": skill_dir.name,
            "description": desc,
            "commit": commit,
            "markdown": text,
            "linked_by": [],
        }
        skills[hub_rel] = skill
        cats.setdefault(category, []).append(skill)
    return skills, cats


def name_of(src, category, skill_name):
    if category in (".", ""):
        return skill_name
    return f"{category}/{skill_name}"


# ---------------------------------------------------------------- locks

def parse_lock(path):
    """Parse a .roo/skills.lock: `link:` blocks with indented key: value."""
    entries = []
    cur = None
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return entries
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([^\s:]+):\s*$", line)
        if m:
            cur = {"link": m.group(1)}
            entries.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^\s+(source|category|path|commit|aliased):\s*(.*)$", line)
        if m:
            cur[m.group(1)] = m.group(2).strip()
    return entries


def scan_local_skills(project_root):
    """Real (non-symlink) skill dirs in .roo/skills. Hub links are symlinks."""
    out = []
    sk_dir = project_root / ".roo" / "skills"
    if not sk_dir.is_dir():
        return out
    for entry in sorted(sk_dir.iterdir()):
        n = entry.name
        if n.startswith(".") or ".pre-hub-" in n:
            continue
        if entry.is_symlink() or not entry.is_dir():
            continue
        sk_md = entry / "SKILL.md"
        if not sk_md.is_file():
            continue
        try:
            text = sk_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        meta, rest = parse_frontmatter(text)
        desc = (meta.get("description") or "").strip() or first_paragraph(rest) or "project-local skill"
        out.append({"name": n, "description": desc})
    return out


# ---------------------------------------------------------------- folder readmes

def read_category_readme(root_dir, category):
    """Folder-level README describing a skill set (a category folder).

    The UI renders it as markdown above the folder's skills, so a team can
    document what e.g. `saas-pegasus` is for. `README.txt` wins over
    `README.md` (the .txt name keeps git forges from treating it as the
    repo readme). Returns {"file", "markdown"} or None.
    """
    folder = root_dir if category in (".", "") else root_dir / category
    for fname in ("README.txt", "README.md"):
        try:
            text = (folder / fname).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        return {"file": fname, "markdown": text}
    return None


# ---------------------------------------------------------------- full scan

def _kind_of(src):
    if src["untrusted"]:
        return "external"
    if src["path"].split("/", 1)[0] == "personal":
        return "personal"
    return "shared"


def _scan(hub):
    hub = Path(hub).resolve()
    sources_meta = parse_sources(hub / "sources.yml")

    hub_remote = _git(hub, "remote", "get-url", "origin")
    path_index = {}  # hub-relative posix path -> skill dict
    sources_out = []
    skills_count = 0

    for src in sources_meta:
        kind = _kind_of(src)
        remote = src["remote"] or _git(hub / src["path"], "remote", "get-url", "origin")
        skills, cats = scan_source_skills(hub, src)
        root_dir = (hub / src["path"] / src["root"]).resolve()
        for hub_rel, skill in skills.items():
            path_index[hub_rel] = skill
        skills_count += sum(len(v) for v in cats.values())
        note = (EXTERNAL_NOTE if src["untrusted"]
                else PERSONAL_NOTE if kind == "personal"
                else "shared content repo — own git history and remote")
        sources_out.append({
            "name": src["name"],
            "kind": kind,
            "path": src["path"],
            "root": src["root"],
            "remote": remote,
            "untrusted": bool(src["untrusted"]),
            "note": note,
            "categories": [
                {
                    "name": cat,
                    "readme": read_category_readme(root_dir, cat),
                    "skills": cat_skills,
                }
                for cat, cat_skills in sorted(cats.items())
            ],
        })

    # ---------------------------------------------------------- projects
    projects_out = []
    unresolved = []
    roots_file = hub / ".link-roots"
    home = str(Path.home())
    if roots_file.is_file():
        for line in roots_file.read_text(encoding="utf-8", errors="replace").splitlines():
            root = line.strip()
            if not root or root.startswith("#"):
                continue
            r = Path(root)
            name = r.name or root
            disp = root.replace(home, "~") if root.startswith(home) else root
            lock_path = r / ".roo" / "skills.lock"
            linked = []
            stale = not lock_path.is_file()
            if not stale:
                for e in parse_lock(lock_path):
                    skill = path_index.get(e.get("path", ""))
                    if skill is None:
                        unresolved.append((name, e.get("path", ""), e.get("link", "")))
                        continue
                    linked.append({
                        "id": skill["id"],
                        "name": skill["name"],
                        "source": next(s["name"] for s in sources_meta if skill["id"].startswith(s["name"] + "/")),
                        "category": e.get("category", "."),
                        "commit": e.get("commit", "-"),
                    })
                    if name not in skill["linked_by"]:
                        skill["linked_by"].append(name)
            projects_out.append({
                "name": name,
                "path": disp,
                "stale": stale,
                "linked": linked,
                "local": scan_local_skills(r),
            })

    for s in path_index.values():
        s["linked_by"].sort()

    link_count = sum(len(p["linked"]) for p in projects_out)
    hub_out = {
        "meta": {
            "title": "Skills Hub",
            "remote": hub_remote,
            "note": "live data",
            "skill_count": skills_count,
            "source_count": len(sources_out),
            "project_count": len(projects_out),
            "link_count": link_count,
        },
        "sources": sources_out,
        "_unresolved": unresolved,
    }
    return {"hub": hub_out, "projects": {"projects": projects_out}}


def scan(hub_root, force=False):
    """Cached entry point (SCAN_TTL seconds)."""
    hub_root = str(Path(hub_root).resolve())
    now = time.monotonic()
    if (not force and _CACHE["data"] is not None
            and _CACHE["root"] == hub_root and now - _CACHE["ts"] < SCAN_TTL):
        return _CACHE["data"]
    data = _scan(hub_root)
    _CACHE.update(ts=now, data=data, root=hub_root)
    return data


if __name__ == "__main__":  # standalone sanity check: python3 app/scanner.py [hub_root]
    import json
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
    d = scan(root, force=True)
    meta = d["hub"]["meta"]
    print(json.dumps(meta, indent=2))
    for s in d["hub"]["sources"]:
        cats = ", ".join(f"{c['name']}:{len(c['skills'])}" for c in s["categories"])
        print(f"  {s['name']:<14} {s['kind']:<9} remote={s['remote'] or '-':<50} {cats}")
    for p in d["projects"]["projects"]:
        flag = " STALE" if p["stale"] else ""
        print(f"  {p['name']:<28} {len(p['linked'])} linked, {len(p['local'])} local{flag}")
    unres = d["hub"]["_unresolved"]
    print(f"unresolved lock paths: {len(unres)}")
    for u in unres[:10]:
        print("   ", u)
