/* Skills Hub UI — prototype. Vanilla JS, no dependencies. */
"use strict";

/* ------------------------------------------------------------------ state */

const state = {
  hub: null,
  projects: null,
  sourceKinds: {},
  sourceOpen: {},
  query: "",
};

function isSourceOpen(name) {
  return state.sourceOpen[name] !== false;
}

const view = document.getElementById("view");
const searchInput = document.getElementById("search");

const SOURCE_COLORS = {
  personal: "var(--personal)",
  shared: "var(--shared)",
  external: "var(--external)",
};

/* ------------------------------------------------------------------ utils */

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

function linkIcon(size = 12) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M6.35 4.15 7.4 3.1a3.5 3.5 0 0 1 4.95 4.95l-1.05 1.05-.7-.7 1.05-1.05a2.5 2.5 0 0 0-3.55-3.55L5.65 5.95l-.7-.7 1.4-1.1Zm3.3 7.7L8.6 12.9a3.5 3.5 0 0 1-4.95-4.95l1.05-1.05.7.7-1.05 1.05a2.5 2.5 0 0 0 3.55 3.55l1.4-1.05.35-.35.7.7-.65.35Z");
  path.setAttribute("fill", "currentColor");
  svg.appendChild(path);
  return svg;
}

function copyIcon(size = 13) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  const back = document.createElementNS("http://www.w3.org/2000/svg", "path");
  back.setAttribute("d", "M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Zm5-5C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z");
  back.setAttribute("fill", "currentColor");
  svg.appendChild(back);
  return svg;
}

function externalIcon() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("width", "12");
  svg.setAttribute("height", "12");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M9 2h5v5h-1V3.7l-5.4 5.39-.71-.71L12.3 3H9V2ZM4 3h4v1H4.5A1.5 1.5 0 0 0 3 5.5v6A1.5 1.5 0 0 0 4.5 13h6a1.5 1.5 0 0 0 1.5-1.5V8h1v3.5A2.5 2.5 0 0 1 10.5 14h-6A2.5 2.5 0 0 1 2 11.5v-6A2.5 2.5 0 0 1 4.5 2Z");
  path.setAttribute("fill", "currentColor");
  svg.appendChild(path);
  return svg;
}

function dotLabel(kind) {
  return el("span", { class: "dot-label" },
    el("span", { class: "dot", style: `--dot-color:${SOURCE_COLORS[kind]}` }), kind);
}

function matchesSkill(skill, q) {
  return skill.name.toLowerCase().includes(q) || skill.description.toLowerCase().includes(q);
}

function matchesProject(project, q) {
  if (project.name.toLowerCase().includes(q) || project.path.toLowerCase().includes(q)) return true;
  return (
    project.linked.some((s) => s.name.toLowerCase().includes(q)) ||
    project.local.some((s) => s.name.toLowerCase().includes(q))
  );
}

/* --------------------------------------------------- clipboard + link prompts */

function copyText(text) {
  return new Promise((resolve) => {
    const fallback = () => {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand("copy");
        ta.remove();
        resolve(ok);
      } catch {
        resolve(false);
      }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => resolve(true), fallback);
    } else {
      fallback();
    }
  });
}

let toastTimer = null;
function toast(msg) {
  let node = document.querySelector(".toast");
  if (!node) {
    node = el("div", { class: "toast", role: "status" });
    document.body.appendChild(node);
  }
  node.textContent = msg;
  node.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("show"), 2200);
}

/* One line each — the skill-hub-handling meta skill owns the detailed flow
   (refs in .roo/skills.yml, `skill-repo link`, load check, and the rule
   that untrusted sources link individual skills only). */
function skillLinkPrompt(skill) {
  return `Link the skills-hub skill \`${skill.id}\` into this project, following the skill-hub-handling skill.`;
}

function categoryLinkPrompt(src, cat) {
  const count = (cat.skills || []).length;
  const n = `${count} skill${count === 1 ? "" : "s"}`;
  const label = cat.name === "." || cat.name === "" ? src.name : `${src.name}/${cat.name}`;
  return `Link all ${n} in the skills-hub folder \`${label}\` into this project, following the skill-hub-handling skill.`;
}

