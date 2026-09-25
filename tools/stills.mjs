// One still per beat (or custom times) → out/stills/*.png, for checking the grid before a full render.
// usage: node tools/stills.mjs [offset=0.3] | node tools/stills.mjs --at 4.2 6.7 ...
import { mkdirSync, writeFileSync } from 'node:fs';
import { openScene } from './page.mjs';

const args = process.argv.slice(2);
const times = args[0] === '--at'
  ? args.slice(1).map(Number)
  : Array.from({ length: 28 }, (_, b) => b * 0.5 + Number(args[0] ?? 0.3));
mkdirSync('out/stills', { recursive: true });
const { browser, pages, shot } = await openScene();
for (const t of times) {
  const name = `out/stills/t${t.toFixed(3).padStart(6, '0')}.png`;
  writeFileSync(name, await shot(pages[0], t));
  console.log(name);
}
await browser.close();
