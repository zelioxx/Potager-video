// Couche 3D (three.js) posée au-dessus des photos : texte 3D, vapeur, pluie, gouttes, cristaux, bulles, logo.
// Tout est déterministe : chaque élément est recalculé à partir du temps t (rendu image par image).
import * as THREE from 'three';
import { TTFLoader } from 'three/addons/loaders/TTFLoader.js';
import { Font } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';

export const W = 1080, H = 1920;
export const VERT = 0x1d3828, JAUNE = 0xfed14a, BLANC = 0xffffff;

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const prog = (t, a, b) => clamp((t - a) / (b - a));
export const easeOut = (k) => 1 - Math.pow(1 - k, 3);
export const easeIn = (k) => k * k * k;
export const easeInOut = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
export const easeOutBack = (k) => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
export const pop = (t, t0, d = 0.3) => (t < t0 ? 0 : easeOutBack(prog(t, t0, t0 + d)));
export function rng(seed) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
// hash déterministe (i, k) -> [0,1)
export const hrand = (i, k = 0) => { const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };

// Coordonnées écran (px, origine en haut à gauche) -> monde
export const P = (x, y, z = 0) => new THREE.Vector3(x - W / 2, H / 2 - y, z);

export class Stage3D {
  constructor(canvas) {
    this.renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(window.devicePixelRatio || 1);
    this.renderer.setSize(W, H, false);
    this.renderer.setClearColor(0x000000, 0);
    this.scene = new THREE.Scene();
    const fov = 30;
    this.camera = new THREE.PerspectiveCamera(fov, W / H, 10, 20000);
    this.camera.position.set(0, 0, (H / 2) / Math.tan((fov / 2) * Math.PI / 180));
    this.scene.add(new THREE.AmbientLight(0xffffff, 1.6));
    const key = new THREE.DirectionalLight(0xffffff, 2.6); key.position.set(-600, 900, 1400); this.scene.add(key);
    const rim = new THREE.DirectionalLight(0xfff3d6, 1.2); rim.position.set(800, -300, 600); this.scene.add(rim);
    this.groups = [];
  }
  add(obj) { this.scene.add(obj); return obj; }
  render() { this.renderer.render(this.scene, this.camera); }
}

export function loadFont(url) {
  return new Promise((res, rej) => new TTFLoader().load(url, (json) => res(new Font(json)), undefined, rej));
}

const matCache = {};
export function mat(color, { emissive = 0.28, rough = 0.42, metal = 0.0 } = {}) {
  const k = `${color}-${emissive}-${rough}-${metal}`;
  if (!matCache[k]) {
    const c = new THREE.Color(color);
    matCache[k] = new THREE.MeshStandardMaterial({ color: c, emissive: c.clone().multiplyScalar(emissive), roughness: rough, metalness: metal });
  }
  return matCache[k];
}