function copyPromptButton(title, getPrompt, label) {
  const children = [copyIcon()];
  if (label) children.push(el("span", { text: label }));
  return el("button", {
    class: "copy-prompt" + (label ? " labeled" : ""),
    type: "button",
    title,
    "aria-label": title,
    onclick: (e) => {
      e.stopPropagation();
      copyText(getPrompt()).then((ok) => {
        toast(ok ? "prompt copied — paste it into your agent chat" : "copy failed — clipboard unavailable");
      });
      const btn = e.currentTarget;
      btn.classList.add("flash");
      setTimeout(() => btn.classList.remove("flash"), 1800);
    },
  }, children);
}

/* ------------------------------------------------------------------ router */

function currentView() {
  return location.hash.startsWith("#/projects") ? "projects" : "hub";
}

function navigate(viewName, skillId) {
  if (viewName === "skill") {
    location.hash = `#/skill/${encodeURIComponent(skillId)}`;
    return;
  }
  const base = viewName === "projects" ? "#/projects" : "#/hub";
  location.hash = skillId ? `${base}?skill=${encodeURIComponent(skillId)}` : base;
}

function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, qs] = raw.split("?");
  const params = new URLSearchParams(qs || "");
  if (path === "projects") return { viewName: "projects", skillId: params.get("skill") };
  if (path.startsWith("skill/")) {
    return { viewName: "skill", skillId: decodeURIComponent(path.slice("skill/".length)) };
  }
  return { viewName: "hub", skillId: params.get("skill") };
}

window.addEventListener("hashchange", render);

/* ------------------------------------------------------------------ render */

let lastRoute = null; // route key of the previous render — detects real navigation

function render() {
  const { viewName, skillId } = parseHash();
  const route = `${viewName}:${skillId || ""}`;
  const routeChanged = route !== lastRoute;
  lastRoute = route;
  document.getElementById("tab-hub").setAttribute("aria-selected", String(viewName === "hub"));
  document.getElementById("tab-projects").setAttribute("aria-selected", String(viewName === "projects"));
  view.textContent = "";
  document.title = viewName === "skill" && skillId
    ? `${skillId.split("/").pop()} — Skills Hub`
    : "Skills Hub";
  if (viewName === "projects") renderProjects(skillId);
  else if (viewName === "skill") renderSkillView(skillId);
  else renderHub(skillId);
  if (routeChanged) resetScroll(viewName, skillId);
}

/* Hash navigation keeps the old scroll offset (the fragment matches no anchor),
   so a fresh route would otherwise open mid-page. Focused hub/projects routes
   are the exception: their focus helpers scroll to the flashed card instead. */
function resetScroll(viewName, skillId) {
  if (skillId && viewName !== "skill") return;
  const html = document.documentElement;
  const smooth = html.style.scrollBehavior;
  html.style.scrollBehavior = "auto"; // bypass the global smooth scrolling
  window.scrollTo(0, 0);
  html.style.scrollBehavior = smooth;
}

function renderEmptyState(isSearch) {
  const wrap = el("div", { class: "empty" });
  if (isSearch) {
    wrap.append(
      el("div", { class: "empty-title", text: `No matches for "${state.query}"` }),
      el("div", {}, "Try a shorter term, or ",
        el("button", { onclick: clearSearch, text: "clear the search" }), "."),
    );
  } else {
    wrap.append(el("div", { class: "empty-title", text: "Nothing here yet" }));
  }
  view.appendChild(wrap);
}

/* ------------------------------------------------------------------ hub view */

function renderHub(focusSkillId) {
  const { meta, sources } = state.hub;
  const q = state.query.trim().toLowerCase();
  const searching = q.length > 0;

  const catNodes = [];
  let shown = 0;
  for (const src of sources) {
    const srcCats = [];
    let srcCount = 0;
    for (const cat of src.categories) {
      const skills = searching ? cat.skills.filter((s) => matchesSkill(s, q)) : cat.skills;
      if (skills.length === 0) continue;
      srcCount += skills.length;
      srcCats.push(buildCategory(cat, skills, src, searching, focusSkillId));
    }
    if (srcCats.length === 0) continue;
    shown += srcCount;
    catNodes.push(buildSourceCard(src, srcCats, srcCount, searching));
  }

  view.appendChild(el("div", { class: "stats-row" },
    searching
      ? statPill(`${shown} / ${meta.skill_count}`, "skills match")
      : statPill(meta.skill_count, "skills"),
    statPill(sources.length, "sources"),
    statPill(meta.project_count, "projects linking"),
    statPill(meta.link_count, "active links"),
  ));

  if (!searching) view.appendChild(buildTreeCard(sources));

  if (catNodes.length === 0) {
    renderEmptyState(searching);
    return;
  }
  for (const node of catNodes) view.appendChild(node);

  if (focusSkillId) focusSkillCard(focusSkillId);
}

