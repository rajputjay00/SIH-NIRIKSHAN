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

  const response = await fetch(`${BASE}/scan`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Scan failed');
  }

  return response.json();
}
