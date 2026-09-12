const BASE = (import.meta.env.VITE_API_URL ?? "/api").replace(/\/$/, "");

export async function checkHealth() {
  const response = await fetch(`${BASE}/health`);
  if (!response.ok) {
    throw new Error('Health check failed');
  }
  return response.json();
}

export async function scanImage(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${BASE}/scan`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Scan failed');
  }

  return response.json();
}

