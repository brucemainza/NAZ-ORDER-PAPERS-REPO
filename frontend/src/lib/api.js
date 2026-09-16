import axios from "axios";

export const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || undefined,
    withCredentials: true,
    headers: {
        "Content-Type": "application/json",
    },
});

export const backendApi = axios.create({
    baseURL: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080",
    withCredentials: false,
    headers: {
        "Content-Type": "application/json",
    },
});

api.interceptors.request.use((config) => {
    config.withCredentials = true;
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error?.response?.status === 401 && typeof window !== "undefined") {
            window.dispatchEvent(new Event("naz:auth-expired"));
        }
        return Promise.reject(error);
    }
);

export const searchAI = (queryText, options = {}) =>
    api.post("/api/ai/search", {
        query_text: queryText,
        session_id: options.sessionId || null,
        item_type: options.itemType || null,
        status: options.status || null,
    });
