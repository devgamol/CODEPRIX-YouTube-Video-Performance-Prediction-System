const API_BASE = "http://localhost:8000";
let authToken = null;

export function setAuthToken(token) {
  authToken = token;
}

const authFetch = (url, options = {}) => {
  return fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
  });
};

export async function uploadVideo(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authFetch("/upload", {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.detail || "Upload failed");
  }
  return data;
}

export async function getJobStatus(job_id) {
  const response = await authFetch(`/status/${job_id}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.detail || "Failed to fetch job status");
  }
  return data;
}

export async function exportReport(resultData) {
  const response = await authFetch("/export", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(resultData),
  });

  if (!response.ok) {
    let message = "Failed to export report";
    try {
      const data = await response.json();
      message = data?.detail || message;
    } catch {
      // Keep default message when response is non-JSON.
    }
    throw new Error(message);
  }

  return response.blob();
}

export { API_BASE, authFetch };
