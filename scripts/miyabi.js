/* 和食処 雅 — ページの動き
   ヘッダー・ナビ・出現アニメーション・器のビューア。
   three.js はリアルタイム3Dに切り替えたときだけ読み込む。 */

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* 連番の URL。{i} を 2 桁に埋める */
function frameUrl(pattern, index) {
  return pattern.replace('{i}', String(index).padStart(2, '0'));
}

function preloadFrames(pattern, indices) {
  return Promise.all(indices.map((i) => new Promise((resolve) => {
    const img = new Image();
    img.decoding = 'async';
    img.onload = img.onerror = () => resolve(img);
    img.src = frameUrl(pattern, i);
  })));
}

/* 待ちが長引いても先へ進む */
function atMost(promise, ms) {
  return Promise.race([promise, new Promise((r) => setTimeout(r, ms))]);
}

/* rAF で間引くスクロール購読 */
function onScroll(handler) {
  let queued = false;
  const run = () => { queued = false; handler(); };
  const request = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(run);
  };
  window.addEventListener('scroll', request, { passive: true });
  window.addEventListener('resize', request, { passive: true });
  handler();
}

/* ------------------------------------------------------------- ヘッダー */
function setupHeader() {
  const head = document.getElementById('head');
  if (!head) return;
  const update = () => head.classList.toggle('is-stuck', window.scrollY > 24);
  update();
  window.addEventListener('scroll', update, { passive: true });
}

/* --------------------------------------------------------- ナビ(スマホ) */
function setupNav() {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('nav');
  if (!toggle || !nav) return;

  const setOpen = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  };

  toggle.addEventListener('click', () => {
    setOpen(toggle.getAttribute('aria-expanded') !== 'true');
  });
  nav.addEventListener('click', (event) => {
    if (event.target.closest('a')) setOpen(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });
  // 画面が広がったらドロワーの状態を捨てる
  window.matchMedia('(min-width: 48rem)').addEventListener('change', (m) => {
    if (m.matches) setOpen(false);
  });
}

