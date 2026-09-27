// Voxel world for the preview: expands the merged boxes from world.json and
// meshes 16^3 chunks with face culling, vanilla-style face shading, smooth
// ambient occlusion, biome tints, cut-out leaves/plants and translucent water.
import * as THREE from 'three';

const CS = 16;
const SHADE = { up: 1.0, down: 0.5, north: 0.8, south: 0.8, east: 0.6, west: 0.6 };
const DIRS = {
  up: [0, 1, 0], down: [0, -1, 0], north: [0, 0, -1], south: [0, 0, 1], east: [1, 0, 0], west: [-1, 0, 0],
};
// face corners (TL, TR, BR, BL as seen from outside) for a unit cube
const FACE = {
  north: [[1, 1, 0], [0, 1, 0], [0, 0, 0], [1, 0, 0]],
  south: [[0, 1, 1], [1, 1, 1], [1, 0, 1], [0, 0, 1]],
  east: [[1, 1, 1], [1, 1, 0], [1, 0, 0], [1, 0, 1]],
  west: [[0, 1, 0], [0, 1, 1], [0, 0, 1], [0, 0, 0]],
  up: [[0, 1, 0], [1, 1, 0], [1, 1, 1], [0, 1, 1]],
  down: [[0, 0, 1], [1, 0, 1], [1, 0, 0], [0, 0, 0]],
};
const AO_CURVE = [1.0, 0.8, 0.66, 0.52];

export class VoxelWorld {
  constructor(data, atlasTexture) {
    this.data = data;
    this.defs = data.defs;
    this.chunks = new Map();
    this.meshes = new Map();
    this.group = new THREE.Group();
    const t = data.tints;
    this.tints = {};
    for (const k in t) this.tints[k] = t[k].map(v => v / 255);
    this.atlas = atlasTexture;
    this.cols = data.atlas.cols; this.rows = data.atlas.rows;
    this.solid = new THREE.MeshBasicMaterial({ map: atlasTexture, vertexColors: true, alphaTest: 0.5 });
    this.plants = new THREE.MeshBasicMaterial({ map: atlasTexture, vertexColors: true, alphaTest: 0.5, side: THREE.DoubleSide });
    this.water = new THREE.MeshBasicMaterial({ map: atlasTexture, vertexColors: true, transparent: true, opacity: 0.72, depthWrite: false, side: THREE.DoubleSide });
    this.materials = [this.solid, this.plants, this.water];
    const b = data.boxes;
    for (let i = 0; i < b.length; i += 7) this.fillBox(b[i], b[i + 1], b[i + 2], b[i + 3], b[i + 4], b[i + 5], b[i + 6] + 1);
    this.dirty = new Set(this.chunks.keys());
    this.stateIndex = new Map(data.states.map((s, i) => [s, i + 1]));
  }

  key(cx, cy, cz) { return cx + ',' + cy + ',' + cz; }
  chunk(cx, cy, cz, create) {
    const k = this.key(cx, cy, cz);
    let c = this.chunks.get(k);
    if (!c && create) { c = new Uint16Array(CS * CS * CS); this.chunks.set(k, c); }
    return c;
  }
  get(x, y, z) {
    const c = this.chunk(x >> 4, y >> 4, z >> 4, false);
    return c ? c[((y & 15) * CS + (z & 15)) * CS + (x & 15)] : 0;
  }
  set(x, y, z, v) {
    const c = this.chunk(x >> 4, y >> 4, z >> 4, true);
    c[((y & 15) * CS + (z & 15)) * CS + (x & 15)] = v;
    this.dirty.add(this.key(x >> 4, y >> 4, z >> 4));
    // neighbours may need re-meshing (culling / AO)
    for (const [dx, dy, dz] of [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]) {
      const k = this.key((x + dx) >> 4, (y + dy) >> 4, (z + dz) >> 4);
      if (this.chunks.has(k)) this.dirty.add(k);
    }
  }
  fillBox(x1, y1, z1, x2, y2, z2, v) {
    for (let y = y1; y <= y2; y++) for (let z = z1; z <= z2; z++) for (let x = x1; x <= x2; x++) {
      const c = this.chunk(x >> 4, y >> 4, z >> 4, true);
      c[((y & 15) * CS + (z & 15)) * CS + (x & 15)] = v;
    }
  }
  setState(x, y, z, state) {
    if (state === null) { this.set(x, y, z, 0); return; }
    let v = this.stateIndex.get(state);
    if (!v) throw new Error('unknown state ' + state);
    this.set(x, y, z, v);
  }
  def(v) { return v ? this.defs[v - 1] : null; }
  opaqueAt(x, y, z) { const d = this.def(this.get(x, y, z)); return !!(d && d.opaque && d.shape === 'cube' && !d.alpha); }
  occludes(x, y, z) { const d = this.def(this.get(x, y, z)); return !!(d && d.shape === 'cube' && (d.opaque || d.leaves)); }