function statPill(n, label) {
  return el("span", { class: "stat-pill" }, el("b", { text: String(n) }), label);
}

function buildTreeCard(sources) {
  const meta = state.hub.meta;
  const dirCount = (src) => src.categories.reduce((n, c) => n + c.skills.length, 0);

  const card = el("section", { class: "tree-card" }, el("h2", { text: "hub layout" }));
  const pre = el("div", { class: "tree" });

  const line = (main, rest, mainClass) => {
    const row = el("div", { class: "t-row" });
    row.appendChild(el("span", { class: `t-main ${mainClass || ""}`.trim(), text: main }));
    if (rest) row.appendChild(el("span", { class: "t-note", text: rest }));
    pre.appendChild(row);
  };

  line("skill-hub/", meta.remote, "t-dir");
  line("├── bin/skill-repo", "the CLI (bash, no dependencies)", "t-dim");
  line("├── meta/skill-hub-handling/", "the one global skill", "t-dim");
  line("├── sources.yml", "machine-local registry (gitignored)", "t-dim");
  sources.forEach((src, i) => {
    const last = i === sources.length - 1;
    const parts = [`${dirCount(src)} skills`];
    parts.push(src.remote || "no remote yet");
    if (src.untrusted) parts.push("untrusted");
    line((last ? "└── " : "├── ") + src.path + "/", parts.join(" ·\u00a0"), "t-dir");
  });

  card.appendChild(pre);
  return card;
}

function buildSourceCard(src, catNodes, count, forceOpen) {
  const headChildren = [
    el("span", { class: "source-dot" }),
    el("span", { class: "source-name", text: src.name }),
  ];
  if (src.path !== src.name) headChildren.push(el("span", { class: "source-path", text: src.path + "/" }));
  headChildren.push(el("span", { class: `badge kind-${src.kind}`, text: src.kind }));

  const section = el("section", { class: "source-card", "data-source": src.name });
  const open = forceOpen || isSourceOpen(src.name);
  if (!open) section.classList.add("collapsed");

  const toggle = el("button", {
    class: "source-toggle", type: "button",
    title: open ? "collapse repo" : "expand repo",
    "aria-expanded": String(open),
    "aria-label": `${open ? "collapse" : "expand"} ${src.name}`,
    onclick: (e) => { e.stopPropagation(); applyOpen(!isOpen()); },
  }, open ? "−" : "+");

  const head = el("div", {
    class: "source-head", style: `--src-color:${SOURCE_COLORS[src.kind] || "var(--faint)"}`,
    onclick: (e) => {
      if (e.target.closest("a, button.source-remote")) return;
      applyOpen(!isOpen());
    },
  }, headChildren);
  if (src.untrusted) head.appendChild(el("span", { class: "badge untrusted", title: src.note, text: "untrusted" }));

  if (src.remote && /^https?:\/\//.test(src.remote)) {
    head.appendChild(el("a", {
      class: "source-remote", href: src.remote, target: "_blank", rel: "noreferrer noopener",
      title: src.remote,
    }, externalIcon(), src.remote));
  } else if (src.remote) {
    const btn = el("button", {
      class: "source-remote", type: "button",
      title: `${src.remote} — click to copy`,
      text: src.remote,
    });
    btn.addEventListener("click", () => {
      const done = () => {
        btn.classList.add("flash");
        setTimeout(() => btn.classList.remove("flash"), 1800);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(src.remote).then(done, done);
      } else { done(); }
    });
    head.appendChild(btn);
  } else {
    head.appendChild(el("span", { class: "source-remote no-remote", title: src.note }, "no remote"));
  }

  head.appendChild(el("span", { class: "source-count", title: "expand / collapse" }, el("b", { text: String(count) }), " skills"));
  head.appendChild(toggle);

  const body = el("div", { class: "source-body" });
  for (const cat of catNodes) body.appendChild(cat);

  section.append(head, body);

  function isOpen() { return !section.classList.contains("collapsed"); }

  function applyOpen(val) {
    state.sourceOpen[src.name] = val;
    section.classList.toggle("collapsed", !val);
    toggle.textContent = val ? "−" : "+";
    toggle.setAttribute("aria-expanded", String(val));
    toggle.setAttribute("aria-label", `${val ? "collapse" : "expand"} ${src.name}`);
    toggle.title = val ? "collapse repo" : "expand repo";
  }

  return section;
}

