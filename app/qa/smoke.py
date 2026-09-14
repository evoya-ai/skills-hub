#!/usr/bin/env python3
"""Playwright smoke test + screenshots for the Skills Hub UI.

Data-driven: derives every expected number from /api/hub and /api/projects,
so it works against real hub data AND --dummy mode.

Run:  uv run --with playwright python app/qa/smoke.py [--base http://127.0.0.1:8765]
Writes screenshots + report into migration/ui-qa/. Exits non-zero on failure.
"""

import argparse
import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).resolve().parents[2] / "migration" / "ui-qa"
FAILURES = []


def check(cond, label):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        FAILURES.append(label)


def get_json(base, path):
    with urllib.request.urlopen(base + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    hub = get_json(args.base, "/api/hub")
    projects = get_json(args.base, "/api/projects")["projects"]
    meta = hub["meta"]
    n_sources = len(hub["sources"])
    n_projects = len(projects)
    n_links = sum(len(p["linked"]) for p in projects)
    n_local = sum(len(p["local"]) for p in projects)
    n_untrusted = sum(1 for s in hub["sources"] if s["untrusted"])

    # first skill (in DOM order) that is linked by at least one project
    anchor = None
    for src in hub["sources"]:
        for cat in src["categories"]:
            for sk in cat["skills"]:
                if sk["linked_by"]:
                    anchor = {"src": src["name"], "cat": cat["name"], **sk}
                    break
            if anchor:
                break
        if anchor:
            break
    assert anchor, "no linked skill found in API data — nothing to drive the flow with"

    print(f"data: {n_sources} sources, {meta['skill_count']} skills, "
          f"{n_projects} projects, {n_links} links, {n_local} local; "
          f"anchor skill: {anchor['id']}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        print("== hub view ==")
        page.goto(args.base, wait_until="networkidle")
        page.evaluate("document.querySelector('.topbar').style.position = 'static'")  # capture fidelity
        check(page.locator(".tab[aria-selected=true]").get_attribute("data-view") == "hub", "hub tab selected on load")
        check(page.locator(".stat-pill").count() == 4, "4 stat pills shown")
        check(page.locator(".source-card").count() == n_sources, f"{n_sources} source cards")
        check(page.locator(".tree-card .tree").count() == 1, "hub layout tree shown")
        check(page.locator(".badge.untrusted").count() == n_untrusted, f"{n_untrusted} untrusted badge(s)")
        check(page.locator(".category.open").count() == 0, "categories collapsed by default")
        check(not page.locator(".proto-badge").is_visible() if meta["note"].startswith("live")
              else page.locator(".proto-badge").is_visible(),
              "prototype badge matches data mode")

        print("== repo expand/collapse ==")
        first_src = page.locator(".source-card").first
        first_src.locator(".source-toggle").click()
        page.wait_for_timeout(150)
        check(first_src.evaluate("n => n.classList.contains('collapsed')"), "repo collapses via +/- button")
        page.screenshot(path=str(OUT / "11-hub-source-collapsed.png"), full_page=True)
        first_src.locator(".source-count").click()
        page.wait_for_timeout(150)
        check(first_src.evaluate("n => !n.classList.contains('collapsed')"), "repo re-expands via skills count text")

        print("== anchor category: cards + expand ==")
        cat_head = page.locator(f'.source-card[data-source="{anchor["src"]}"] .category-head',
                                has_text=anchor["cat"]).first
        cat_head.click()
        page.wait_for_timeout(150)
        card = page.locator(f'.skill[data-skill-id="{anchor["id"]}"]').first
        check(card.is_visible(), "anchor skill card visible after opening its category")
        collapsed_clamp = card.locator(".skill-desc").evaluate("n => getComputedStyle(n).webkitLineClamp")
        check(collapsed_clamp == "2", f"description clamped to 2 lines (got {collapsed_clamp})")
        card.click()
        page.wait_for_timeout(150)
        check("expanded" in (card.get_attribute("class") or ""), "skill card expands on click")
        expanded_clamp = card.locator(".skill-desc").evaluate("n => getComputedStyle(n).webkitLineClamp")
        check(expanded_clamp == "none", f"clamp released when expanded (got {expanded_clamp})")
        page.screenshot(path=str(OUT / "02-hub-expanded.png"), full_page=True)
        page.screenshot(path=str(OUT / "01-hub-collapsed.png"), full_page=False)  # above-fold view

        print("== skill detail view (SKILL.md) ==")
        card.locator(".skill-name a").click()
        page.wait_for_timeout(400)
        check("#/skill/" in page.url, "skill name link opens SKILL.md view")
        check(page.locator(".skill-hero .skill-title").inner_text() == anchor["name"], "hero shows the skill name")
        md_text = page.locator(".md").inner_text()
        check(len(md_text.strip()) > 50, f"markdown body rendered ({len(md_text)} chars)")
        check(page.locator(".md h2, .md h3, .md h4").count() >= 1, "markdown headings rendered")
        check(not md_text.lstrip().startswith("---"), "frontmatter stripped")
        page.screenshot(path=str(OUT / "10-skill-view.png"), full_page=True)
        page.locator(".crumb").click()
        page.wait_for_timeout(300)
        check("#/hub" in page.url, "breadcrumb returns to hub")

        print("== cross-navigation: skill -> projects ==")
        page.locator(f'.source-card[data-source="{anchor["src"]}"] .category-head',
                     has_text=anchor["cat"]).first.click()
        page.wait_for_timeout(150)
        page.locator(f'.skill[data-skill-id="{anchor["id"]}"] .linked-by').first.click()
        page.wait_for_timeout(400)
        check("#/projects" in page.url, "navigated to projects view")
        check(page.locator(".project-card").count() == n_projects, f"{n_projects} project cards")
        check(page.locator(".chip.flash").count() >= 1, "linked chips flash for focused skill")

        print("== cross-navigation: chip -> SKILL.md -> back ==")
        page.locator(".project-card .chip.linked").first.click()
        page.wait_for_timeout(400)
        check("#/skill/" in page.url, "chip opens the skill detail view")
        page.locator(".skill-hero .linked-by").first.click()
        page.wait_for_timeout(400)
        check("#/projects" in page.url, "linked-by from skill view goes to projects")
        page.screenshot(path=str(OUT / "03-projects-flash.png"), full_page=True)

        print("== projects view ==")
        page.locator("#tab-projects").click()
        page.wait_for_timeout(250)
        check(page.locator(".legend").count() == 1, "legend shown")
        check(page.locator(".legend .dot-label").count() == 3, "legend explains source dot colors")
        check(page.locator(".project-card .chip.linked[data-skill-id]").count() == n_links, f"{n_links} linked chips")
        check(page.locator(".project-card .chip.local").count() == n_local, f"{n_local} local chips")
        page.screenshot(path=str(OUT / "04-projects.png"), full_page=True)

        print("== search (hub) ==")
        term = anchor["name"].split("-")[0].lower()
        expected_hub = sum(
            1 for s in hub["sources"] for c in s["categories"] for sk in c["skills"]
            if term in sk["name"].lower() or term in (sk["description"] or "").lower())
        page.locator("#tab-hub").click()
        page.wait_for_timeout(250)
        page.fill("#search", term)
        page.wait_for_timeout(250)
        got = page.locator(".skill").count()
        check(got == expected_hub, f"search '{term}' filters hub to {expected_hub} cards (got {got})")
        pill = page.locator(".stats-row .stat-pill").first.inner_text().replace("\u00a0", " ")
        check(f"{expected_hub} / {meta['skill_count']}" in pill, f"stats pill shows match count ({pill.strip()})")
        page.screenshot(path=str(OUT / "06-hub-search.png"), full_page=True)

        print("== search (projects) ==")
        pterm = projects[0]["name"].lower()[:6]
        expected_proj = sum(
            1 for pr in projects
            if pterm in pr["name"].lower() or pterm in pr["path"].lower()
            or any(pterm in s["name"].lower() for s in pr["linked"])
            or any(pterm in s["name"].lower() for s in pr["local"]))
        page.locator("#tab-projects").click()
        page.wait_for_timeout(250)
        page.fill("#search", pterm)
        page.wait_for_timeout(250)
        gotp = page.locator(".project-card").count()
        check(gotp == expected_proj, f"search '{pterm}' filters projects to {expected_proj} cards (got {gotp})")
        page.screenshot(path=str(OUT / "05-projects-search.png"), full_page=True)

        print("== empty state + clear button ==")
        page.fill("#search", "zzzz-no-such-thing")
        page.wait_for_timeout(250)
        check(page.locator(".empty").count() == 1, "empty state for nonsense query")
        page.screenshot(path=str(OUT / "07-empty.png"))
        check(page.locator("#clear-btn").is_visible(), "styled clear button visible when search not empty")
        page.click("#clear-btn")
        page.wait_for_timeout(250)
        check(page.locator("#clear-btn").is_hidden(), "clear button hides after clearing")
        check(page.locator(".project-card").count() == n_projects, "clearing restores all projects")

        print("== mobile viewport ==")
        mp = browser.new_page(viewport={"width": 390, "height": 844})
        mp.on("pageerror", lambda e: console_errors.append(str(e)))
        mp.goto(args.base, wait_until="networkidle")
        mp.evaluate("document.querySelector('.topbar').style.position = 'static'")
        mp.screenshot(path=str(OUT / "08-mobile-hub.png"), full_page=True)
        mp.locator("#tab-projects").click()
        mp.wait_for_timeout(250)
        mp.screenshot(path=str(OUT / "09-mobile-projects.png"), full_page=True)
        mp.close()
        browser.close()

    print("\n== console ==")
    if console_errors:
        for e in console_errors[:10]:
            print(f"  [FAIL] console error: {e}")
        FAILURES.extend(console_errors[:10])
    else:
        print("  [PASS] no console errors / page errors")

    (OUT / "report.json").write_text(json.dumps({
        "failures": FAILURES,
        "data": {"sources": n_sources, "skills": meta["skill_count"],
                 "projects": n_projects, "links": n_links, "local": n_local},
        "screenshots": sorted(f.name for f in OUT.glob("*.png")),
    }, indent=2))
    print(f"\nreport: {OUT / 'report.json'}")
    if FAILURES:
        print(f"\n{len(FAILURES)} FAILURE(S)")
        sys.exit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
