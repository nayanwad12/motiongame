// Shared: open motion.html in headless Chromium at 1440×1440, ready to seek.
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { mkdirSync, writeFileSync } from 'node:fs';

export async function openScene(n = 1) {
  const browser = await chromium.launch();
  const url = pathToFileURL(resolve('motion.html')).href + '?render';
  const pages = [];
  for (let i = 0; i < n; i++) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1440 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
    page.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
    await page.goto(url);
    await page.evaluate(() => window.ready);
    pages.push(page);
  }
  // sound cues live in the scene; export them for tools/audio.py
  mkdirSync('out', { recursive: true });
  writeFileSync('out/cues.json', JSON.stringify(await pages[0].evaluate(() => window.CUES)));
  const shot = async (page, t) => {
    await page.evaluate(t => window.seek(t), t);
    return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1440, height: 1440 } });
  };
  return { browser, pages, shot };
}