  uvFor(tex) {
    const i = this.data.atlas.index[tex];
    const u0 = (i % this.cols) / this.cols, v0 = Math.floor(i / this.cols) / this.rows;
    const du = 1 / this.cols, dv = 1 / this.rows;
    const e = 0.0005;
    return [u0 + e, 1 - v0 - e, u0 + du - e, 1 - (v0 + dv) + e]; // (left, top, right, bottom) in GL uv
  }

  // rebuild every dirty chunk mesh
  update() {
    for (const k of this.dirty) this.buildChunk(k);
    this.dirty.clear();
  }

  buildChunk(k) {
    const old = this.meshes.get(k);
    if (old) { for (const m of old) { this.group.remove(m); m.geometry.dispose(); } }
    const [cx, cy, cz] = k.split(',').map(Number);
    const c = this.chunks.get(k);
    if (!c) return;
    const out = [mkBuf(), mkBuf(), mkBuf()];
    const ox = cx * CS, oy = cy * CS, oz = cz * CS;
    for (let ly = 0; ly < CS; ly++) for (let lz = 0; lz < CS; lz++) for (let lx = 0; lx < CS; lx++) {
      const v = c[(ly * CS + lz) * CS + lx];
      if (!v) continue;
      this.meshBlock(out, ox + lx, oy + ly, oz + lz, this.defs[v - 1]);
    }
    const meshes = [];
    out.forEach((b, i) => {
      if (!b.pos.length) return;
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(b.pos, 3));
      g.setAttribute('uv', new THREE.Float32BufferAttribute(b.uv, 2));
      g.setAttribute('color', new THREE.Float32BufferAttribute(b.col, 3));
      g.setIndex(b.idx);
      const m = new THREE.Mesh(g, this.materials[i]);
      if (i === 2) m.renderOrder = 2;
      this.group.add(m);
      meshes.push(m);
    });
    this.meshes.set(k, meshes);
  }

  tintOf(name) { return name ? this.tints[name] : null; }

  // one quad, with optional per-vertex AO
  quad(buf, pts, uvr, rgb, shade, ao) {
    const base = buf.pos.length / 3;
    const [ul, vt, ur, vb] = uvr;
    const uvs = [[ul, vt], [ur, vt], [ur, vb], [ul, vb]];
    for (let i = 0; i < 4; i++) {
      buf.pos.push(pts[i][0], pts[i][1], pts[i][2]);
      buf.uv.push(uvs[i][0], uvs[i][1]);
      const a = ao ? AO_CURVE[ao[i]] : 1;
      buf.col.push(rgb[0] * shade * a, rgb[1] * shade * a, rgb[2] * shade * a);
    }
    if (ao && ao[0] + ao[2] > ao[1] + ao[3]) buf.idx.push(base + 1, base + 0, base + 3, base + 1, base + 3, base + 2);
    else buf.idx.push(base, base + 3, base + 2, base, base + 2, base + 1);
  }

  aoFor(x, y, z, face, corner) {
    // corner in unit coords of the face vertex; sample the 3 blocks around that vertex on the face's outer side
    const n = DIRS[face];
    const ax = [0, 1, 2].filter(i => n[i] === 0);
    const s = [0, 0, 0];
    const p = [x + n[0], y + n[1], z + n[2]];
    const d0 = [0, 0, 0], d1 = [0, 0, 0];
    d0[ax[0]] = corner[ax[0]] ? 1 : -1;
    d1[ax[1]] = corner[ax[1]] ? 1 : -1;
    const s1 = this.occludes(p[0] + d0[0], p[1] + d0[1], p[2] + d0[2]) ? 1 : 0;
    const s2 = this.occludes(p[0] + d1[0], p[1] + d1[1], p[2] + d1[2]) ? 1 : 0;
    const cc = this.occludes(p[0] + d0[0] + d1[0], p[1] + d0[1] + d1[1], p[2] + d0[2] + d1[2]) ? 1 : 0;
    if (s1 && s2) return 3;
    return s1 + s2 + cc;
  }

  box(buf, x, y, z, d, from, to, faceCheck, texFn, tint, noAO) {
    for (const f of ['up', 'down', 'north', 'south', 'east', 'west']) {
      if (faceCheck && !faceCheck(f)) continue;
      const tex = texFn(f);
      if (!tex) continue;
      const pts = FACE[f].map(c => [x + (c[0] ? to[0] : from[0]), y + (c[1] ? to[1] : from[1]), z + (c[2] ? to[2] : from[2])]);
      let uvr = this.uvFor(tex);
      // crop uv to the box extent (like vanilla default uvs)
      const [ul, vt, ur, vb] = uvr;
      const du = ur - ul, dv = vt - vb;
      let a0, a1, b0, b1; // horizontal / vertical extents in 0..1
      if (f === 'up' || f === 'down') { a0 = from[0]; a1 = to[0]; b0 = from[2]; b1 = to[2]; if (f === 'down') { b0 = 1 - to[2]; b1 = 1 - from[2]; } }
      else if (f === 'north') { a0 = 1 - to[0]; a1 = 1 - from[0]; b0 = 1 - to[1]; b1 = 1 - from[1]; }
      else if (f === 'south') { a0 = from[0]; a1 = to[0]; b0 = 1 - to[1]; b1 = 1 - from[1]; }
      else if (f === 'east') { a0 = 1 - to[2]; a1 = 1 - from[2]; b0 = 1 - to[1]; b1 = 1 - from[1]; }
      else { a0 = from[2]; a1 = to[2]; b0 = 1 - to[1]; b1 = 1 - from[1]; }
      uvr = [ul + du * a0, vt - dv * b0, ul + du * a1, vt - dv * b1];
      const col = (f === 'up' && d.tint_up) ? this.tints[d.tint_up] : (tint || [1, 1, 1]);
      const full = from[0] === 0 && from[1] === 0 && from[2] === 0 && to[0] === 1 && to[1] === 1 && to[2] === 1;
      const ao = (!noAO && full) ? FACE[f].map(c => this.aoFor(x, y, z, f, c)) : null;
      this.quad(buf, pts, uvr, col, SHADE[f], ao);
    }
  }

  meshBlock(out, x, y, z, d) {
    const [solid, plants, water] = out;
    const tint = d.tint ? this.tints[d.tint] : null;
    const self = this;
    const nb = f => { const n = DIRS[f]; return [x + n[0], y + n[1], z + n[2]]; };
    const shape = d.shape;
    if (shape === 'cube') {
      this.box(solid, x, y, z, d, [0, 0, 0], [1, 1, 1], f => {
        const [a, b, c] = nb(f);
        const nd = self.def(self.get(a, b, c));
        if (!nd) return true;
        if (nd.shape !== 'cube') return true;
        if (d.leaves) return !nd.opaque && !(nd.leaves);
        if (d.alpha) return nd.tex.up !== d.tex.up && !nd.opaque;
        return !(nd.opaque && !nd.alpha);
      }, f => d.tex[f], tint);
    } else if (shape === 'slab_bottom' || shape === 'slab_top' || shape === 'carpet') {
      const h = shape === 'carpet' ? 1 / 16 : 0.5;
      const y0 = shape === 'slab_top' ? 0.5 : 0;
      this.box(solid, x, y, z, d, [0, y0, 0], [1, y0 + h, 1], f => {
        if (f === 'up' && y0 + h < 1) return true;
        if (f === 'down' && y0 > 0) return true;
        const [a, b, c] = nb(f);
        return !self.opaqueAt(a, b, c);
      }, f => d.tex[f], tint);
    } else if (shape === 'stairs') {
      this.box(solid, x, y, z, d, [0, 0, 0], [1, 0.5, 1], f => { const [a, b, c] = nb(f); return f === 'up' || !self.opaqueAt(a, b, c); }, f => d.tex[f], tint);
      const q = { north: [[0, 0.5, 0], [1, 1, 0.5]], south: [[0, 0.5, 0.5], [1, 1, 1]], east: [[0.5, 0.5, 0], [1, 1, 1]], west: [[0, 0.5, 0], [0.5, 1, 1]] }[d.facing];
      this.box(solid, x, y, z, d, q[0], q[1], f => { const [a, b, c] = nb(f); return !self.opaqueAt(a, b, c); }, f => d.tex[f], tint, true);
    } else if (shape === 'cross') {
      const uvr = this.uvFor(d.tex.cross);
      const col = tint || [1, 1, 1];
      const e = 0.15;
      this.quad(plants, [[x + e, y + 1, z + e], [x + 1 - e, y + 1, z + 1 - e], [x + 1 - e, y, z + 1 - e], [x + e, y, z + e]], uvr, col, 0.95);
      this.quad(plants, [[x + 1 - e, y + 1, z + e], [x + e, y + 1, z + 1 - e], [x + e, y, z + 1 - e], [x + 1 - e, y, z + e]], uvr, col, 0.95);
    } else if (shape === 'campfire') {
      const L = d.tex.log;
      this.box(solid, x, y, z, d, [1 / 16, 0, 0], [5 / 16, 4 / 16, 1], null, () => L, null, true);
      this.box(solid, x, y, z, d, [11 / 16, 0, 0], [15 / 16, 4 / 16, 1], null, () => L, null, true);
      this.box(solid, x, y, z, d, [0, 3 / 16, 1 / 16], [1, 7 / 16, 5 / 16], null, () => L, null, true);
      this.box(solid, x, y, z, d, [0, 3 / 16, 11 / 16], [1, 7 / 16, 15 / 16], null, () => L, null, true);
      if (d.lit) {
        const uvr = this.uvFor(d.tex.fire);
        this.quad(plants, [[x + 0.1, y + 1, z + 0.1], [x + 0.9, y + 1, z + 0.9], [x + 0.9, y, z + 0.9], [x + 0.1, y, z + 0.1]], uvr, [1, 1, 1], 1.2);
        this.quad(plants, [[x + 0.9, y + 1, z + 0.1], [x + 0.1, y + 1, z + 0.9], [x + 0.1, y, z + 0.9], [x + 0.9, y, z + 0.1]], uvr, [1, 1, 1], 1.2);
      }
    } else if (shape === 'lantern') {
      const L = d.tex.lantern;
      this.box(solid, x, y, z, d, [5 / 16, 0, 5 / 16], [11 / 16, 7 / 16, 11 / 16], null, () => L, [1.25, 1.15, 0.9], true);
      this.box(solid, x, y, z, d, [6 / 16, 7 / 16, 6 / 16], [10 / 16, 9 / 16, 10 / 16], null, () => L, null, true);
    }
    if (d.water) this.meshWater(water, x, y, z);
  }

  hasWater(x, y, z) { const d = this.def(this.get(x, y, z)); return !!(d && d.water); }

  meshWater(buf, x, y, z) {
    const h = 8 / 9;
    const uvr = this.uvFor('water_still');
    const col = this.tints.water;
    if (!this.hasWater(x, y + 1, z)) {
      this.quad(buf, [[x, y + h, z], [x + 1, y + h, z], [x + 1, y + h, z + 1], [x, y + h, z + 1]], uvr, col, 1.0);
    }
    for (const f of ['north', 'south', 'east', 'west']) {
      const n = DIRS[f];
      const a = x + n[0], c = z + n[2];
      if (this.hasWater(a, y, c) || this.opaqueAt(a, y, c)) continue;
      const pts = FACE[f].map(cn => [x + cn[0], y + (cn[1] ? h : 0), z + cn[2]]);
      this.quad(buf, pts, uvr, col, SHADE[f]);
    }
  }
}

function mkBuf() { return { pos: [], uv: [], col: [], idx: [] }; }
