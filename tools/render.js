#!/usr/bin/env node
// Rendu image par image d'une page HTML animée (window.seek(t), window.DURATION)
// puis assemblage avec la voix off via ffmpeg.
//
// Usage : node tools/render.js <page.html> <voix.mp3> <sortie.mp4> [--fps 30] [--from 0] [--to DURATION] [--preview]
//   --preview : rendu rapide en 540x960 pour vérifier le montage.

const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : def;
}

(async () => {
  const [html, audio, out] = process.argv.slice(2);
  if (!html || !audio || !out) {
    console.error('Usage : node tools/render.js <page.html> <voix.mp3> <sortie.mp4>');
    process.exit(1);
  }
  const fps = Number(arg('--fps', 30));
  const preview = process.argv.includes('--preview');
  const scale = preview ? 0.5 : 1;

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: scale });
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
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

  for (let i = 0; i < n; i++) {
    const t = from + i / fps;
    await page.evaluate((t) => window.seek(t), t);
    const buf = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % 60 === 0) process.stdout.write(`\r${i}/${n} images`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  await browser.close();
  console.log(`\nOK → ${out}`);
})();
