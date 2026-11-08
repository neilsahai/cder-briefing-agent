"""Silent Playwright recording of the product: ask → trace → citation → row → pin → certify → briefing.
Produces deliverables/demo_walkthrough.webm (+ .mp4 via ffmpeg). Run with the API server on :8787."""
import asyncio, subprocess, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

BASE = "http://localhost:8787"
OUT = Path(__file__).resolve().parents[1] / "deliverables"

async def caption(page, text):
    await page.evaluate("""(t) => { let c = document.getElementById('__cap'); if (!c) { c = document.createElement('div'); c.id='__cap';
      c.style.cssText='position:fixed;left:24px;bottom:24px;max-width:70%;background:#16211D;color:#F6F7F5;padding:12px 16px;border-radius:10px;font:15px/1.4 IBM Plex Sans,system-ui;z-index:99999;box-shadow:0 6px 24px rgba(0,0,0,.25)';
      document.body.appendChild(c);} c.textContent = t; }""", text)

async def main():
    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 1440, "height": 900}, record_video_dir=str(OUT / "_video"), record_video_size={"width": 1440, "height": 900})
        page = await ctx.new_page()
        await page.goto(BASE + "/"); await page.wait_for_timeout(1500)
        await caption(page, "CDER Drug Shortage Briefing Agent — ask a question the way a hearing-prep analyst would.")
        await page.wait_for_timeout(2500)
        box = page.locator("textarea").first
        await box.click()
        await box.type("Is the amoxicillin shortage resolved?", delay=45)
        await caption(page, "Gate → planner → tools → narrator → Opus verifier. Every step streams into the trace.")
        await page.keyboard.press("Control+Enter")
        # wait for answer card
        t0 = time.time()
        while time.time() - t0 < 180:
            if await page.locator("button.cite").count():
                break
            await page.wait_for_timeout(1000)
        await page.wait_for_timeout(1500)
        await caption(page, "The answer: No. Latest revision is Current. The earlier Resolved record is disclosed, not ignored.")
        await page.wait_for_timeout(4000)
        chip = page.locator("button.cite").first
        if await chip.count():
            await chip.click(); await caption(page, "Click a citation → the evidence item → the exact CSV line it came from.")
            await page.wait_for_timeout(4000)
        for name in ["Verifier", "Interpretations", "Caveats"]:
            tab = page.locator(f"button:has-text('{name}')").first
            if await tab.count():
                await tab.click(); await caption(page, f"{name}: " + {"Verifier": "each atomic claim checked against evidence and source table by Opus.", "Interpretations": "every ambiguous term, the reading used, the alternate, and whether it changes the answer.", "Caveats": "data-audit warnings that attached themselves because the answer touched a flagged row."}[name])
                await page.wait_for_timeout(3500)
        await page.goto(BASE + "/certified"); await caption(page, "Certified-query registry: verified plans with who/when/version, promote and revoke audited.")
        await page.wait_for_timeout(4000)
        await page.goto(BASE + "/data"); await caption(page, "Data health: 13 audit rules over the snapshot, with the rows each finding touches.")
        await page.wait_for_timeout(4000)
        await page.goto(BASE + "/evals"); await caption(page, "Evals: measured pass rates, hallucinated-number rate, claims verified, cost per question.")
        await page.wait_for_timeout(4000)
        await page.goto(BASE + "/briefing"); await caption(page, "Briefing: pin answers, staff sign-off, readiness check, export to Word.")
        await page.wait_for_timeout(4000)
        await ctx.close(); await b.close()
    vids = sorted((OUT / "_video").glob("*.webm"), key=lambda f: f.stat().st_mtime)
    src = vids[-1]; dst = OUT / "demo_walkthrough.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", str(dst)], check=True)
    for f in (OUT / "_video").glob("*"): f.unlink()
    (OUT / "_video").rmdir()
    print("wrote", dst, dst.stat().st_size // 1024, "KB")

asyncio.run(main())
