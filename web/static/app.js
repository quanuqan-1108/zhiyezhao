// 职业照小能手 Web - M3 Enhanced Frontend
// Material Design 3 风格前端逻辑：主题切换、Snackbar、动效、状态层

const state = {
  taskId: null,
  userImageUrl: null,
  baselinePhotoUrl: null,
  photos: [],
  currentModalPhotoIdx: null,
  step: 1,
  theme: 'system',
};

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove('hidden');
const hide = (id) => $(id).classList.add('hidden');

// ========== 主题切换 (M3 light/dark/system) ==========
function initTheme() {
  const saved = localStorage.getItem('m3-theme') || 'system';
  state.theme = saved;
  applyTheme(saved);
  $('btn-theme').addEventListener('click', toggleTheme);

  // 系统主题变化时跟随
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (state.theme === 'system') applyTheme('system');
  });
}

function applyTheme(theme) {
  state.theme = theme;
  let actual;
  if (theme === 'system') {
    actual = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } else {
    actual = theme;
  }
  if (actual === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    $('theme-icon').textContent = '☀️';
    $('btn-theme').title = '切换到浅色模式';
  } else {
    document.documentElement.setAttribute('data-theme', 'light');
    $('theme-icon').textContent = '🌙';
    $('btn-theme').title = '切换到深色模式';
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  localStorage.setItem('m3-theme', next);
  applyTheme(next);
  // 按钮动效
  $('btn-theme').animate(
    [{ transform: 'scale(1)' }, { transform: 'scale(0.9)' }, { transform: 'scale(1)' }],
    { duration: 200, easing: 'cubic-bezier(0.2, 0, 0, 1)' }
  );
}

// ========== Snackbar (替代 alert) ==========
function snackbar(msg, duration = 3000) {
  const el = $('snackbar');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('show'), duration);
}

// ========== 上传 ==========
const uploadZone = $('upload-zone');
const fileInput = $('file-input');
const uploadEmpty = $('upload-empty');
const uploadPreview = $('upload-preview');
const btnStart = $('btn-start');

let uploadedFiles = [];

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    fileInput.click();
  }
});

uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('dragover');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  handleFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

function handleFiles(files) {
  const imageFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
  if (imageFiles.length === 0) {
    snackbar('请选择图片文件');
    return;
  }
  const combined = [...uploadedFiles, ...imageFiles].slice(0, 5);
  uploadedFiles = combined;
  renderPreview();
  btnStart.disabled = uploadedFiles.length === 0;
  snackbar(`已上传 ${uploadedFiles.length} 张照片`);
}

function renderPreview() {
  uploadPreview.innerHTML = '';
  if (uploadedFiles.length === 0) {
    uploadEmpty.style.display = 'block';
    return;
  }
  uploadEmpty.style.display = 'none';

  uploadedFiles.forEach((file, i) => {
    const wrap = document.createElement('div');
    wrap.className = 'img-wrap';

    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    img.alt = file.name;

    const btn = document.createElement('button');
    btn.className = 'remove';
    btn.textContent = '×';
    btn.title = '移除';
    btn.setAttribute('aria-label', '移除此照片');
    btn.onclick = (e) => {
      e.stopPropagation();
      uploadedFiles.splice(i, 1);
      renderPreview();
      btnStart.disabled = uploadedFiles.length === 0;
    };

    wrap.appendChild(img);
    wrap.appendChild(btn);
    uploadPreview.appendChild(wrap);
  });
}

// ========== 步骤切换 (M3 Stepper) ==========
function gotoStep(n) {
  state.step = n;
  document.querySelectorAll('.stepper-item').forEach(s => {
    const sn = parseInt(s.dataset.step, 10);
    s.classList.toggle('active', sn === n);
    s.classList.toggle('done', sn < n);
  });

  // 隐藏所有 panel
  hide('panel-upload');
  hide('panel-baseline');
  hide('panel-gallery');

  // 显示当前 panel + 动效
  let panelId;
  if (n <= 2) panelId = 'panel-upload';
  else if (n === 3) panelId = 'panel-baseline';
  else panelId = 'panel-gallery';
  const panel = $(panelId);
  panel.classList.remove('hidden');
  panel.animate(
    [
      { opacity: 0, transform: 'translateY(8px)' },
      { opacity: 1, transform: 'translateY(0)' },
    ],
    { duration: 300, easing: 'cubic-bezier(0.2, 0, 0, 1)' }
  );

  // FAB 仅在 gallery 阶段显示
  $('fab-top').classList.toggle('show', n === 4);
}