function buildCategory(cat, skills, src, searching, focusSkillId) {
  const head = el("button", {
    class: "category-head", type: "button",
    onclick: (e) => { e.currentTarget.closest(".category").classList.toggle("open"); },
  },
    el("span", { class: "cat-chevron", text: "▶" }),
    el("span", { class: "cat-name", text: cat.name }),
    el("span", { class: "cat-count", text: String(skills.length) }),
  );

  const folderLabel = cat.name === "." || cat.name === "" ? src.name : `${src.name}/${cat.name}`;
  const copyBtn = copyPromptButton(
    `copy prompt — link every skill in ${folderLabel}`,
    () => categoryLinkPrompt(src, cat), // cat.skills: the WHOLE folder, even mid-search
  );

  const grid = el("div", { class: "skill-grid" });
  for (const skill of skills) grid.appendChild(buildSkillCard(skill, src, focusSkillId));

  const body = el("div", { class: "category-body" });
  const md = cat.readme && cat.readme.markdown ? cat.readme.markdown.trim() : "";
  if (md) {
    body.appendChild(el("section", { class: "cat-readme" },
      el("div", { class: "cat-readme-file", text: cat.readme.file || "README.txt" }),
      renderMarkdown(md)));
  }
  body.appendChild(grid);

  const node = el("div", { class: "category open" },
    el("div", { class: "category-row" }, head, copyBtn),
    body);
  if (!searching && !focusSkillId) node.classList.remove("open"); // collapsed by default
  return node;
}

function buildSkillCard(skill, src, focusSkillId) {
  const foot = el("div", { class: "skill-foot" });
  if (skill.linked_by.length > 0) {
    foot.appendChild(el("button", {
      class: "linked-by", type: "button",
      title: skill.linked_by.join(", "),
      onclick: (e) => { e.stopPropagation(); navigate("projects", skill.id); },
    }, linkIcon(), `${skill.linked_by.length} project${skill.linked_by.length === 1 ? "" : "s"}`));
  } else {
    foot.appendChild(el("span", { class: "not-linked", text: "not linked yet" }));
  }
  foot.appendChild(copyPromptButton(`copy prompt — link ${skill.id}`, () => skillLinkPrompt(skill)));
  foot.appendChild(el("span", { class: "expand-hint" },
    el("span", { class: "more", text: "more" }),
    el("span", { class: "chev", text: "▾" }),
    el("span", { class: "less", text: "less" }),
  ));

  const article = el("article", {
    class: "skill" + (focusSkillId === skill.id ? " expanded flash" : ""),
    tabindex: "0",
    role: "button",
    "aria-expanded": String(focusSkillId === skill.id),
    "data-skill-id": skill.id,
    style: `--src-color:${SOURCE_COLORS[src.kind] || "var(--faint)"}`,
    onclick: () => toggleSkill(article),
    onkeydown: (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleSkill(article); }
    },
  },
    el("div", { class: "skill-head" },
      el("span", { class: "skill-name" },
        el("a", {
          class: "skill-link", href: `#/skill/${encodeURIComponent(skill.id)}`,
          title: "open SKILL.md",
          onclick: (e) => e.stopPropagation(),
          onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") e.stopPropagation(); },
        }, skill.name)),
      el("span", { class: "skill-commit", title: "last hub commit touching this skill", text: skill.commit }),
    ),
    el("p", { class: "skill-desc", text: skill.description }),
    foot,
  );
  return article;

  function toggleSkill(card) {
    card.classList.toggle("expanded");
    card.setAttribute("aria-expanded", String(card.classList.contains("expanded")));
  }
}

