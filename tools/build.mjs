// Inline Geist into the scene so the deliverable is one self-contained HTML file.
import { readFileSync, writeFileSync } from 'node:fs';
const font = readFileSync(new URL('../node_modules/geist/dist/fonts/geist-sans/Geist-Variable.woff2', import.meta.url));
const src = readFileSync(new URL('../src/scene.html', import.meta.url), 'utf8');
writeFileSync(new URL('../motion.html', import.meta.url),
  src.replace('__GEIST__', 'data:font/woff2;base64,' + font.toString('base64')));
console.log('built motion.html');
