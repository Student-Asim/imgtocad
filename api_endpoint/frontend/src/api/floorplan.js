const API_BASE = 'http://127.0.0.1:8000';

async function parseResponse(res) {
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || 'Request failed');
  }

  return data;
}

export async function generateSync(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    body: formData,
  });

  return parseResponse(res);
}

export async function generateAsync(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/generate/async`, {
    method: 'POST',
    body: formData,
  });

  return parseResponse(res);
}

export async function getJob(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  const data = await res.json().catch(() => ({}));

  if (res.status === 202) {
    return {
      status: 'processing',
      detail: data.detail || 'Job still processing',
    };
  }

  if (!res.ok) {
    throw new Error(data.detail || 'Failed to fetch job');
  }

  return data;
}

export function resolveApiUrl(path) {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  return `${API_BASE}${path}`;
}