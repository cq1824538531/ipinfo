// ── Config ──────────────────────────────────────────
const API_BASE = 'https://ipinfo.io/';

// ── DOM refs (populated on DOMContentLoaded) ─────────
const $ = id => document.getElementById(id);

let ipInput, loadingEl, errorEl, resultEl, searchBtn;

// ── Init ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  ipInput   = $('ipInput');
  loadingEl = $('loading');
  errorEl   = $('error');
  resultEl  = $('ipInfo');
  searchBtn = $('searchBtn');

  ipInput?.addEventListener('keydown', e => {
    if (e.key === 'Enter') queryIP();
  });

  // Auto-query on home page
  if (resultEl) queryMyIP();
});

// ── State helpers ─────────────────────────────────────
function showLoading() {
  loadingEl.style.display = 'block';
  errorEl.style.display   = 'none';
  resultEl.style.display  = 'none';
}

function hideLoading() {
  loadingEl.style.display = 'none';
}

function showError(msg) {
  errorEl.querySelector('.error-inner').innerHTML =
    `<span>⚠️</span><span>${msg}</span>`;
  errorEl.style.display  = 'flex';
  resultEl.style.display = 'none';
}

// ── Validation ────────────────────────────────────────
function validateIP(ip) {
  const re = /^(\d{1,3}\.){3}\d{1,3}$/;
  if (!re.test(ip)) return false;
  return ip.split('.').every(n => +n >= 0 && +n <= 255);
}

function isPrivateIP(ip) {
  const [a, b] = ip.split('.').map(Number);
  return a === 10 ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    a === 127;
}

// ── API ───────────────────────────────────────────────
async function queryIP() {
  const ip = ipInput.value.trim();
  if (!ip) { showError('请输入 IP 地址'); return; }
  if (!validateIP(ip)) { showError('请输入有效的 IPv4 地址（例如：8.8.8.8）'); return; }
  await fetchIPInfo(ip);
}

async function queryMyIP() {
  await fetchIPInfo('');
}

async function fetchIPInfo(ip) {
  showLoading();
  try {
    const url = ip ? `${API_BASE}${ip}/json` : `${API_BASE}json`;
    const res  = await fetch(url);
    if (!res.ok) throw new Error('网络请求失败，请稍后重试');

    const data = await res.json();
    if (data.bogon) throw new Error('该 IP 地址无法查询归属地（内网 / 保留地址）');

    render(data);
    if (!ip && ipInput) ipInput.value = data.ip;

  } catch (e) {
    console.error(e);
    showError(e.message || '查询失败，请检查网络连接');
  } finally {
    hideLoading();
  }
}

// ── Render ────────────────────────────────────────────
function render(d) {
  // IP + badge
  $('ipAddress').textContent = d.ip;
  const badge = $('ipType');
  const priv  = isPrivateIP(d.ip);
  badge.textContent = priv ? '内网 IP' : '公网 IP';
  badge.className   = `badge ${priv ? 'badge--private' : 'badge--public'}`;

  // Fields
  setValue('country',  d.country   || '—');
  setValue('region',   d.region    || '—');
  setValue('city',     d.city      || '—');
  setValue('zip',      d.postal    || '—');
  setValue('timezone', d.timezone  || '—');

  // org: "ASxxx ISP名"
  let ispName = '—', orgName = '—';
  if (d.org) {
    const parts = d.org.split(' ');
    if (parts.length > 1) {
      orgName = parts[0];
      ispName = parts.slice(1).join(' ');
    } else {
      ispName = orgName = d.org;
    }
  }
  setValue('isp', ispName);
  setValue('org', orgName);

  // Coords
  let lat = null, lon = null;
  if (d.loc) {
    [lat, lon] = d.loc.split(',').map(parseFloat);
    setValue('location', `${lat.toFixed(4)}, ${lon.toFixed(4)}`);
  } else {
    setValue('location', '—');
  }

  // Map links
  const mapArea = $('mapArea');
  if (lat && lon && mapArea) {
    mapArea.innerHTML = `
      <p class="map-section__title">🗺 在地图上查看</p>
      <div class="map-links">
        <a class="map-link-btn" href="https://www.google.com/maps?q=${lat},${lon}" target="_blank" rel="noopener noreferrer">
          🗾 Google Maps
        </a>
        <a class="map-link-btn" href="https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=12" target="_blank" rel="noopener noreferrer">
          🌍 OpenStreetMap
        </a>
      </div>`;
  } else if (mapArea) {
    mapArea.innerHTML = '<p style="color:var(--text-muted);font-size:13px">暂无地理位置信息</p>';
  }

  errorEl.style.display  = 'none';
  resultEl.style.display = 'block';
}

function setValue(id, val) {
  const el = $(id);
  if (el) el.textContent = val;
}
