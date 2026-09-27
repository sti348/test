// Minecraft player / mannequin model for three.js (units: 1 = one block, 1px = 1/16).
// Mirrors the vanilla HumanoidModel layout + skin UV layout, including the
// second (overlay) layer, slim arms and the poses a Mannequin can show in-game:
// standing (walk cycle), riding, crossbow-hold (aim), swimming (prone), sleeping.
import * as THREE from 'three';
THREE.ColorManagement.enabled = false; // work in plain sRGB values like vanilla

const PX = 1 / 16;

function boxUV(geo, u, v, w, h, d) {
  const T = 64;
  const f = (x1, y1, x2, y2) => [
    [x1 / T, 1 - y2 / T], [x2 / T, 1 - y2 / T], [x2 / T, 1 - y1 / T], [x1 / T, 1 - y1 / T],
  ];
  const top = f(u + d, v, u + w + d, v + d);
  const bottom = f(u + w + d, v, u + w * 2 + d, v + d);
  const left = f(u, v + d, u + d, v + d + h);
  const front = f(u + d, v + d, u + w + d, v + d + h);
  const right = f(u + w + d, v + d, u + w + d * 2, v + h + d);
  const back = f(u + w + d * 2, v + d, u + w * 2 + d * 2, v + h + d);
  const order = [
    [right[3], right[2], right[0], right[1]],
    [left[3], left[2], left[0], left[1]],
    [top[3], top[2], top[0], top[1]],
    [bottom[0], bottom[1], bottom[3], bottom[2]],
    [front[3], front[2], front[0], front[1]],
    [back[3], back[2], back[0], back[1]],
  ];
  const uv = geo.attributes.uv;
  let k = 0;
  for (const face of order) for (const p of face) { uv.setXY(k++, p[0], p[1]); }
  uv.needsUpdate = true;
}

function part(mat, u, v, w, h, d, inflate) {
  const g = new THREE.BoxGeometry((w + inflate * 2) * PX, (h + inflate * 2) * PX, (d + inflate * 2) * PX);
  boxUV(g, u, v, w, h, d);
  return new THREE.Mesh(g, mat);
}

const skinCache = new Map();
export function loadSkinTexture(url) {
  if (skinCache.has(url)) return skinCache.get(url);
  const tex = new THREE.TextureLoader().load(url);
  tex.magFilter = THREE.NearestFilter;
  tex.minFilter = THREE.NearestFilter;
  tex.generateMipmaps = false;
  
  skinCache.set(url, tex);
  return tex;
}

export class PlayerModel {
  constructor(skinTex, slim = false) {
    this.slim = slim;
    const base = new THREE.MeshLambertMaterial({ map: skinTex, alphaTest: 0.5 });
    const over = new THREE.MeshLambertMaterial({ map: skinTex, alphaTest: 0.1, side: THREE.DoubleSide });
    this.materials = [base, over];
    const aw = slim ? 3 : 4;
    this.root = new THREE.Group();      // at feet, yaw applied here
    this.pivot = new THREE.Group();     // whole-body rotations (prone etc.)
    this.root.add(this.pivot);
    const P = this.pivot;

    const mk = (u, v, ou, ov, w, h, d, infl, offset) => {
      const g = new THREE.Group();
      const a = part(base, u, v, w, h, d, 0);
      const b = part(over, ou, ov, w, h, d, infl);
      a.position.set(...offset.map(x => x * PX));
      b.position.copy(a.position);
      g.add(a, b);
      return g;
    };
    // head pivot at neck (y=24px)
    this.head = mk(0, 0, 32, 0, 8, 8, 8, 0.5, [0, 4, 0]);
    this.head.position.set(0, 24 * PX, 0);
    this.body = mk(16, 16, 16, 32, 8, 12, 4, 0.25, [0, -6, 0]);
    this.body.position.set(0, 24 * PX, 0);
    // arms: pivot at shoulder
    this.rightArm = mk(40, 16, 40, 32, aw, 12, 4, 0.25, [slim ? -0.5 : -1, -4, 0]);
    this.rightArm.position.set(-5 * PX, 22 * PX, 0);
    this.leftArm = mk(32, 48, 48, 48, aw, 12, 4, 0.25, [slim ? 0.5 : 1, -4, 0]);
    this.leftArm.position.set(5 * PX, 22 * PX, 0);
    // legs: pivot at hip
    this.rightLeg = mk(0, 16, 0, 32, 4, 12, 4, 0.25, [0, -6, 0]);
    this.rightLeg.position.set(-1.9 * PX, 12 * PX, 0);
    this.leftLeg = mk(16, 48, 0, 48, 4, 12, 4, 0.25, [0, -6, 0]);
    this.leftLeg.position.set(1.9 * PX, 12 * PX, 0);
    P.add(this.head, this.body, this.rightArm, this.leftArm, this.rightLeg, this.leftLeg);

    // hand anchors for held items (vanilla ItemInHandLayer offsets)
    this.rightHand = new THREE.Group();
    this.rightHand.position.set((slim ? -0.5 : -1) * PX + 1 * PX, -10 * PX + 2 * PX, 0);
    this.rightArm.add(this.rightHand);
    this.leftHand = new THREE.Group();
    this.leftHand.position.set((slim ? 0.5 : 1) * PX - 1 * PX, -10 * PX + 2 * PX, 0);
    this.leftArm.add(this.leftHand);
    this.held = { right: null, left: null };
  }