/* ------------------------------------------------------------------ projects view */

function renderProjects(focusSkillId) {
  const projects = state.projects.projects;
  const q = state.query.trim().toLowerCase();
  const searching = q.length > 0;

  view.appendChild(el("div", { class: "legend" },
    el("span", { class: "legend-item" },
      el("span", { class: "chip linked example" }, linkIcon(), "linked from hub"),
      el("span", { text: "— click a chip to open its SKILL.md" })),
    el("span", { class: "legend-item" },
      el("span", { class: "chip local example" }, "local only"),
      el("span", { text: "— project-local copy, not managed by the hub" })),
    el("span", { class: "legend-item legend-dots" },
      el("span", { text: "chip dot = source:" }),
      dotLabel("personal"), dotLabel("shared"), dotLabel("external")),
  ));

  const visible = searching ? projects.filter((p) => matchesProject(p, q)) : projects;
  if (visible.length === 0) { renderEmptyState(searching); return; }

  for (const proj of visible) view.appendChild(buildProjectCard(proj, focusSkillId));

  if (focusSkillId) focusProjectChips(focusSkillId);
}

function buildProjectCard(proj, focusSkillId) {
  const counts = el("span", { class: "project-counts" },
    el("b", { class: "n-linked", text: String(proj.linked.length) }), " linked · ",
    el("b", { class: "n-local", text: String(proj.local.length) }), " local",
  );

  const head = el("div", { class: "project-head" },
    el("span", { class: "project-name", text: proj.name }),
    el("span", { class: "project-path", text: proj.path }),
    counts,
  );

  const linkedChips = proj.linked.map((s) => {
    const srcKind = state.sourceKinds[s.source] || "shared";
    return el("button", {
      class: "chip linked" + (focusSkillId === s.id ? " flash" : ""),
      type: "button",
      title: `${s.source}/${s.category}/${s.name}`,
      "data-skill-id": s.id,
      onclick: () => navigate("skill", s.id),
    }, el("span", { class: "dot", style: `--dot-color:${SOURCE_COLORS[srcKind]}` }), s.name);
  });

  const localChips = proj.local.map((s) =>
    el("span", { class: "chip local", title: s.description || "project-local skill" }, s.name));

  const linkedRow = el("div", { class: "prow" },
    el("span", { class: "prow-label", text: "Linked" }),
    linkedChips.length ? el("div", { class: "chips" }, linkedChips) : el("span", { class: "chips-none", text: "none" }),
  );

  const localRow = el("div", { class: "prow" },
    el("span", { class: "prow-label", text: "Local" }),
    localChips.length ? el("div", { class: "chips" }, localChips) : el("span", { class: "chips-none", text: "none" }),
  );

  return el("section", { class: "project-card", "data-project": proj.name }, head, linkedRow, localRow);
}

function focusProjectChips(skillId) {
  const chips = document.querySelectorAll(`.chip.linked[data-skill-id="${CSS.escape(skillId)}"]`);
  chips.forEach((chip) => chip.classList.add("flash"));
  if (chips.length > 0) chips[0].scrollIntoView({ block: "center", behavior: "smooth" });
}

/* ------------------------------------------------------------------ skill detail view */

function findSkill(id) {
  for (const src of state.hub.sources) {
    for (const cat of src.categories) {
      for (const skill of cat.skills) {
        if (skill.id === id) return { src, cat, skill };
      }
    }
  }
  return null;
}