/* ------------------------------------------------------- 出現のきっかけ */
function setupReveal() {
  const targets = document.querySelectorAll('.reveal');
  if (!targets.length) return;
  if (reduceMotion || !('IntersectionObserver' in window)) {
    targets.forEach((el) => el.classList.add('is-in'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      io.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -12% 0px', threshold: 0.12 });
  targets.forEach((el) => io.observe(el));
}

/* ------------------------------------------------------------ 器ビューア */
class Turntable {
  constructor(root) {
    this.root = root;
    this.img = root.querySelector('.viewer__img');
    this.frame = root.querySelector('.viewer__frame');
    this.spinner = root.querySelector('.viewer__spinner');
    this.grab = root.querySelector('.viewer__grab');
    this.count = Number(root.dataset.frames) || 1;
    this.pattern = root.dataset.src || '';
    this.index = 0;
    this.touched = false;
    this.dragging = false;
    this.lastX = 0;
    this.carry = 0;
    this.visible = false;
    this.enabled = false;
  }

  url(i) {
    return this.pattern.replace('{i}', String(i).padStart(2, '0'));
  }

  /* 画面に入るまでは 32 コマを読みにいかない */
  watch() {
    if (!('IntersectionObserver' in window)) {
      this.visible = true;
      this.preload();
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        this.visible = entry.isIntersecting;
        if (entry.isIntersecting && !this.started) {
          this.started = true;
          this.preload();
        }
      });
    }, { threshold: 0.2, rootMargin: '25% 0px' });
    io.observe(this.frame);
  }

  async preload() {
    if (!this.pattern || this.count < 2) return;
    this.spinner.hidden = false;
    const loads = [];
    for (let i = 0; i < this.count; i += 1) {
      loads.push(new Promise((resolve) => {
        const img = new Image();
        img.decoding = 'async';
        img.onload = img.onerror = () => resolve(img);
        img.src = this.url(i);
      }));
    }
    this.frames = await Promise.all(loads);
    this.spinner.hidden = true;
    // 1枚も取れなければ回せないので、案内も引っ込める
    this.enabled = this.frames.some((f) => f.naturalWidth > 0);
    if (this.enabled) {
      this.bind();
    } else {
      this.grab.hidden = true;
      this.root.closest('.utsuwa__stage')?.setAttribute('hidden', '');
    }
  }

  show(index) {
    const i = ((index % this.count) + this.count) % this.count;
    if (i === this.index) return;
    this.index = i;
    this.img.src = this.url(i);
  }

  spin(delta) {
    this.carry += delta;
    const step = Math.trunc(this.carry);
    if (step) {
      this.carry -= step;
      this.show(this.index + step);
    }
  }

  bind() {
    const frame = this.frame;
    // ドラッグ量 1 コマぶんの距離。幅に合わせて感度を決める
    const sensitivity = () => Math.max(frame.clientWidth / (this.count * 1.15), 6);

    frame.addEventListener('pointerdown', (event) => {
      if (this.mode3d) return;
      this.dragging = true;
      this.touched = true;
      this.lastX = event.clientX;
      frame.classList.add('is-dragging');
      frame.setPointerCapture(event.pointerId);
    });
    frame.addEventListener('pointermove', (event) => {
      if (!this.dragging) return;
      const dx = event.clientX - this.lastX;
      this.lastX = event.clientX;
      this.spin(-dx / sensitivity());
    });
    const release = (event) => {
      if (!this.dragging) return;
      this.dragging = false;
      frame.classList.remove('is-dragging');
      if (event.pointerId !== undefined && frame.hasPointerCapture?.(event.pointerId)) {
        frame.releasePointerCapture(event.pointerId);
      }
    };
    // setPointerCapture 中は境界イベントが飛ばないので pointerleave は見ない
    frame.addEventListener('pointerup', release);
    frame.addEventListener('pointercancel', release);

    this.grab.addEventListener('keydown', (event) => {
      const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: 1, ArrowDown: -1 }[event.key];
      if (!step) return;
      event.preventDefault();
      this.touched = true;
      this.show(this.index + step);
    });
    let held = null;
    this.grab.addEventListener('pointerdown', () => {
      this.touched = true;
      held = setInterval(() => this.show(this.index + 1), 70);
    });
    ['pointerup', 'pointerleave', 'pointercancel', 'blur'].forEach((type) => {
      this.grab.addEventListener(type, () => { clearInterval(held); held = null; });
    });

    if (!reduceMotion) this.idle();
  }

  /* 触られるまでは、ゆっくり回して「回せること」を伝える */
  idle() {
    let last = performance.now();
    const tick = (now) => {
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      if (!this.touched && this.visible && !this.dragging && !this.mode3d) {
        this.spin(dt * this.count * 0.055);
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
}

/* ------------------------------------------- リアルタイム3D (three.js) */
async function setupRealtime(root, turntable) {
  const button = root.querySelector('.viewer__mode');
  const canvas = root.querySelector('.viewer__canvas');
  const src = root.dataset.model;
  if (!button || !canvas || !src || !window.WebGLRenderingContext) return;

  // WebGL が実際に使えるかを確かめてから切り替えボタンを出す
  const probe = document.createElement('canvas').getContext('webgl2')
    || document.createElement('canvas').getContext('webgl');
  if (!probe) return;
  button.hidden = false;

  let scene = null;
  let start = null;

  button.addEventListener('click', async () => {
    const on = button.getAttribute('aria-pressed') !== 'true';
    button.setAttribute('aria-pressed', String(on));
    button.textContent = on ? '写真に戻す' : 'リアルタイム3Dで見る';
    turntable.mode3d = on;
    turntable.img.hidden = on;
    canvas.hidden = !on;
    // 写真を隠している間は、canvas 側が器の代わりを務める
    canvas.setAttribute('aria-hidden', String(!on));
    if (on) {
      canvas.setAttribute('role', 'img');
      canvas.setAttribute('aria-label', turntable.img.alt);
    }

    if (!on || scene) return;
    root.querySelector('.viewer__spinner').hidden = false;
    try {
      start = start || (await buildScene(canvas, src));
      scene = start;
    } catch (error) {
      console.warn('3D の読み込みに失敗しました', error);
      button.hidden = true;
      turntable.mode3d = false;
      turntable.img.hidden = false;
      canvas.hidden = true;
    } finally {
      root.querySelector('.viewer__spinner').hidden = true;
    }
  });
}

async function buildScene(canvas, src) {
  const THREE = await import('three');
  const { GLTFLoader } = await import('./vendor/GLTFLoader.js');
  const { RoomEnvironment } = await import('./vendor/RoomEnvironment.js');

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const key = new THREE.DirectionalLight(0xfff0dd, 2.4);
  key.position.set(1.4, 2.0, 1.6);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xffd9a8, 2.0);
  rim.position.set(-1.2, 1.0, -1.8);
  scene.add(rim);

  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 50);
  const pivot = new THREE.Group();
  scene.add(pivot);

  const gltf = await new GLTFLoader().loadAsync(src);
  const model = gltf.scene;

  // 原点まわりに座り直させてから、画角いっぱいに収める
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  model.position.sub(center);
  pivot.add(model);

  const radius = Math.max(size.x, size.y, size.z) * 0.5;
  const distance = radius / Math.sin((camera.fov * Math.PI) / 360) * 1.35;
  camera.position.set(0, radius * 0.72, distance);
  camera.lookAt(0, 0, 0);

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    const side = Math.max(Math.min(rect.width, rect.height), 1);
    renderer.setSize(side, side, false);
    camera.aspect = 1;
    camera.updateProjectionMatrix();
  };
  resize();
  new ResizeObserver(resize).observe(canvas);

  let spin = 0.6;
  let dragging = false;
  let lastX = 0;
  let touched = false;
  const frame = canvas.closest('.viewer__frame');
  frame.addEventListener('pointerdown', (event) => {
    if (canvas.hidden) return;
    dragging = true; touched = true; lastX = event.clientX;
  });
  frame.addEventListener('pointermove', (event) => {
    if (!dragging) return;
    pivot.rotation.y += (event.clientX - lastX) * 0.01;
    lastX = event.clientX;
  });
  ['pointerup', 'pointercancel'].forEach((type) => {
    frame.addEventListener(type, () => { dragging = false; });
  });

  renderer.setAnimationLoop(() => {
    if (canvas.hidden) return;
    if (!touched && !reduceMotion) pivot.rotation.y += spin * 0.004;
    renderer.render(scene, camera);
  });
  return { renderer, scene };
}

