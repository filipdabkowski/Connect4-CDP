import axios from "axios";

export const api = axios.create({
    // baseURL: import.meta.env.AUTH_API_BASE_URL,
    baseURL: "http://localhost:8000/api/",
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true,
    timeout: 1000,
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});
