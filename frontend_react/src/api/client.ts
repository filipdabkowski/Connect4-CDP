import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.AUTH_API_BASE_URL,
  timeout: 1000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