/* --------------------------------------------------------------- 開幕 */
/* 紋を裏から正面へ回して見せる。Blender で焼いた連番をそのまま送る。 */
async function playOpening() {
  const root = document.documentElement;
  const el = document.getElementById('opening');
  if (!el || !root.classList.contains('is-opening')) return;

  const close = () => {
    try { sessionStorage.setItem('miyabi-opened', '1'); } catch (error) { /* 使えなくてよい */ }
    el.classList.add('is-closing');
    setTimeout(() => root.classList.remove('is-opening'), 560);
  };

  if (reduceMotion) { close(); return; }

  const img = document.getElementById('opening-mon');
  const pattern = el.dataset.src;
  const count = Number(el.dataset.frames) || 36;
  if (!img || !pattern) { close(); return; }

  // 裏 (半周) から正面 (0) まで。途中で横を向く瞬間が見せ場になる
  const order = [];
  for (let i = Math.round(count / 2); i < count; i += 1) order.push(i);
  order.push(0);

  let skipped = false;
  const skip = () => { skipped = true; };
  ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach((type) => {
    window.addEventListener(type, skip, { once: true, passive: true });
  });

  const loaded = await atMost(preloadFrames(pattern, order), 1200);
  // 連番が取れないときに欠けた画像を見せるくらいなら、幕を出さずに開く
  const ok = Array.isArray(loaded) && loaded.filter((f) => f.naturalWidth > 0).length;
  if (!ok || ok < order.length / 2) { close(); return; }

  for (const index of order) {
    if (skipped) break;
    img.src = frameUrl(pattern, index);
    await new Promise((r) => setTimeout(r, 55));
  }
  img.src = frameUrl(pattern, 0);
  el.classList.add('is-named');
  await new Promise((r) => setTimeout(r, skipped ? 180 : 620));
  close();
}

/* ------------------------------------------- スクロールに連動する紋 */
function setupScrollMon() {
  const el = document.getElementById('mon-scroll');
  const section = el && el.closest('section');
  if (!el || !section || reduceMotion) return;

  const img = el.querySelector('img');
  const pattern = el.dataset.src;
  const count = Number(el.dataset.frames) || 36;
  if (!img || !pattern) return;

  let current = 0;
  let ready = false;

  const update = () => {
    if (!ready) return;
    const rect = section.getBoundingClientRect();
    const span = rect.height + window.innerHeight;
    const seen = (window.innerHeight - rect.top) / span;
    const progress = Math.min(Math.max(seen, 0), 1);
    const index = Math.round(progress * (count - 1)) % count;
    if (index === current) return;
    current = index;
    img.src = frameUrl(pattern, index);
  };

  const start = () => {
    if (ready) return;
    const all = Array.from({ length: count }, (_, i) => i);
    preloadFrames(pattern, all).then((frames) => {
      if (!frames.some((f) => f.naturalWidth > 0)) {
        el.remove();   // 連番が無ければ飾りごと下ろす
        return;
      }
      ready = true;
      update();
    });
  };

  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { start(); io.disconnect(); }
    }, { rootMargin: '40% 0px' });
    io.observe(section);
  } else {
    start();
  }
  onScroll(update);
}

/* ------------------------------------------------- ヒーローの視差 */
function setupHeroParallax() {
  const media = document.querySelector('.hero__media img');
  if (!media || reduceMotion) return;
  onScroll(() => {
    // 敷いてある余白 (上下 9%) を越えないところまで
    const shift = Math.min(window.scrollY, window.innerHeight) * 0.085;
    media.style.transform = `translate3d(0, ${shift}px, 0)`;
  });
}

/* ---------------------------------------------------------------- 起動 */
function boot() {
  setupHeader();
  setupNav();
  setupReveal();
  setupHeroParallax();
  setupScrollMon();
  playOpening();

  const root = document.getElementById('viewer');
  if (root) {
    const turntable = new Turntable(root);
    turntable.watch();
    setupRealtime(root, turntable);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
