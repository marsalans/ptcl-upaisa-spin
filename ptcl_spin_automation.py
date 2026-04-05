"""
PTCL Spin The Wheel Automation
================================
- Playwright (async) for browser automation
- ddddocr for free, offline CAPTCHA solving
- Logs all results to spin_results.csv
- Screenshots saved as artifacts in GitHub Actions

Config is read from environment variables (set as GitHub Secrets).
"""

import asyncio
import csv
import os
import re
from datetime import datetime
from pathlib import Path

import ddddocr
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────────
# CONFIG  (all read from env / GitHub Secrets)
# ─────────────────────────────────────────────
PTCL_NUMBER         = os.environ.get("PTCL_NUMBER", "03362336394")
SPIN_COUNT          = int(os.environ.get("SPIN_COUNT", "3"))
HEADLESS            = os.environ.get("HEADLESS", "true").lower() == "true"
DELAY_BETWEEN_SPINS = int(os.environ.get("SPIN_DELAY", "5"))
LOG_FILE            = "spin_results.csv"

LOGIN_URL = "https://my.ptcl.net.pk/SpinTheWheel/Default.aspx"
SPIN_URL  = "https://my.ptcl.net.pk/SpinTheWheel/SpinWheel.aspx"

# ─────────────────────────────────────────────
# CAPTCHA SOLVER  (ddddocr — free, offline)
# ─────────────────────────────────────────────
_ocr = None  # lazy-init so we only load the model once

def solve_captcha(image_bytes: bytes) -> str:
    global _ocr
    if _ocr is None:
        _ocr = ddddocr.DdddOcr(show_ad=False)
    result = _ocr.classification(image_bytes)
    # Keep only alphanumeric characters
    result = re.sub(r"[^A-Za-z0-9]", "", result)
    print(f"  [CAPTCHA] ddddocr solved: '{result}'")
    return result