function renderSkillView(id) {
  const hit = findSkill(id);
  if (!hit) {
    view.appendChild(el("div", { class: "empty" },
      el("div", { class: "empty-title", text: "Skill not found" }),
      el("div", {}, "It may live outside this hub — ",
        el("a", { class: "crumb", href: "#/hub", text: "back to the Hub" }), ".")));
    return;
  }
  const { src, cat, skill } = hit;
  const rootPrefix = src.root && src.root !== "." ? `${src.path}/${src.root}` : src.path;

  const actions = el("div", { class: "hero-actions" });
  if (skill.linked_by.length > 0) {
    actions.appendChild(el("button", {
      class: "linked-by", type: "button",
      title: skill.linked_by.join(", "),
      onclick: () => navigate("projects", skill.id),
    }, linkIcon(), `linked by ${skill.linked_by.length} project${skill.linked_by.length === 1 ? "" : "s"}`));
  } else {
    actions.appendChild(el("span", { class: "not-linked", text: "not linked by any project yet" }));
  }
  actions.appendChild(copyPromptButton(
    `copy the prompt that links ${skill.id} into a project`,
    () => skillLinkPrompt(skill),
    "copy link prompt",
  ));
  actions.appendChild(el("button", {
    class: "hero-alt", type: "button",
    onclick: () => navigate("hub", skill.id),
  }, "show in Hub view ↗"));

  const hero = el("section", { class: "skill-hero", style: `--src-color:${SOURCE_COLORS[src.kind] || "var(--faint)"}` },
    el("a", { class: "crumb", href: "#/hub", text: "← Hub" }),
    el("h1", { class: "skill-title", text: skill.name }),
    el("div", { class: "skill-meta" },
      el("span", { class: `badge kind-${src.kind}`, text: src.name }),
      el("span", { class: "hero-path", text: `${rootPrefix}/${cat.name}/${skill.name}/SKILL.md` }),
      el("span", { class: "skill-commit", title: "hub commit recorded in the project's skills.lock", text: skill.commit }),
      src.untrusted ? el("span", { class: "badge untrusted", text: "untrusted" }) : null,
    ),
    el("p", { class: "skill-lede", text: skill.description }),
    actions,
  );

  const mdCard = el("section", { class: "md-card" },
    el("h2", { class: "md-file", text: "SKILL.md" }),
    renderMarkdown(skill.markdown || ""),
  );

  view.append(hero, mdCard);
}

/* ------------------------------------------------------------------ markdown (safe mini renderer) */

const HTML_ESCAPES = {
  "&": "&" + "amp;",
  "<": "&" + "lt;",
  ">": "&" + "gt;",
  '"': "&" + "quot;",
};

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (ch) => HTML_ESCAPES[ch]);
}

function inlineHtml(text) {
  let s = escapeHtml(text);
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>');
  return s;
}

function renderMarkdown(src) {
  const wrap = el("div", { class: "md" });
  let text = String(src).replace(/\r\n/g, "\n");
  text = text.replace(/^---\n[\s\S]*?\n---\n/, ""); // strip YAML frontmatter
  const lines = text.split("\n");

  let para = [];
  const flushPara = () => {
    if (para.length) {
      const p = el("p");
      p.innerHTML = inlineHtml(para.join(" "));
      wrap.appendChild(p);
      para = [];
    }
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) { flushPara(); i++; continue; }

    if (line.startsWith("```")) {
      flushPara();
      const lang = line.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) { codeLines.push(lines[i]); i++; }
      i++; // skip closing fence
      const pre = el("pre", lang ? { "data-lang": lang } : {});
      pre.appendChild(el("code", { text: codeLines.join("\n") }));
      wrap.appendChild(pre);
      continue;
    }

    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      flushPara();
      const tag = "h" + Math.min(h[1].length + 1, 5); // demote one level; page owns h1
      const node = el(tag);
      node.innerHTML = inlineHtml(h[2]);
      wrap.appendChild(node);
      i++;
      continue;
    }

    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) { flushPara(); wrap.appendChild(el("hr")); i++; continue; }

    if (line.startsWith(">")) {
      flushPara();
      const q = [];
      while (i < lines.length && lines[i].startsWith(">")) { q.push(lines[i].replace(/^>\s?/, "")); i++; }
      const bq = el("blockquote");
      const p = el("p");
      p.innerHTML = inlineHtml(q.join(" "));
      bq.appendChild(p);
      wrap.appendChild(bq);
      continue;
    }

    const isTableRow = (l) => l.includes("|") && l.trim().length > 1;
    const isTableSep = (l) => /^\s*\|?\s*:?-{2,}[-\s|:]*\|/.test(l) && l.includes("-");
    if (isTableRow(line) && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      flushPara();
      const rows = [];
      while (i < lines.length && isTableRow(lines[i])) { rows.push(lines[i]); i++; }
      const parseRow = (r) => r.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());
      const table = el("table");
      const thead = el("thead");
      const trh = el("tr");
      for (const c of parseRow(rows[0])) { const th = el("th"); th.innerHTML = inlineHtml(c); trh.appendChild(th); }
      thead.appendChild(trh);
      table.appendChild(thead);
      const tbody = el("tbody");
      for (const r of rows.slice(2)) {
        const tr = el("tr");
        for (const c of parseRow(r)) { const td = el("td"); td.innerHTML = inlineHtml(c); tr.appendChild(td); }
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
      wrap.appendChild(table);
      continue;
    }

    const isUl = (l) => /^\s*[-*]\s+/.test(l);
    const isOl = (l) => /^\s*\d+\.\s+/.test(l);
    if (isUl(line) || isOl(line)) {
      flushPara();
      const ul = isUl(line);
      const re = ul ? /^\s*[-*]\s+/ : /^\s*\d+\.\s+/;
      const items = [];
      while (i < lines.length && (ul ? isUl(lines[i]) : isOl(lines[i]))) {
        let itemText = lines[i].replace(re, "");
        i++;
        // hard-wrapped continuation lines belong to the previous item
        while (i < lines.length && /^\s{2,}\S/.test(lines[i])
               && !isUl(lines[i]) && !isOl(lines[i])
               && !lines[i].startsWith("#") && !lines[i].startsWith("```")
               && !lines[i].startsWith(">")) {
          itemText += " " + lines[i].trim();
          i++;
        }
        items.push(itemText);
      }
      const list = el(ul ? "ul" : "ol");
      for (const it of items) {
        const li = el("li");
        const task = it.match(/^\[( |x|X)\]\s*(.*)$/);
        li.innerHTML = task
          ? (task[1].trim() ? "☑ " : "☐ ") + inlineHtml(task[2])
          : inlineHtml(it);
        list.appendChild(li);
      }
      wrap.appendChild(list);
      continue;
    }

    para.push(line.trim());
    i++;
  }
  flushPara();
  return wrap;
}