  setHeld(side, obj) {
    const hand = side === 'right' ? this.rightHand : this.leftHand;
    if (this.held[side]) hand.remove(this.held[side]);
    this.held[side] = obj;
    if (obj) hand.add(obj);
  }

  // state: {pose, walkPos, walkAmt, age, headYaw, headPitch, holding:{right,left}, aim}
  // Rotations follow vanilla HumanoidModel.setupAnim.  With three's y-up/+z-front frame:
  // three.x = mc.xRot, three.y = -mc.yRot, three.z = -mc.zRot (Euler order ZYX like vanilla).
  applyPose(st) {
    const parts = [this.head, this.body, this.rightArm, this.leftArm, this.rightLeg, this.leftLeg];
    for (const o of parts) { o.rotation.order = 'ZYX'; o.rotation.set(0, 0, 0); }
    this.pivot.rotation.set(0, 0, 0);
    this.pivot.position.set(0, 0, 0);
    const hp = st.headPitch || 0, hy = st.headYaw || 0;
    this.head.rotation.set(hp, hy, 0);
    const pos = st.walkPos || 0, amt = Math.min(1, st.walkAmt || 0);
    const age = st.age || 0;
    const c = Math.cos(pos * 0.6662), cpi = Math.cos(pos * 0.6662 + Math.PI);
    this.rightArm.rotation.x = cpi * amt;
    this.leftArm.rotation.x = c * amt;
    this.rightLeg.rotation.x = c * 1.4 * amt;
    this.leftLeg.rotation.x = cpi * 1.4 * amt;
    const pose = st.pose || 'standing';
    if (pose === 'riding') {
      this.rightArm.rotation.x += -Math.PI / 5;
      this.leftArm.rotation.x += -Math.PI / 5;
      this.rightLeg.rotation.set(-1.4137167, -Math.PI / 10, -0.07853982);
      this.leftLeg.rotation.set(-1.4137167, Math.PI / 10, 0.07853982);
    }
    const hold = st.holding || {};
    if (hold.right) this.rightArm.rotation.x = this.rightArm.rotation.x * 0.5 - Math.PI / 10;
    if (hold.left) this.leftArm.rotation.x = this.leftArm.rotation.x * 0.5 - Math.PI / 10;
    if (st.aim) {
      this.rightArm.rotation.y = 0.3 + hy;
      this.leftArm.rotation.y = -0.6 + hy;
      this.rightArm.rotation.x = -Math.PI / 2 + hp + 0.1;
      this.leftArm.rotation.x = -1.5 + hp;
    }
    // idle arm sway (AnimationUtils.bobModelPart)
    this.rightArm.rotation.z -= Math.cos(age * 0.09) * 0.05 + 0.05;
    this.leftArm.rotation.z += Math.cos(age * 0.09) * 0.05 + 0.05;
    this.rightArm.rotation.x += Math.sin(age * 0.067) * 0.05;
    this.leftArm.rotation.x -= Math.sin(age * 0.067) * 0.05;

    const PXs = PX;
    if (pose === 'crouching') {
      // vanilla HumanoidModel: torso tilts 0.5 rad, legs move 4px BACK (three -z), upper body drops
      this.body.rotation.x = 0.5;
      this.rightArm.rotation.x += 0.4; this.leftArm.rotation.x += 0.4;
      this.rightLeg.position.set(-1.9 * PXs, 12 * PXs, -4 * PXs);
      this.leftLeg.position.set(1.9 * PXs, 12 * PXs, -4 * PXs);
      this.head.position.y = 19.8 * PXs; this.body.position.y = 20.8 * PXs;
      this.rightArm.position.y = 18.8 * PXs; this.leftArm.position.y = 18.8 * PXs;
    } else {
      this.rightLeg.position.set(-1.9 * PXs, 12 * PXs, 0); this.leftLeg.position.set(1.9 * PXs, 12 * PXs, 0);
      this.head.position.y = 24 * PXs; this.body.position.y = 24 * PXs;
      this.rightArm.position.y = 22 * PXs; this.leftArm.position.y = 22 * PXs;
    }
    if (pose === 'swimming') {
      // Pose.SWIMMING out of water = lying face down, arms stretched past the head
      this.pivot.rotation.x = Math.PI / 2;
      this.pivot.position.set(0, 0.16, -1.0);
      this.head.rotation.set(-Math.PI / 4 + hp * 0.3, hy, 0);
      if (st.aim) {
        this.rightArm.rotation.set(-Math.PI + 0.25, 0.15, 0);
        this.leftArm.rotation.set(-Math.PI + 0.35, -0.25, 0);
      } else {
        this.rightArm.rotation.set(0, -Math.PI, -Math.PI);
        this.leftArm.rotation.set(0, -Math.PI, -Math.PI);
      }
      this.rightLeg.rotation.set(0.3, 0, 0);
      this.leftLeg.rotation.set(-0.3, 0, 0);
    }
    if (pose === 'sleeping') {
      this.pivot.rotation.x = -Math.PI / 2;
      this.pivot.position.set(0, 0.14, 0.9);
      this.rightArm.rotation.set(0, 0, 0); this.leftArm.rotation.set(0, 0, 0);
      this.rightLeg.rotation.set(0, 0, 0); this.leftLeg.rotation.set(0, 0, 0);
    }
  }
}
