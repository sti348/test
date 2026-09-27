// Plays film.json (compiled by tools/compile.py) on a Stage: actors, props,
// camera, block changes, particles, overlays, subtitles and titles.
import * as THREE from 'three';
import { PlayerModel, loadSkinTexture } from './player.js';
import { loadItemModel, itemMesh, itemDisplayMatrix, heldMatrix, displayMatrix, pixelTexture } from './mcmodel.js';
import { aimCamera } from './stage.js';
THREE.ColorManagement.enabled = false;

const DEG = Math.PI / 180;

function findRow(rows, t) {
  let lo = 0, hi = rows.length - 1, ans = -1;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (rows[m][0] <= t) { ans = m; lo = m + 1; } else hi = m - 1; }
  return ans;
}
// keyframe rows [t, v0, v1, ...] or [t, null]; returns interpolated values or null
export function sampleTrack(rows, t, jump = 2.5) {
  if (!rows || !rows.length) return null;
  const i = findRow(rows, t);
  if (i < 0) return null;
  const a = rows[i];
  if (a[1] === null) return null;
  const b = rows[i + 1];
  if (!b || b[1] === null || b[0] === a[0]) return a.slice(1);
  const dx = b[1] - a[1], dy = b[2] - a[2], dz = b[3] - a[3];
  if (b[0] - a[0] === 1 && Math.hypot(dx, dy, dz) > jump) return a.slice(1);
  const u = (t - a[0]) / (b[0] - a[0]);
  return a.slice(1).map((v, k) => v + (b[k + 1] - v) * u);
}
function lastChange(list, t, def = null) {
  let best = def;
  for (const c of list) { if (c[0] <= t) best = c; else break; }
  return best;
}
function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
function gauss(r) { return Math.sqrt(-2 * Math.log(r() + 1e-9)) * Math.cos(2 * Math.PI * r()); }

// ---------------------------------------------------------------------------
// particles (analytic, so any frame can be rendered independently)
const PT = {
  flame: { tex: ['flame'], life: [12, 20], size: 0.12, grav: 0, drag: 0.96, vel: 0, bright: true },
  small_flame: { tex: ['flame'], life: [8, 14], size: 0.06, grav: 0, drag: 0.96, vel: 0, bright: true },
  lava: { tex: ['lava'], life: [16, 32], size: 0.12, grav: 0.03, drag: 0.999, vel: 0.3, bright: true, up: 0.25 },
  smoke: { tex: seq('generic_', 8, true), life: [16, 30], size: 0.12, grav: -0.004, drag: 0.96, vel: 0, tint: [0.3, 0.3, 0.3] },
  large_smoke: { tex: seq('generic_', 8, true), life: [30, 60], size: 0.35, grav: -0.006, drag: 0.96, vel: 0, tint: [0.25, 0.25, 0.25] },
  poof: { tex: seq('generic_', 8, true), life: [10, 18], size: 0.18, grav: 0, drag: 0.9, vel: 0, tint: [0.9, 0.9, 0.9] },
  campfire: { tex: seq('big_smoke_', 12), life: [80, 160], size: 0.9, grav: -0.02, drag: 1.0, vel: 0, tint: [0.85, 0.85, 0.85], alpha: 0.6 },
  explosion: { tex: seq('explosion_', 16), life: [6, 16], size: 1.6, grav: 0, drag: 1, vel: 0, bright: true },
  dust: { tex: seq('generic_', 8, true), life: [8, 30], size: 0.1, grav: 0, drag: 0.96, vel: 0 },
  splash: { tex: ['splash_0', 'splash_1', 'splash_2', 'splash_3'], life: [6, 14], size: 0.08, grav: 0.04, drag: 0.98, vel: 0.15, up: 0.2 },
  crit: { tex: ['critical_hit'], life: [8, 16], size: 0.08, grav: 0.02, drag: 0.7, vel: 0.4 },
  blood: { tex: seq('generic_', 8, true), life: [14, 26], size: 0.08, grav: 0.03, drag: 0.98, vel: 0.12, tint: [0.55, 0.03, 0.03] },
};
function seq(p, n, rev) { const a = []; for (let i = 0; i < n; i++) a.push(p + i); return rev ? a.reverse() : a; }

export class FilmPlayer {
  constructor(stage, film, rp) {
    this.stage = stage; this.film = film; this.rp = rp;
    this.actors = {}; this.props = {}; this.drops = [];
    this.blockLog = [];     // applied block changes (for scrubbing backwards)
    this.appliedBlocks = 0;
    this.blockEvents = film.events.filter(e => e[1] === 'blocks').sort((a, b) => a[0] - b[0]);
    this.particleEvents = film.events.filter(e => e[1] === 'particle').sort((a, b) => a[0] - b[0]);
    this.dropEvents = film.events.filter(e => e[1] === 'drop');
    this.sprites = [];
    this.texCache = {};
    this.spriteGroup = new THREE.Group();
    stage.scene.add(this.spriteGroup);
  }

