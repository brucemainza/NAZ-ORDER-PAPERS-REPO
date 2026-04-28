var _a;
import axios from "axios";
export const api = axios.create({
    baseURL: (_a = process.env.NEXT_PUBLIC_API_URL) !== null && _a !== void 0 ? _a : "",
    withCredentials: true,
    headers: {
        "Content-Type": "application/json",
    },
});
api.interceptors.request.use((config) => {
    config.withCredentials = true;
    // JWT is stored in an httpOnly cookie, so the browser includes it automatically.
    // TODO: Proxy upstream backend requests through Next.js when the backend is connected.
    return config;
});
api.interceptors.response.use((response) => response, (error) => Promise.reject(error));