// ---------------- Texte 3D ----------------
// lines : ["L'eau de *cuisson*", ...] — *mot* = couleur clé. Renvoie un Group centré.
export function text3D(font, lines, { size = 60, depth = 14, outline = 7, front = BLANC, key = JAUNE, side = VERT, lineHeight = 1.18, upper = false } = {}) {
  const g = new THREE.Group();
  if (typeof lines === 'string') lines = lines.split('\n');
  const space = size * 0.3 + 2 * outline;
  lines.forEach((line, li) => {
    if (upper) line = line.toUpperCase();
    // tokens : morceaux de texte de même couleur ; spaceBefore = un espace les précède
    const tokens = [];
    let pendingSpace = false;
    line.split(/(\*[^*]+\*)/).forEach((part) => {
      if (!part) return;
      const isKey = part.startsWith('*');
      const txt = isKey ? part.slice(1, -1) : part;
      txt.split(/( )/).forEach((w) => {
        if (w === ' ') { pendingSpace = true; return; }
        if (!w) return;
        tokens.push({ w, isKey, spaceBefore: pendingSpace && tokens.length > 0 });
        pendingSpace = false;
      });
    });
    const lineG = new THREE.Group();
    let x = 0;
    tokens.forEach((tk) => {
      if (tk.spaceBefore) x += space;
      const geo = new TextGeometry(tk.w, { font, size, depth, curveSegments: 5, bevelEnabled: false });
      geo.computeBoundingBox();
      const w = geo.boundingBox.max.x - geo.boundingBox.min.x;
      const m = new THREE.Mesh(geo, [mat(tk.isKey ? key : front), mat(side, { emissive: 0.15 })]);
      m.position.x = x - geo.boundingBox.min.x;
      lineG.add(m);
      if (outline > 0) {
        const og = new TextGeometry(tk.w, { font, size, depth, curveSegments: 5, bevelEnabled: true, bevelThickness: 2, bevelSize: outline, bevelSegments: 2 });
        const om = new THREE.Mesh(og, mat(side, { emissive: 0.1 }));
        om.position.set(m.position.x, 0, -3);
        lineG.add(om);
      }
      x += w + size * 0.02;
    });
    lineG.position.x = -x / 2;
    lineG.position.y = -li * size * lineHeight;
    g.add(lineG);
  });
  // centre vertical
  const n = lines.length;
  g.children.forEach((c) => { c.position.y += ((n - 1) * size * lineHeight) / 2 - size * 0.36; });
  const box = new THREE.Box3().setFromObject(g);
  g.userData.width = box.max.x - box.min.x;
  return g;
}

// ---------------- Textures ----------------
export function softTexture(inner = 'rgba(255,255,255,1)', outer = 'rgba(255,255,255,0)') {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const x = c.getContext('2d'); const gr = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, inner); gr.addColorStop(0.45, inner.replace(/[\d.]+\)$/, '0.45)')); gr.addColorStop(1, outer);
  x.fillStyle = gr; x.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// ---------------- Vapeur / fumée ----------------
// Sprites recalculés à chaque image. opts : {x, y, spread, rise, life, rate, size, opacity, tint}
export class Smoke {
  constructor(stage, n = 70, tint = 0xffffff) {
    this.tex = softTexture();
    this.sprites = [];
    for (let i = 0; i < n; i++) {
      const m = new THREE.SpriteMaterial({ map: this.tex, color: tint, transparent: true, depthWrite: false, opacity: 0 });
      const s = new THREE.Sprite(m); s.visible = false; stage.add(s); this.sprites.push(s);
    }
  }
  hide() { this.sprites.forEach((s) => (s.visible = false)); }
  update(t, { x, y, spread = 200, rise = 520, life = 2.4, size = 180, opacity = 0.55, strength = 1, wind = 40, t0 = -10 }) {
    const n = this.sprites.length;
    this.sprites.forEach((s, i) => {
      const birth = t0 - life + (i / n) * life + Math.floor((t - t0) / life) * life; // naissance périodique
      let age = (t - birth) % life; if (age < 0) age += life;
      const k = age / life;
      const born = t - age;
      if (born < t0 - life * 0.02) { s.visible = false; return; }
      const r1 = hrand(i, 1), r2 = hrand(i, 2), r3 = hrand(i, 3);
      const px = x + (r1 - 0.5) * spread + Math.sin(k * 5 + i) * 30 * k + wind * k;
      const py = y - rise * easeOut(k) * (0.7 + 0.5 * r2);
      s.position.copy(P(px, py, 50 + r3 * 40));
      const sc = size * (0.5 + 1.4 * k) * (0.8 + 0.4 * r3);
      s.scale.set(sc, sc, 1);
      s.material.opacity = opacity * strength * Math.sin(Math.PI * Math.min(1, k * 1.15)) * (0.6 + 0.4 * r2);
      s.material.rotation = r1 * 6 + k * (r2 - 0.5) * 2;
      s.visible = s.material.opacity > 0.003;
    });
  }
}

