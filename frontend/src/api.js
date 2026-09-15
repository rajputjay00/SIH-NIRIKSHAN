const BASE = (import.meta.env.VITE_API_URL ?? "/api").replace(/\/$/, "");

export async function checkHealth() {
  const response = await fetch(`${BASE}/health`);
  if (!response.ok) {
    throw new Error('Health check failed');
  }
  return response.json();
}

export async function scanImage(file, context = {}) {
  const formData = new FormData();
  formData.append('file', file);
  if (context.packageType) formData.append('package_type', context.packageType);
  if (context.category) formData.append('category', context.category);
  if (context.isImport !== undefined && context.isImport !== null) {
    formData.append('is_import', context.isImport);
  }
  if (context.channel) formData.append('channel', context.channel);
  if (context.geometryChecks) formData.append('geometry_checks', 'true');

  const response = await fetch(`${BASE}/scan`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Scan failed');
  }

  return response.json();
}

async function postJson(path, payload) {
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let detail = `${response.status}`;
    try { detail = (await response.json()).detail || detail; } catch (e) { /* ignore */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response;
}

// Tol — R31 single-package MPE check
export async function weighPack(payload) {
  const response = await postJson('/tol/weigh', payload);
  return response.json();
}

// Tol — R32 lot inspection (Rules 19–21, Fifth/Sixth Schedules)
export async function inspectLot(payload) {
  const response = await postJson('/tol/lot', payload);
  return response.json();
}

// Tol — Seventh Schedule Form A/B as a PDF blob
export async function downloadLotForm(payload) {
  const response = await postJson('/tol/lot/form', payload);
  return response.blob();
}

// Jaal — e-commerce listing check (R29 Rule 6(10), R30 Rule 31)
export async function checkListing({ url, files = [], isImport } = {}) {
  const formData = new FormData();
  if (url) formData.append('url', url);
  if (isImport !== undefined && isImport !== null) formData.append('is_import', String(isImport));
  files.slice(0, 6).forEach((f, i) => formData.append(`file_${i + 1}`, f));

  const response = await fetch(`${BASE}/listing/check`, { method: 'POST', body: formData });
  if (!response.ok) {
    let detail = `${response.status}`;
    try { detail = (await response.json()).detail || detail; } catch (e) { /* ignore */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response.json();
}
