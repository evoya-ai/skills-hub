#!/usr/bin/env python3
"""One-off probe: load #/projects directly and dump errors + DOM state."""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    msgs = []
    page.on("console", lambda m: msgs.append(f"console.{m.type}: {m.text}"))
    page.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
    page.goto(BASE + "#/projects", wait_until="networkidle")
    page.wait_for_timeout(500)
    print("errors/messages:")
    for m in msgs:
        print("  " + m)
    print("project cards:", page.locator(".project-card").count())
    print("view child count:", page.evaluate("document.getElementById('view').children.length"))
    print("view html head:", page.evaluate("document.getElementById('view').innerHTML.slice(0, 300)"))
    b.close()
