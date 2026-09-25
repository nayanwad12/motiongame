// Full render: 840 frames × 4 subframes → ffmpeg tmix (motion blur) → 60 fps H.264 + audio.
// usage: node tools/render.mjs [--audio out/audio.wav] [--out out/motion.mp4] [--workers 3]
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { openScene } from './page.mjs';

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const FPS = 60, SUB = 4, SHUTTER = 0.5;            // 180° shutter, 4 samples spread across it
const AUDIO = arg('--audio', 'out/audio.wav'), OUT = arg('--out', 'out/motion.mp4');
const WORKERS = Number(arg('--workers', 3));

const { browser, pages, shot } = await openScene(WORKERS);
const T = await pages[0].evaluate(() => window.DURATION);
const FRAMES = Math.round(T * FPS);                // frame FRAMES would equal frame 0 → loop point
const times = f => Array.from({ length: SUB }, (_, s) => f / FPS + ((s + .5) / SUB - .5) * SHUTTER / FPS);

const ff = spawn('ffmpeg', [
  '-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS * SUB), '-c:v', 'png', '-i', '-',
  ...(existsSync(AUDIO) ? ['-i', AUDIO] : []),
  '-vf', `tmix=frames=${SUB}:weights='${Array(SUB).fill(1).join(' ')}',select='eq(mod(n\\,${SUB})\\,${SUB - 1})',setpts=N/(${FPS}*TB)`,
  '-r', String(FPS), '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
  ...(existsSync(AUDIO) ? ['-c:a', 'aac', '-b:a', '320k', '-t', String(T)] : []),
  OUT,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const write = buf => new Promise(r => ff.stdin.write(buf) ? r() : ff.stdin.once('drain', r));

const done = new Map();
let next = 0, written = 0;
const t0 = Date.now();
async function worker(page) {
  while (true) {
    const f = next++;
    if (f >= FRAMES) return;
    while (f - written > 24) await new Promise(r => setTimeout(r, 5));
    const bufs = [];
    for (const t of times(f)) bufs.push(await shot(page, t));
    done.set(f, bufs);
    while (done.has(written)) {
      for (const b of done.get(written)) await write(b);
      done.delete(written++);
      if (written % 60 === 0) console.log(`frame ${written}/${FRAMES}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }
}
await Promise.all(pages.map(worker));
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log(`wrote ${OUT} (${FRAMES} frames @ ${FPS} fps, ${SUB} subframes each)`);
