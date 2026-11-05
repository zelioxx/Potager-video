// Outils communs pour les animations « Potager » (rendu déterministe : tout dépend de t).
const P = (() => {
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, k) => a + (b - a) * k;
  const prog = (t, a, b) => clamp((t - a) / (b - a));
  const easeOut = (k) => 1 - Math.pow(1 - k, 3);
  const easeIn = (k) => k * k * k;
  const easeInOut = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
  const easeOutBack = (k) => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const mix = (c1, c2, k) => { const a = hex(c1), b = hex(c2); return `rgb(${a.map((v, i) => Math.round(lerp(v, b[i], k))).join(',')})`; };
  function rng(seed) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  // Pop d'apparition : 0 → 1.1 → 1
  const pop = (t, t0, d = 0.28) => (t < t0 ? 0 : easeOutBack(prog(t, t0, t0 + d)));

  // ---- Scènes : [{id, start, end, zoom:[from,to]}]
  function scenes(list, t) {
    for (const s of list) {
      const el = document.getElementById(s.id);
      const on = t >= s.start && t < s.end;
      el.style.display = on ? 'block' : 'none';
      if (on) {
        const z = s.zoom || [1, 1.06];
        el.style.transform = `scale(${lerp(z[0], z[1], prog(t, s.start, s.end))})`;
      }
    }
  }

  // ---- Sous-titres
  // segments : [{start, end, chunks:["L'eau de *cuisson*", ...]}] — *mot* = surligné jaune.
  // Le temps du segment est réparti entre les morceaux au prorata des syllabes.
  const syll = (s) => Math.max(1, (s.toLowerCase().match(/[aeiouyàâäéèêëîïôöûùüœ]+/g) || []).length);
  function buildCaptions(segments) {
    const out = [];
    for (const seg of segments) {
      const w = seg.chunks.map(syll), tot = w.reduce((a, b) => a + b, 0);
      let t = seg.start;
      seg.chunks.forEach((c, i) => {
        const d = ((seg.end - seg.start) * w[i]) / tot;
        out.push({ start: t, end: i === seg.chunks.length - 1 ? seg.hold ?? seg.end + 0.15 : t + d, text: c });
        t += d;
      });
    }
    return out;
  }
  const fmt = (s) => s.replace(/\*([^*]+)\*/g, '<span class="k">$1</span>');
  let lastCap = null;
  function captions(caps, t) {
    const el = document.getElementById('caption');
    let cur = null;
    for (const c of caps) if (t >= c.start && t < c.end) cur = c;
    if (cur !== lastCap) { el.innerHTML = cur ? fmt(cur.text) : ''; lastCap = cur; }
    if (cur) { const k = easeOutBack(prog(t, cur.start, cur.start + 0.12)); el.style.transform = `scale(${lerp(0.88, 1, k)})`; }
  }

  // ---- Gros titres : [{text, start, end, top, size, rot}]
  function buildTitles(list) {
    const stage = document.getElementById('stage');
    list.forEach((ti, i) => {
      const d = document.createElement('div');
      d.className = 'title'; d.id = 'title' + i;
      d.style.top = (ti.top ?? 300) + 'px';
      d.style.fontSize = (ti.size ?? 130) + 'px';
      const html = ti.text.split('\n').map((l) => `<span>${l}</span>`).join('');
      d.innerHTML = `<div class="t-back">${html}</div><div class="t-front">${html}</div>`;
      stage.appendChild(d);
    });
  }
  function titles(list, t) {
    list.forEach((ti, i) => {
      const d = document.getElementById('title' + i);
      const on = t >= ti.start && t < ti.end;
      d.style.display = on ? 'block' : 'none';
      if (!on) return;
      const k = pop(t, ti.start, 0.3);
      const out = prog(t, ti.end - 0.12, ti.end);
      d.style.transform = `rotate(${ti.rot ?? -3}deg) scale(${k * (1 - out)})`;
    });
  }

  return { clamp, lerp, prog, easeOut, easeIn, easeInOut, easeOutBack, mix, rng, pop, scenes, buildCaptions, captions, buildTitles, titles };
})();
