import axios from 'axios';
import { auth } from '../firebase';

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const api = axios.create({
    baseURL: API_BASE_URL,
});

api.interceptors.request.use(async (config) => {
    try {
        const user = auth.currentUser;
        if (user && !config.headers.Authorization) {
            const token = await user.getIdToken();
            config.headers.Authorization = `Bearer ${token}`;
        }
    } catch (err) {
        console.warn('Could not attach auth token to request:', err);
    }
    return config;
});

export default api;
