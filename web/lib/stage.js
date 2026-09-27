// Renderer + sky + fog + time of day, shared by the set viewer and the film player.
import * as THREE from 'three';
THREE.ColorManagement.enabled = false; // work in plain sRGB values like vanilla
import { VoxelWorld } from './world.js';

const TAU = Math.PI * 2;
export function celestialAngle(t) {
  const d0 = ((t / 24000 - 0.25) % 1 + 1) % 1;
  const d1 = 0.5 - Math.cos(d0 * Math.PI) / 2;
  return (d0 * 2 + d1) / 3;
}
export function skyBrightness(t) {
  return Math.max(0, Math.min(1, Math.cos(celestialAngle(t) * TAU) * 2 + 0.5));
}
function sunriseColor(t) {
  const f = Math.cos(celestialAngle(t) * TAU);
  if (f < -0.4 || f > 0.4) return null;
  const f3 = f / 0.4 * 0.5 + 0.5;
  let f4 = 1 - (1 - Math.sin(f3 * Math.PI)) * 0.99; f4 *= f4;
  return [f3 * 0.3 + 0.7, f3 * f3 * 0.7 + 0.2, 0.2, f4];
}
const BASE_SKY = [122 / 255, 166 / 255, 1.0];
const BASE_FOG = [0.7529, 0.847, 1.0];