// ========== 上传 + 创建任务 ==========
btnStart.addEventListener('click', async () => {
  if (uploadedFiles.length === 0) return;

  const fd = new FormData();
  fd.append('photo', uploadedFiles[0]);
  fd.append('field', $('field').value);
  fd.append('use_case', $('use-case').value);
  fd.append('style', $('style').value);
  fd.append('wear_glasses', $('wear-glasses').value);
  fd.append('framing', $('framing').value);

  showLoading('上传照片 + 创建任务…', '约 1-2 秒');
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    state.taskId = data.task_id;
    state.userImageUrl = data.user_image_url;
    hideLoading();
    gotoStep(2);
    await generateBaseline();
  } catch (e) {
    hideLoading();
    snackbar('上传失败: ' + e.message, 5000);
  }
});

// ========== 生成基准照 ==========
async function generateBaseline() {
  if (!state.taskId) return;
  showLoading('生成基准照中…', '约 30-60 秒');
  try {
    const res = await fetch(`/api/generate/baseline/${state.taskId}`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    state.baselinePhotoUrl = data.url;
    state.photos = [data];

    const img = $('baseline-img');
    img.src = data.url + '?t=' + Date.now();
    img.onload = () => {
      hideLoading();
      gotoStep(3);
      snackbar('基准照已生成 ✓');
    };
    img.onerror = () => {
      hideLoading();
      gotoStep(3);
    };
  } catch (e) {
    hideLoading();
    snackbar('基准照生成失败: ' + e.message, 5000);
  }
}

$('btn-confirm').addEventListener('click', async () => {
  showLoading('生成其余 5 张中…', '约 1-2 分钟');
  try {
    const res = await fetch(`/api/generate/rest/${state.taskId}`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    state.photos = data.photos;
    renderGallery();
    hideLoading();
    gotoStep(4);
    snackbar('6 张形象照已全部生成 ✓');
  } catch (e) {
    hideLoading();
    snackbar('生成失败: ' + e.message, 5000);
  }
});

$('btn-regen-baseline').addEventListener('click', () => {
  if (confirm('重新生成基准照将消耗一次调整机会（基准照阶段最多 5 次），继续？')) {
    generateBaseline();
  }
});

$('btn-back').addEventListener('click', () => gotoStep(1));

// ========== Gallery ==========
function renderGallery() {
  const gallery = $('gallery');
  gallery.innerHTML = '';

  state.photos.forEach((p, i) => {
    const card = document.createElement('div');
    card.className = 'photo-card';

    const img = document.createElement('img');
    img.src = p.url + '?t=' + Date.now();
    img.alt = p.name;
    img.loading = 'lazy';
    img.onclick = () => openViewer(p.idx);

    const body = document.createElement('div');
    body.className = 'photo-card-body';
    body.innerHTML = `
      <div class="photo-card-title">${p.idx}. ${p.name}</div>
      <div class="photo-card-idx">3:4 竖版 · 1024×1536</div>
      <div class="photo-card-actions">
        <button class="btn btn-tonal btn-sm" data-action="view" data-idx="${p.idx}">🔍 查看</button>
        <button class="btn btn-outlined btn-sm" data-action="prompt" data-idx="${p.idx}">📄 提示词</button>
        <button class="btn btn-outlined btn-sm" data-action="revise" data-idx="${p.idx}">✏️ 修改</button>
        <button class="btn btn-text btn-sm" data-action="download" data-idx="${p.idx}">⬇ 下载</button>
      </div>
    `;

    // 事件委托 - 避免内联 onclick 在 strict mode 报错
    body.querySelectorAll('button[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const idx = parseInt(btn.dataset.idx, 10);
        if (action === 'view') openViewer(idx);
        else if (action === 'prompt') viewPrompt(idx);
        else if (action === 'revise') openRevise(idx);
        else if (action === 'download') downloadOne(idx);
      });
    });

    card.appendChild(img);
    card.appendChild(body);
    gallery.appendChild(card);

    // 入场动效
    card.animate(
      [
        { opacity: 0, transform: 'translateY(20px) scale(0.95)' },
        { opacity: 1, transform: 'translateY(0) scale(1)' },
      ],
      { duration: 350, delay: i * 80, easing: 'cubic-bezier(0.2, 0, 0, 1)', fill: 'backwards' }
    );
  });
}

