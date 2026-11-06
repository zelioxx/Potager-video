#!/usr/bin/env node
// Rendu image par image d'une page HTML animée (window.seek(t), window.DURATION, window.READY optionnel)
// puis assemblage avec l'audio via ffmpeg. La page est servie en HTTP local (modules ES, three.js).
//
// Usage : node tools/render.js <page.html> <audio> <sortie.mp4> [--fps 30] [--from 0] [--to DURATION] [--preview]
//         node tools/render.js <page.html> --snap <dossier> t1 t2 ...   (captures de contrôle en 540x960)

const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml',
  '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.woff': 'font/woff', '.mp4': 'video/mp4' };

function serve() {
  return new Promise((res) => {
    const srv = http.createServer((req, rsp) => {
      const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(p).toLowerCase()] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(rsp);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

function arg(name, def) { const i = process.argv.indexOf(name); return i > -1 ? process.argv[i + 1] : def; }

async function openPage(html, scale) {
  const srv = await serve();
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: scale });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  const url = `http://127.0.0.1:${srv.address().port}/${path.relative(ROOT, path.resolve(html)).split(path.sep).join('/')}`;
  await page.goto(url);
  await page.evaluate(async () => { await document.fonts.ready; if (window.READY) await window.READY; });
  if (errors.length) console.error('Erreurs page :\n' + errors.join('\n'));
  return { page, browser, srv, errors };
}

(async () => {
  const [html, audio, out] = process.argv.slice(2);
  if (!html) { console.error('Usage : node tools/render.js <page.html> <audio> <sortie.mp4>'); process.exit(1); }

  if (audio === '--snap') {
    const dir = out; fs.mkdirSync(dir, { recursive: true });
    const { page, browser, srv } = await openPage(html, 0.5);
    for (const t of process.argv.slice(5)) {
      await page.evaluate((t) => window.seek(t), Number(t));
      await page.screenshot({ path: path.join(dir, `s_${Number(t).toFixed(2).padStart(6, '0')}.png`) });
    }
    await browser.close(); srv.close(); return;
  }

  const fps = Number(arg('--fps', 30));
  const preview = process.argv.includes('--preview');
  const { page, browser, srv } = await openPage(html, preview ? 0.5 : 1);
  const duration = Number(arg('--to', await page.evaluate(() => window.DURATION)));
  const from = Number(arg('--from', 0));
  const n = Math.round((duration - from) * fps);

  const ff = spawn('ffmpeg', [
    '-y', '-v', 'error',
    '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-ss', String(from), '-i', audio,
    '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-preset', preview ? 'veryfast' : 'slow', '-crf', preview ? '28' : '18',
    '-pix_fmt', 'yuv420p', '-r', String(fps),
    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',
    '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',
    '-t', String(duration - from), '-movflags', '+faststart', out,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });

  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    const t = from + i / fps;
    await page.evaluate((t) => window.seek(t), t);
    const buf = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % 30 === 0) process.stdout.write(`\r${i}/${n} images (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  await browser.close(); srv.close();
  console.log(`\nOK → ${out}`);
})();
