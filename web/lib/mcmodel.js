// Minecraft block/item model JSON ("elements") -> three.js mesh, plus the exact
// transform chains vanilla uses for item_display entities and items held in hand.
import * as THREE from 'three';
THREE.ColorManagement.enabled = false; // work in plain sRGB values like vanilla

const texLoader = new THREE.TextureLoader();
const texCache = new Map();
export function pixelTexture(url) {
  if (texCache.has(url)) return texCache.get(url);
  const t = texLoader.load(url);
  t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter;
  t.generateMipmaps = false; 
  texCache.set(url, t);
  return t;
}

const FACE_VERTS = {
  north: (a, b) => [[b[0], b[1], a[2]], [a[0], b[1], a[2]], [a[0], a[1], a[2]], [b[0], a[1], a[2]]],
  south: (a, b) => [[a[0], b[1], b[2]], [b[0], b[1], b[2]], [b[0], a[1], b[2]], [a[0], a[1], b[2]]],
  east: (a, b) => [[b[0], b[1], b[2]], [b[0], b[1], a[2]], [b[0], a[1], a[2]], [b[0], a[1], b[2]]],
  west: (a, b) => [[a[0], b[1], a[2]], [a[0], b[1], b[2]], [a[0], a[1], b[2]], [a[0], a[1], a[2]]],
  up: (a, b) => [[a[0], b[1], a[2]], [b[0], b[1], a[2]], [b[0], b[1], b[2]], [a[0], b[1], b[2]]],
  down: (a, b) => [[a[0], a[1], b[2]], [b[0], a[1], b[2]], [b[0], a[1], a[2]], [a[0], a[1], a[2]]],
};

// Build geometry in block units (model units / 16), untranslated (0..1 = one block).
export function buildModelGeometry(model) {
  const pos = [], uv = [], idx = [];
  const v3 = new THREE.Vector3();
  for (const el of model.elements) {
    let rot = null, origin = null;
    if (el.rotation && el.rotation.angle) {
      const ax = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) }[el.rotation.axis];
      rot = new THREE.Matrix4().makeRotationAxis(ax, el.rotation.angle * Math.PI / 180);
      origin = new THREE.Vector3(...el.rotation.origin);
    }
    for (const [face, f] of Object.entries(el.faces)) {
      const vs = FACE_VERTS[face](el.from, el.to);
      const base = pos.length / 3;
      for (const p of vs) {
        v3.set(p[0], p[1], p[2]);
        if (rot) { v3.sub(origin).applyMatrix4(rot).add(origin); }
        pos.push(v3.x / 16, v3.y / 16, v3.z / 16);
      }
      const [u0, v0, u1, v1] = f.uv;
      uv.push(u0 / 16, 1 - v0 / 16, u1 / 16, 1 - v0 / 16, u1 / 16, 1 - v1 / 16, u0 / 16, 1 - v1 / 16);
      idx.push(base, base + 3, base + 2, base, base + 2, base + 1);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

const modelCache = new Map();
export async function loadItemModel(base, name) {
  if (modelCache.has(name)) return modelCache.get(name);
  let json = await (await fetch(`${base}/assets/kino/models/item/${name}.json`)).json();
  let texName = name;
  if (json.parent) {
    const pn = json.parent.split('/').pop();
    const parent = await (await fetch(`${base}/assets/kino/models/item/${pn}.json`)).json();
    json = { ...parent, display: { ...(parent.display || {}), ...(json.display || {}) } };
    texName = pn;
  }
  const tex = pixelTexture(`${base}/assets/kino/textures/item/${texName}.png`);
  const geo = buildModelGeometry(json);
  const mat = new THREE.MeshLambertMaterial({ map: tex, transparent: true, alphaTest: 0.05, side: THREE.DoubleSide });
  const entry = { json, geo, mat };
  modelCache.set(name, entry);
  return entry;
}

// A mesh whose own matrix already contains the -0.5 recentring vanilla applies.
export function itemMesh(entry) {
  const m = new THREE.Mesh(entry.geo, entry.mat);
  m.matrixAutoUpdate = false;
  m.matrix.makeTranslation(-0.5, -0.5, -0.5);
  const holder = new THREE.Group();
  holder.add(m);
  holder.matrixAutoUpdate = false;
  return holder;
}

const DEG = Math.PI / 180;

// ItemTransform.apply (display block of the model json)
export function displayMatrix(json, ctx, leftHand = false) {
  const d = (json.display || {})[ctx];
  const M = new THREE.Matrix4();
  if (!d) return M;
  const t = d.translation || [0, 0, 0], r = d.rotation || [0, 0, 0], s = d.scale || [1, 1, 1];
  const clampT = v => Math.max(-80, Math.min(80, v)) / 16;
  let rx = r[0], ry = r[1], rz = r[2];
  if (leftHand) { ry = -ry; rz = -rz; }
  const i = leftHand ? -1 : 1;
  M.makeTranslation(i * clampT(t[0]), clampT(t[1]), clampT(t[2]));
  M.multiply(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rx * DEG, ry * DEG, rz * DEG, 'XYZ')));
  M.multiply(new THREE.Matrix4().makeScale(Math.max(-4, Math.min(4, s[0])), Math.max(-4, Math.min(4, s[1])), Math.max(-4, Math.min(4, s[2]))));
  return M;
}

// item_display: world = T(pos) Ry(-yaw) Rx(pitch) · Transformation · Ry(180) · display(none) · T(-0.5)
export function itemDisplayMatrix(pos, yaw, pitch, tr) {
  const M = new THREE.Matrix4().makeTranslation(pos[0], pos[1], pos[2]);
  M.multiply(new THREE.Matrix4().makeRotationY(-yaw * DEG));
  M.multiply(new THREE.Matrix4().makeRotationX(pitch * DEG));
  if (tr) {
    const t = tr.translation || [0, 0, 0], s = tr.scale || [1, 1, 1];
    M.multiply(new THREE.Matrix4().makeTranslation(t[0], t[1], t[2]));
    if (tr.left_rotation) M.multiply(new THREE.Matrix4().makeRotationFromQuaternion(new THREE.Quaternion(...tr.left_rotation)));
    M.multiply(new THREE.Matrix4().makeScale(s[0], s[1], s[2]));
    if (tr.right_rotation) M.multiply(new THREE.Matrix4().makeRotationFromQuaternion(new THREE.Quaternion(...tr.right_rotation)));
  }
  M.multiply(new THREE.Matrix4().makeRotationY(Math.PI));
  return M;
}

// Held item, relative to the (three.js) arm group of PlayerModel.
// Vanilla: translateToHand · Rx(-90) · Ry(180) · T(±1/16, 2/16, -10/16) · display · T(-0.5)
// three arm frame = vanilla ModelPart frame rotated 180° about X  (F = diag(1,-1,-1)).
export function heldMatrix(json, leftHand, slim) {
  const M = new THREE.Matrix4().makeScale(1, -1, -1);
  if (slim) M.multiply(new THREE.Matrix4().makeTranslation((leftHand ? -0.5 : 0.5) / 16, 0, 0));
  M.multiply(new THREE.Matrix4().makeRotationX(-90 * DEG));
  M.multiply(new THREE.Matrix4().makeRotationY(180 * DEG));
  M.multiply(new THREE.Matrix4().makeTranslation((leftHand ? -1 : 1) / 16, 0.125, -0.625));
  M.multiply(displayMatrix(json, leftHand ? 'thirdperson_lefthand' : 'thirdperson_righthand', leftHand));
  return M;
}
