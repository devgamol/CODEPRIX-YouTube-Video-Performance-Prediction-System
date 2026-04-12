import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

export async function uploadVideo(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function getJobStatus(job_id) {
  const response = await api.get(`/status/${job_id}`);
  return response.data;
}