  async load() {
    const f = this.film;
    const models = new Set();
    for (const [id, a] of Object.entries(f.actors)) {
      const tex = loadSkinTexture(`${this.rp}/assets/kino/textures/entity/skins/${a.skin}.png`);
      const m = new PlayerModel(tex, a.slim);
      m.root.visible = false;
      this.stage.scene.add(m.root);
      this.actors[id] = { def: a, model: m, heldKey: { main: null, off: null } };
      for (const it of a.items) if (it[2]) models.add(it[2]);
    }
    for (const [id, p] of Object.entries(f.props)) if (p.model) models.add(p.model);
    for (const e of this.dropEvents) models.add(e[2].model);
    this.models = {};
    for (const name of models) this.models[name] = await loadItemModel(this.rp, name);
    for (const [id, p] of Object.entries(f.props)) {
      let obj = null;
      if (p.model) { obj = itemMesh(this.models[p.model]); obj.visible = false; this.stage.scene.add(obj); }
      this.props[id] = { def: p, obj };
    }
    for (const e of this.dropEvents) {
      const o = itemMesh(this.models[e[2].model]); o.visible = false; this.stage.scene.add(o);
      this.drops.push({ ev: e, obj: o });
    }
    const names = new Set();
    for (const k in PT) for (const t of PT[k].tex) names.add(t);
    for (const n of names) {
      const tex = pixelTexture(`../build/preview/tex/${n}.png`);
      this.texCache[n] = tex;
    }
  }

  applyBlocks(tick) {
    const w = this.stage.world;
    // forward
    while (this.appliedBlocks < this.blockEvents.length && this.blockEvents[this.appliedBlocks][0] <= tick) {
      const ev = this.blockEvents[this.appliedBlocks];
      const undo = [];
      for (const [x, y, z, s] of ev[2].list) { undo.push([x, y, z, w.get(x, y, z)]); w.setState(x, y, z, s); }
      this.blockLog.push(undo);
      this.appliedBlocks++;
    }
    // backward
    while (this.appliedBlocks > 0 && this.blockEvents[this.appliedBlocks - 1][0] > tick) {
      const undo = this.blockLog.pop();
      for (let i = undo.length - 1; i >= 0; i--) { const [x, y, z, v] = undo[i]; w.set(x, y, z, v); }
      this.appliedBlocks--;
    }
    w.update();
  }

  holdItem(a, hand, name, aim) {
    const key = name ? name + (aim ? '#aim' : '') : null;
    if (a.heldKey[hand] === key) return;
    a.heldKey[hand] = key;
    const arm = hand === 'main' ? a.model.rightArm : a.model.leftArm;
    if (a[hand + 'Obj']) { arm.remove(a[hand + 'Obj']); a[hand + 'Obj'] = null; }
    if (!name) return;
    const e = this.models[name];
    const o = itemMesh(e);
    o.matrix.copy(heldMatrix(e.json, hand !== 'main', a.def.slim));
    arm.add(o);
    a[hand + 'Obj'] = o;
  }

  renderAt(tick) {
    const f = this.film, st = this.stage;
    const ti = Math.floor(tick);
    this.applyBlocks(ti);
    // time of day
    const tm = lastChange(f.times, ti);
    st.setTime(tm ? tm[1] : 1000);
    // props
    for (const [id, p] of Object.entries(this.props)) {
      const s = sampleTrack(p.def.track, tick);
      if (!p.obj) continue;
      p.obj.visible = !!s;
      if (!s) continue;
      p.obj.matrix.copy(itemDisplayMatrix([s[0], s[1], s[2]], s[3], s[4],
        { translation: p.def.translation, scale: [p.def.scale, p.def.scale, p.def.scale] }));
      p.obj.matrixWorldNeedsUpdate = true;
    }
    // actors
    for (const [id, a] of Object.entries(this.actors)) {
      const s = sampleTrack(a.def.track, tick);
      const m = a.model;
      m.root.visible = !!s;
      if (!s) continue;
      const pose = (lastChange(a.def.poses, ti) || [0, 'standing'])[1];
      const ride = (lastChange(a.def.rides, ti) || [0, null])[1];
      m.root.position.set(s[0], s[1], s[2]);
      m.root.rotation.set(0, -s[3] * DEG, 0);
      let main = null, off = null;
      for (const it of a.def.items) { if (it[0] > ti) break; if (it[1] === 'main') main = it; else off = it; }
      this.holdItem(a, 'main', main && main[2], main && main[3]);
      this.holdItem(a, 'off', off && off[2], off && off[3]);
      m.applyPose({
        pose: ride ? 'riding' : pose, walkPos: s[5], walkAmt: s[6], age: tick,
        headPitch: s[4] * DEG, headYaw: 0,
        holding: { right: !!(main && main[2]), left: !!(off && off[2]) }, aim: !!(main && main[3]),
      });
      let burning = false;
      for (const fr of a.def.fires) if (ti >= fr[0] && ti <= fr[1]) burning = true;
      a.burning = burning;
    }
    // thrown items
    for (const d of this.drops) {
      const [t0, , data] = d.ev;
      const age = tick - t0;
      if (age < 0 || age > (data.life || 600)) { d.obj.visible = false; continue; }
      let [x, y, z] = data.pos, [vx, vy, vz] = data.vel;
      const floorY = data.floor ?? 64.5;
      let k = 0;
      for (; k < Math.floor(age); k++) {
        vy -= 0.04; vx *= 0.98; vy *= 0.98; vz *= 0.98;
        x += vx; y += vy; z += vz;
        if (y < floorY) { y = floorY; vy = 0; vx *= 0.5; vz *= 0.5; }
      }
      const e = this.models[data.model];
      const M = new THREE.Matrix4().makeTranslation(x, y + 0.1 + Math.sin(age / 10) * 0.05, z);
      M.multiply(new THREE.Matrix4().makeRotationY(age / 20));
      M.multiply(displayMatrix(e.json, 'ground'));
      d.obj.matrix.copy(M); d.obj.matrixWorldNeedsUpdate = true; d.obj.visible = true;
    }
    this.renderParticles(tick);
    // camera
    const c = sampleTrack(f.cam, tick, 3.5);
    aimCamera(st.camera, [c[0], c[1], c[2]], c[3], c[4], 70);
    st.render();
  }

