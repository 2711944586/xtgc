from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
SCREENSHOTS_DIR = ROOT / "reports" / "screenshots"
RUNTIME_DIR = ROOT / "tmp" / "playwright-runtime"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def ensure_playwright_runtime() -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm is required to install the local Playwright runtime")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    package_json = RUNTIME_DIR / "package.json"
    if not package_json.exists():
        package_json.write_text('{"private":true,"type":"commonjs"}\n', encoding="utf-8")
    if not (RUNTIME_DIR / "node_modules" / "playwright").exists():
        subprocess.run(
            [npm, "install", "--no-audit", "--no-fund", "playwright"],
            cwd=RUNTIME_DIR,
            check=True,
        )


def write_capture_script(path: Path) -> None:
    script = r"""
const { chromium } = require('playwright');
const fs = require('fs');

const url = process.argv[2];
const outDir = process.argv[3];
fs.mkdirSync(outDir, { recursive: true });

async function waitForReady(page) {
  await page.waitForSelector('#flight-count');
  await page.waitForFunction(() => {
    const count = document.querySelector('#flight-count')?.textContent || '';
    return count.trim() && !count.includes('--') && !count.includes('加载');
  }, null, { timeout: 20000 });
  await page.waitForTimeout(900);
}

async function setDemoState(page) {
  await page.locator('#scenario-select').selectOption('weather').catch(() => {});
  await page.waitForTimeout(120);
  await page.locator('#shock-airport-select').selectOption('DFW').catch(() => {});
  await page.waitForTimeout(120);
  await page.locator('#strategy-select').selectOption('dynamic_combo').catch(() => {});
  await page.locator('#airport-select').selectOption('MIA').catch(() => {});
  await page.locator('#lambda-input').evaluate((el) => {
    el.value = '0.2';
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }).catch(() => {});
  await page.waitForTimeout(500);
}

async function screenshotSections(page) {
  await page.addStyleTag({
    content: `
      html { scroll-behavior: auto !important; }
      .topbar, .presentation-dock, .demo-caption, .demo-cursor { display: none !important; }
      body { padding-top: 0 !important; }
      .section, .hero { scroll-margin-top: 0 !important; }
    `
  });
  const sections = [
    ['#overview', 'screen_01_home.png'],
    ['#dashboard', 'screen_02_dashboard.png'],
    ['#prediction', 'screen_03_prediction.png'],
    ['#network', 'screen_04_network.png'],
    ['#simulation', 'screen_05_simulation.png'],
    ['#decision', 'screen_06_decision.png'],
    ['#method', 'screen_07_method.png'],
  ];
  for (const [selector, name] of sections) {
    const loc = page.locator(selector);
    await loc.scrollIntoViewIfNeeded();
    await page.waitForTimeout(350);
    await loc.screenshot({ path: `${outDir}/${name}` });
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });

  const desktop = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
  await desktop.goto(url, { waitUntil: 'networkidle' });
  await waitForReady(desktop);
  await setDemoState(desktop);
  await desktop.screenshot({ path: `${outDir}/static_web_desktop.png` });
  await desktop.screenshot({ path: `${outDir}/static_web_fullpage.png`, fullPage: true });
  await screenshotSections(desktop);

  const mobile = await browser.newPage({ viewport: { width: 390, height: 980 }, isMobile: true, deviceScaleFactor: 2 });
  await mobile.goto(url, { waitUntil: 'networkidle' });
  await waitForReady(mobile);
  await mobile.screenshot({ path: `${outDir}/static_web_mobile.png`, fullPage: true });

  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
"""
    path.write_text(textwrap.dedent(script).strip() + "\n", encoding="utf-8")


def main() -> None:
    ensure_playwright_runtime()
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    port = find_free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "-d", str(WEB_DIR)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    script_path = RUNTIME_DIR / "capture_web_screenshots.cjs"
    write_capture_script(script_path)
    try:
        time.sleep(1.0)
        subprocess.run(
            ["node", str(script_path), f"http://127.0.0.1:{port}/", str(SCREENSHOTS_DIR)],
            cwd=RUNTIME_DIR,
            check=True,
        )
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        script_path.unlink(missing_ok=True)
    print(SCREENSHOTS_DIR)


if __name__ == "__main__":
    main()
