import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const BACKEND_KEY = import.meta.env.VITE_BACKEND_KEY || '';

const defaultHeaders = {};
if (BACKEND_KEY) {
  defaultHeaders['X-API-Key'] = BACKEND_KEY;
}

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: defaultHeaders,
});

// Add request interceptor for request timing (dev only)
if (import.meta.env.DEV) {
  client.interceptors.request.use((config) => {
    config.metadata = { startTime: Date.now() };
    return config;
  });

  client.interceptors.response.use(
    (response) => {
      const elapsed = Date.now() - (response.config.metadata?.startTime || Date.now());
      console.debug(`[API] ${response.config.method?.toUpperCase()} ${response.config.url} → ${response.status} (${elapsed}ms)`);
      return response;
    },
    (error) => {
      const elapsed = Date.now() - (error.config?.metadata?.startTime || Date.now());
      console.warn(`[API] ${error.config?.method?.toUpperCase()} ${error.config?.url} → ERROR (${elapsed}ms)`, error.message);
      return Promise.reject(error);
    }
  );
}

export default client;