// ---------------- Gouttes / pluie / cristaux (InstancedMesh) ----------------
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _up = new THREE.Vector3(0, 1, 0), _v = new THREE.Vector3();
export class Instanced {
  constructor(stage, geo, material, n) {
    this.mesh = new THREE.InstancedMesh(geo, material, n);
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.mesh.frustumCulled = false;
    this.n = n; stage.add(this.mesh); this.hide();
  }
  hide() { for (let i = 0; i < this.n; i++) this.set(i, null); this.mesh.instanceMatrix.needsUpdate = true; this.mesh.visible = false; }
  // st : {x,y,z, sx,sy,sz, dir:[vx,vy] (orientation), rot:[rx,ry,rz]}
  set(i, st) {
    if (!st) { _m.makeScale(0, 0, 0); this.mesh.setMatrixAt(i, _m); return; }
    const p = P(st.x, st.y, st.z || 80);
    if (st.dir) { _v.set(st.dir[0], -st.dir[1], 0).normalize(); _q.setFromUnitVectors(_up, _v); }
    else if (st.rot) _q.setFromEuler(new THREE.Euler(...st.rot));
    else _q.identity();
    _s.set(st.sx, st.sy ?? st.sx, st.sz ?? st.sx);
    _m.compose(p, _q, _s); this.mesh.setMatrixAt(i, _m);
  }
  update(fn) { this.mesh.visible = true; for (let i = 0; i < this.n; i++) this.set(i, fn(i)); this.mesh.instanceMatrix.needsUpdate = true; }
}

export function waterMaterial() {
  return new THREE.MeshPhysicalMaterial({ color: 0xe8f3f8, emissive: 0x6a8a99, emissiveIntensity: 0.25, roughness: 0.05, metalness: 0, clearcoat: 1, transparent: true, opacity: 0.82 });
}
export function saltMaterial() {
  return new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x9a9a9a, roughness: 0.25, metalness: 0.05 });
}
export function rainMaterial() {
  return new THREE.MeshBasicMaterial({ color: 0xbfd6ff, transparent: true, opacity: 0.55, depthWrite: false });
}

// Courbe de Bézier quadratique (pour les filets d'eau)
export const bez = (p0, p1, p2, u) => [
  (1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
  (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1],
];
export const bezD = (p0, p1, p2, u) => [2 * (1 - u) * (p1[0] - p0[0]) + 2 * u * (p2[0] - p1[0]), 2 * (1 - u) * (p1[1] - p0[1]) + 2 * u * (p2[1] - p1[1])];

// ---------------- Bulle 3D avec lettres ----------------
export function bubble(font, label, r = 64) {
  const g = new THREE.Group();
  const s = new THREE.Mesh(new THREE.SphereGeometry(r, 48, 32),
    new THREE.MeshPhysicalMaterial({ color: JAUNE, emissive: 0x7a5a00, emissiveIntensity: 0.35, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.08 }));
  g.add(s);
  const t = text3D(font, [label], { size: label.length > 1 ? r * 0.62 : r * 0.78, depth: 8, outline: 0, front: VERT, side: VERT });
  t.position.z = r + 6; g.add(t);
  return g;
}

// ---------------- Carte logo 3D ----------------
export function logoCard(img, size = 600) {
  const tex = new THREE.Texture(img); tex.colorSpace = THREE.SRGBColorSpace; tex.needsUpdate = true; tex.anisotropy = 4;
  const side = new THREE.MeshStandardMaterial({ color: 0x2f6b3a, roughness: 0.5 });
  const face = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.55, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: 0.35 });
  return new THREE.Mesh(new THREE.BoxGeometry(size, size, 28), [side, side, side, side, face, face]);
}

// ---------------- Panneau « interdit » 3D ----------------
export function banSign(r = 250) {
  const red = new THREE.MeshStandardMaterial({ color: 0xd2382c, emissive: 0x5a0e08, roughness: 0.35 });
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.TorusGeometry(r, r * 0.12, 24, 96), red));
  const bar = new THREE.Mesh(new THREE.BoxGeometry(r * 2, r * 0.22, r * 0.2), red);
  bar.rotation.z = -Math.PI / 4; g.add(bar);
  return g;
}