// ========== Modal: Viewer ==========
function openViewer(idx) {
  const photo = state.photos.find(p => p.idx === idx);
  if (!photo) return;
  state.currentModalPhotoIdx = idx;
  $('modal-img').src = photo.url + '?t=' + Date.now();
  $('modal-info').textContent = `${photo.idx}. ${photo.name} · 3:4 竖版 · 1024×1536`;
  show('modal-viewer');
}

function closeViewer() {
  hide('modal-viewer');
  state.currentModalPhotoIdx = null;
}

$('modal-download').addEventListener('click', () => {
  if (state.currentModalPhotoIdx) downloadOne(state.currentModalPhotoIdx);
});
$('modal-view-prompt').addEventListener('click', () => {
  if (state.currentModalPhotoIdx) {
    closeViewer();
    setTimeout(() => viewPrompt(state.currentModalPhotoIdx), 200);
  }
});
$('modal-revise').addEventListener('click', () => {
  if (state.currentModalPhotoIdx) {
    const idx = state.currentModalPhotoIdx;
    closeViewer();
    setTimeout(() => openRevise(idx), 200);
  }
});

// ========== Modal: Prompt ==========
function viewPrompt(idx) {
  const photo = state.photos.find(p => p.idx === idx);
  if (!photo) return;
  $('prompt-text').textContent = photo.prompt || '(暂无提示词)';
  const u = photo.usage || {};
  $('prompt-usage').textContent = u.total_tokens
    ? `Token 用量: input_images=${u.input_images || 0}, output=${u.output_tokens || 0}, total=${u.total_tokens}`
    : '';
  show('modal-prompt');
}

function closePrompt() { hide('modal-prompt'); }

// ========== Modal: Revise ==========
function openRevise(idx) {
  const photo = state.photos.find(p => p.idx === idx);
  if (!photo) return;
  state.currentModalPhotoIdx = idx;
  $('revise-name').textContent = photo.name;
  $('revise-input').value = '';
  show('modal-revise');
  setTimeout(() => $('revise-input').focus(), 100);
}

function closeRevise() {
  hide('modal-revise');
  state.currentModalPhotoIdx = null;
}

$('btn-revise-submit').addEventListener('click', async () => {
  const idx = state.currentModalPhotoIdx;
  const requirement = $('revise-input').value.trim();
  if (!idx || !requirement) {
    snackbar('请输入修改要求');
    return;
  }

  closeRevise();
  showLoading(`重新生成第 ${idx} 张中…`, '约 30-60 秒');

  try {
    const fd = new FormData();
    fd.append('requirement', requirement);
    const res = await fetch(`/api/revise/${state.taskId}/${idx}`, { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();

    // 更新 state 里该张
    const i = state.photos.findIndex(p => p.idx === idx);
    if (i >= 0) state.photos[i] = { ...state.photos[i], ...data };

    renderGallery();
    hideLoading();
    snackbar(`第 ${idx} 张已重新生成 ✓`);
  } catch (e) {
    hideLoading();
    snackbar('修改失败: ' + e.message, 5000);
  }
});

// ========== 下载 ==========
function downloadOne(idx) {
  if (!state.taskId) return;
  window.open(`/api/download/${state.taskId}/${idx}`, '_blank');
}

$('btn-download-all').addEventListener('click', () => {
  if (!state.taskId) return;
  window.open(`/api/download/${state.taskId}/all`, '_blank');
  snackbar('打包下载已开始…');
});

$('btn-new-task').addEventListener('click', () => {
  if (confirm('开始新任务将清空当前进度，继续？')) {
    location.reload();
  }
});

// ========== Loading ==========
function showLoading(text, sub) {
  $('loading-text').textContent = text;
  if (sub) $('loading-sub').textContent = sub;
  show('loading');
}
function hideLoading() { hide('loading'); }

// ========== ESC 关闭模态框 ==========
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeViewer();
    closePrompt();
    closeRevise();
  }
});

// ========== 滚动监听：App Bar 阴影 + FAB ==========
window.addEventListener('scroll', () => {
  const appBar = $('app-bar');
  if (window.scrollY > 8) appBar.classList.add('scrolled');
  else appBar.classList.remove('scrolled');
});

$('fab-top').addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ========== 初始化 ==========
initTheme();
gotoStep(1);