export class Stage {
  constructor(canvas, W, H) {
    this.W = W; this.H = H;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true });
    this.renderer.autoClear = false;
    this.renderer.setSize(W, H, false);
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(70, W / H, 0.05, 140);
    this.skyScene = new THREE.Scene();
    this.skyCam = new THREE.PerspectiveCamera(70, W / H, 1, 3000);
    this.fogFar = 118;
    this.scene.fog = new THREE.Fog(0xc0d8ff, this.fogFar * 0.55, this.fogFar);
    // sky dome
    const sg = new THREE.SphereGeometry(400, 32, 16);
    this.skyMat = new THREE.ShaderMaterial({
      uniforms: { top: { value: new THREE.Color() }, horizon: { value: new THREE.Color() }, sunset: { value: new THREE.Vector4() }, sunDir: { value: new THREE.Vector3() } },
      vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: `uniform vec3 top; uniform vec3 horizon; uniform vec4 sunset; uniform vec3 sunDir; varying vec3 vP;
        void main(){ float h = clamp(vP.y, -1.0, 1.0);
          vec3 c = mix(horizon, top, smoothstep(-0.02, 0.35, h));
          if (h < -0.02) c = mix(horizon, horizon*0.6, smoothstep(-0.02,-0.4,h));
          float toward = max(0.0, dot(normalize(vec3(vP.x,0.0,vP.z)), normalize(vec3(sunDir.x,0.0,sunDir.z))));
          float band = sunset.w * pow(toward, 3.0) * (1.0 - smoothstep(0.0, 0.45, abs(h - 0.05)));
          c = mix(c, sunset.rgb, clamp(band, 0.0, 1.0));
          gl_FragColor = vec4(c, 1.0); }`,
      side: THREE.BackSide, depthWrite: false, fog: false,
    });
    this.sky = new THREE.Mesh(sg, this.skyMat);
    this.sky.renderOrder = -10;
    this.skyScene.add(this.sky);
    // sun
    const sunTex = new THREE.TextureLoader().load('../build/preview/tex/sun.png');
    sunTex.magFilter = THREE.NearestFilter; 
    this.sun = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshBasicMaterial({ map: sunTex, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, fog: false }));
    this.sun.renderOrder = -9;
    this.skyScene.add(this.sun);
    // clouds
    const ct = new THREE.TextureLoader().load('../build/preview/tex/clouds.png');
    ct.magFilter = THREE.NearestFilter; ct.wrapS = ct.wrapT = THREE.RepeatWrapping; ct.repeat.set(4, 4);
    this.cloudMat = new THREE.MeshBasicMaterial({ map: ct, transparent: true, opacity: 0.8, depthWrite: false, fog: false, side: THREE.DoubleSide, alphaTest: 0.1 });
    this.clouds = new THREE.Mesh(new THREE.PlaneGeometry(12 * 256 * 4, 12 * 256 * 4), this.cloudMat);
    this.clouds.rotation.x = -Math.PI / 2;
    this.clouds.position.y = 192.3;
    this.skyScene.add(this.clouds);
    // entity lights
    this.amb = new THREE.AmbientLight(0xffffff, 1.4);
    this.dir = new THREE.DirectionalLight(0xffffff, 1.2);
    this.dir.position.set(0.2, 1, -0.7);
    this.scene.add(this.amb, this.dir);
    this.brightness = 1;
  }

  async loadWorld(base) {
    const data = await (await fetch(base + '/world.json')).json();
    const atlas = await new THREE.TextureLoader().loadAsync(base + '/atlas.png');
    atlas.magFilter = THREE.NearestFilter; atlas.minFilter = THREE.NearestFilter; atlas.generateMipmaps = false;
    
    this.world = new VoxelWorld(data, atlas);
    this.world.update();
    this.scene.add(this.world.group);
    return this.world;
  }

  setTime(t, weatherDark = 0) {
    const a = celestialAngle(t);
    const f = skyBrightness(t) * (1 - weatherDark);
    const sky = BASE_SKY.map(v => v * f);
    const fog = [BASE_FOG[0] * (f * 0.94 + 0.06), BASE_FOG[1] * (f * 0.94 + 0.06), BASE_FOG[2] * (f * 0.91 + 0.09)];
    const sr = sunriseColor(t);
    this.skyMat.uniforms.top.value.setRGB(...sky);
    this.skyMat.uniforms.horizon.value.setRGB(...fog);
    const sd = new THREE.Vector3(-Math.sin(a * TAU), Math.cos(a * TAU), 0);
    this.skyMat.uniforms.sunDir.value.copy(sd);
    const srgb = new THREE.Color().setRGB(...(sr ? sr.slice(0, 3) : [0, 0, 0]));
    this.skyMat.uniforms.sunset.value.set(srgb.r, srgb.g, srgb.b, sr ? sr[3] : 0);
    this.sunDir = sd;
    // fog tinted toward the sunset when looking at the sun is handled in the dome; keep fog = horizon colour
    this.scene.fog.color.setRGB(...fog);
    if (sr) this.scene.fog.color.lerp(new THREE.Color().setRGB(sr[0], sr[1], sr[2]), sr[3] * 0.25);
    const b = 0.22 + 0.78 * f;
    this.brightness = b;
    if (this.world) for (const m of this.world.materials) m.color.setScalar(b);
    this.amb.intensity = 1.35 * b;
    this.dir.intensity = 1.1 * b;
    if (sr) { this.dir.color.setRGB(1, 0.85 + 0.15 * (1 - sr[3]), 0.7 + 0.3 * (1 - sr[3])); } else this.dir.color.setRGB(1, 1, 1);
    this.dir.position.copy(sd).multiplyScalar(10).add(new THREE.Vector3(0, 3, -4));
    this.cloudMat.color.setScalar(0.35 + 0.65 * f);
    this.time = t;
  }

  render(cam) {
    const c = cam || this.camera;
    const sc = this.skyCam;
    sc.position.copy(c.position); sc.quaternion.copy(c.quaternion);
    if (sc.fov !== c.fov || sc.aspect !== c.aspect) { sc.fov = c.fov; sc.aspect = c.aspect; sc.updateProjectionMatrix(); }
    this.sky.position.copy(c.position);
    this.sun.position.copy(c.position).addScaledVector(this.sunDir || new THREE.Vector3(0, 1, 0), 350);
    this.sun.lookAt(c.position);
    this.clouds.position.x = c.position.x - ((c.position.x) % (12 * 256)) + (this.time || 0) * 0.03 % (12 * 256);
    this.clouds.position.z = c.position.z - (c.position.z % (12 * 256));
    this.renderer.clear();
    this.renderer.render(this.skyScene, sc);
    this.renderer.clearDepth();
    this.renderer.render(this.scene, c);
  }
}

// yaw/pitch in Minecraft degrees -> camera orientation
export function aimCamera(cam, pos, yaw, pitch, fov = 70) {
  cam.position.set(pos[0], pos[1], pos[2]);
  const y = yaw * Math.PI / 180, p = pitch * Math.PI / 180;
  const dir = new THREE.Vector3(-Math.sin(y) * Math.cos(p), -Math.sin(p), Math.cos(y) * Math.cos(p));
  cam.up.set(0, 1, 0);
  cam.lookAt(cam.position.clone().add(dir));
  if (cam.fov !== fov) { cam.fov = fov; cam.updateProjectionMatrix(); }
}