# ─────────────────────────────────────────────
# RESULT LOGGER
# ─────────────────────────────────────────────
class ResultLogger:
    def __init__(self, filepath: str):
        self.filepath = filepath
        if not Path(filepath).exists():
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["spin_number", "timestamp", "result", "status"])

    def log(self, spin_num: int, result: str, status: str = "success"):
        with open(self.filepath, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([spin_num, datetime.now().isoformat(), result, status])
        print(f"  [LOG] Spin #{spin_num} -> {result} ({status})")


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
async def login(page: Page, spin_num: int) -> bool:
    print(f"\n[->] Loading login page...")
    await page.goto(LOGIN_URL, wait_until="networkidle")

    # Phone number
    for sel in ['input[name*="Phone"]', 'input[id*="Phone"]',
                'input[name*="phone"]', 'input[id*="phone"]',
                'input[type="text"]:first-of-type']:
        try:
            await page.fill(sel, PTCL_NUMBER, timeout=3000)
            print(f"  [OK] Phone filled ({sel})")
            break
        except Exception:
            continue
    else:
        print("  [!] Phone field not found")
        return False

    # CAPTCHA image
    captcha_el = None
    for sel in ['img[id*="captcha" i]', 'img[src*="captcha" i]',
                'img[id*="Captcha"]',   'img[class*="captcha" i]']:
        try:
            captcha_el = await page.wait_for_selector(sel, timeout=5000)
            if captcha_el:
                print(f"  [OK] CAPTCHA image found ({sel})")
                break
        except PlaywrightTimeout:
            continue

    if not captcha_el:
        print("  [!] CAPTCHA image not found")
        return False

    img_bytes = await captcha_el.screenshot()
    Path("screenshots").mkdir(exist_ok=True)
    Path(f"screenshots/captcha_spin{spin_num}.png").write_bytes(img_bytes)

    solved = solve_captcha(img_bytes)

    # CAPTCHA input
    for sel in ['input[name*="captcha" i]', 'input[id*="captcha" i]',
                'input[name*="Captcha"]',   'input[id*="Captcha"]']:
        try:
            await page.fill(sel, solved, timeout=3000)
            print(f"  [OK] CAPTCHA filled ({sel})")
            break
        except Exception:
            continue
    else:
        print("  [!] CAPTCHA input field not found")
        return False

    # Submit
    for sel in ['input[type="submit"]', 'button[type="submit"]',
                'input[value*="Start" i]', 'button:has-text("Start")',
                'input[value*="Game"  i]']:
        try:
            await page.click(sel, timeout=3000)
            print(f"  [OK] Submitted ({sel})")
            break
        except Exception:
            continue
    else:
        print("  [!] Submit button not found")
        return False

    # Wait for redirect to spin page
    try:
        await page.wait_for_url("**/SpinWheel.aspx**", timeout=15000)
        print("  [OK] Reached spin page!")
        return True
    except PlaywrightTimeout:
        print(f"  [!] Still on: {page.url}")
        await page.screenshot(path=f"screenshots/login_fail_spin{spin_num}.png")
        return False


# ─────────────────────────────────────────────
# SPIN
# ─────────────────────────────────────────────
async def spin_wheel(page: Page, spin_num: int) -> str:
    print("\n[->] Spinning the wheel...")
    await page.wait_for_load_state("networkidle")

    clicked = False
    for sel in ['input[value*="Spin" i]', 'button:has-text("Spin")',
                '#btnSpin', 'input[id*="Spin" i]',
                'button[id*="Spin" i]', '#SpinButton', 'a:has-text("Spin")']:
        try:
            await page.click(sel, timeout=4000)
            print(f"  [OK] Spin clicked ({sel})")
            clicked = True
            break
        except Exception:
            continue

    if not clicked:
        # Fallback: canvas wheel centre click
        try:
            canvas = await page.wait_for_selector("canvas", timeout=4000)
            bb = await canvas.bounding_box()
            await page.mouse.click(
                bb["x"] + bb["width"] / 2,
                bb["y"] + bb["height"] / 2
            )
            print("  [OK] Clicked canvas centre")
            clicked = True
        except Exception:
            pass

    if not clicked:
        return "ERROR: spin button not found"

    # Wait for animation to finish
    await asyncio.sleep(6)

    # Extract result text
    for sel in ['[id*="result" i]', '[id*="Result" i]',
                '[id*="prize"  i]', '[id*="Prize"  i]',
                '[id*="reward" i]', '#lblResult', '#lblPrize']:
        try:
            el   = await page.wait_for_selector(sel, timeout=5000)
            text = (await el.inner_text()).strip()
            if text:
                return text
        except PlaywrightTimeout:
            continue

    # Fallback: scan page body for win keywords
    body = await page.inner_text("body")
    for line in body.splitlines():
        line = line.strip()
        if any(kw in line.lower() for kw in
               ["congratulations", "you won", "prize", "mb", "reward", "free"]):
            return line

    return "Result not detected — check screenshot"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
async def run():
    logger = ResultLogger(LOG_FILE)
    Path("screenshots").mkdir(exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  PTCL Spin Automation")
    print(f"  Number  : {PTCL_NUMBER}")
    print(f"  Spins   : {SPIN_COUNT}")
    print(f"  Headless: {HEADLESS}")
    print(f"{'='*50}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        for spin_num in range(1, SPIN_COUNT + 1):
            print(f"\n{'-'*50}")
            print(f"  SPIN {spin_num} / {SPIN_COUNT}")
            print(f"{'-'*50}")
            page = await context.new_page()

            try:
                ok = await login(page, spin_num)
                if not ok:
                    logger.log(spin_num, "N/A", "login_failed")
                    await page.close()
                    continue

                result = await spin_wheel(page, spin_num)
                logger.log(spin_num, result)
                await page.screenshot(path=f"screenshots/result_spin{spin_num}.png")

            except Exception as exc:
                print(f"  [X] Error: {exc}")
                logger.log(spin_num, str(exc), "error")
                try:
                    await page.screenshot(path=f"screenshots/crash_spin{spin_num}.png")
                except Exception:
                    pass
            finally:
                await page.close()

            if spin_num < SPIN_COUNT:
                print(f"  [~] Waiting {DELAY_BETWEEN_SPINS}s...")
                await asyncio.sleep(DELAY_BETWEEN_SPINS)

        await browser.close()

    print(f"\n{'='*50}")
    print(f"  All done! Results -> {LOG_FILE}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    asyncio.run(run())