  renderParticles(tick) {
    for (const s of this.sprites) s.visible = false;
    let used = 0;
    const get = () => {
      if (used >= this.sprites.length) {
        const sp = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, alphaTest: 0.05, depthWrite: false }));
        this.spriteGroup.add(sp); this.sprites.push(sp);
      }
      const sp = this.sprites[used++]; sp.visible = true; return sp;
    };
    const emit = (type, x, y, z, age, life, r, col) => {
      const P = PT[type];
      const u = age / life;
      const texName = P.tex[Math.min(P.tex.length - 1, Math.floor(u * P.tex.length))];
      const sp = get();
      sp.material.map = this.texCache[texName];
      const b = P.bright ? 1 : this.stage.brightness;
      const tint = col || P.tint || [1, 1, 1];
      sp.material.color.setRGB(tint[0] * b, tint[1] * b, tint[2] * b);
      sp.material.opacity = P.alpha ? P.alpha * (1 - u * 0.6) : 1;
      let size = P.size * (type === 'flame' ? (1 - u * u * 0.5) : 1) * (0.7 + r * 0.6);
      sp.scale.set(size * 2, size * 2, 1);
      sp.position.set(x, y, z);
    };
    // burning actors (vanilla: flames around the entity every tick)
    const lo = tick - 60;
    for (const ev of this.particleEvents) {
      const t0 = ev[0];
      if (t0 < lo - 100) continue;
      if (t0 > tick) break;
      const d = ev[2];
      const P = PT[d.type];
      if (!P) continue;
      const R = rng(d.seed || (t0 * 7919 + 1));
      const n = Math.min(d.count || 1, 200);
      for (let i = 0; i < n; i++) {
        const life = P.life[0] + R() * (P.life[1] - P.life[0]);
        const delay = (d.spread || 0) * R();
        const age = tick - t0 - delay;
        const ox = gauss(R) * (d.delta ? d.delta[0] : 0), oy = gauss(R) * (d.delta ? d.delta[1] : 0), oz = gauss(R) * (d.delta ? d.delta[2] : 0);
        const sp = d.speed || 0;
        let vx = gauss(R) * (P.vel + sp), vy = gauss(R) * (P.vel + sp) + (P.up || 0), vz = gauss(R) * (P.vel + sp);
        if (d.dir) { vx += d.dir[0]; vy += d.dir[1]; vz += d.dir[2]; }
        const rr = R();
        if (age < 0 || age > life) continue;
        // closed form for v *= drag, v -= grav per tick
        const k = P.drag, a = age;
        const geo = k === 1 ? a : (1 - Math.pow(k, a)) / (1 - k);
        let x = d.pos[0] + ox + vx * geo, y = d.pos[1] + oy + vy * geo - P.grav * a * a * 0.5, z = d.pos[2] + oz + vz * geo;
        if (d.type === 'blood' || d.type === 'splash') y = Math.max(y, 64.9);
        emit(d.type, x, y, z, age, life, rr, d.color);
      }
    }
    for (const a of Object.values(this.actors)) {
      if (!a.burning || !a.model.root.visible) continue;
      const R = rng(Math.floor(tick) * 13 + 5);
      const p = a.model.root.position;
      for (let k = 0; k < 40; k++) {
        const age = (tick * 1.0 + k * 3.7) % 18;
        const life = 18;
        const rr = rng(k * 31 + 7);
        const ox = (rr() - 0.5) * 0.7, oz = (rr() - 0.5) * 0.7, oy = rr() * 1.8;
        emit('flame', p.x + ox, p.y + oy + age * 0.03, p.z + oz, age, life, rr(), null);
      }
    }
  }
}