/* ------------------------------------------------------------------ focus helpers */

function focusSkillCard(skillId) {
  const card = view.querySelector(`.skill[data-skill-id="${CSS.escape(skillId)}"]`);
  if (!card) return;
  card.scrollIntoView({ block: "center", behavior: "smooth" });
  card.focus({ preventScroll: true });
}

/* ------------------------------------------------------------------ search + tabs */

function clearSearch() {
  searchInput.value = "";
  searchInput.classList.remove("not-empty");
  state.query = "";
  render();
}

searchInput.addEventListener("input", () => {
  state.query = searchInput.value;
  searchInput.classList.toggle("not-empty", searchInput.value.length > 0);
  render();
});

searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { clearSearch(); searchInput.blur(); }
});

document.getElementById("clear-btn").addEventListener("click", () => {
  clearSearch();
  searchInput.focus();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== searchInput) {
    e.preventDefault();
    searchInput.focus();
    searchInput.select();
  }
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => navigate(tab.dataset.view));
});

/* ------------------------------------------------------------------ boot */

async function boot() {
  const [hubRes, projRes] = await Promise.all([fetch("/api/hub"), fetch("/api/projects")]);
  if (!hubRes.ok || !projRes.ok) throw new Error(`API error (${hubRes.status}/${projRes.status})`);
  state.hub = await hubRes.json();
  state.projects = await projRes.json();

  for (const src of state.hub.sources) state.sourceKinds[src.name] = src.kind;

  document.getElementById("count-hub").textContent = state.hub.meta.skill_count;
  document.getElementById("count-projects").textContent = state.hub.meta.project_count;

  const live = String(state.hub.meta.note || "").startsWith("live");
  const protoBadge = document.querySelector(".proto-badge");
  if (protoBadge) protoBadge.style.display = live ? "none" : "";
  const footerNote = document.querySelector(".footer-note");
  if (footerNote) footerNote.textContent = live ? "live data" : "prototype — dummy data";
  const footerSep = document.querySelector(".footer .footer-sep");
  if (footerSep && footerSep.nextElementSibling && live) {
    footerSep.nextElementSibling.textContent = "rescans the hub every few seconds — reload to refresh";
  }

  if (!location.hash) location.hash = "#/hub";
  render();
}

boot().catch((err) => {
  view.textContent = "";
  view.appendChild(el("div", { class: "empty" },
    el("div", { class: "empty-title", text: "Failed to load" }),
    el("div", { text: String(err) })));
});
