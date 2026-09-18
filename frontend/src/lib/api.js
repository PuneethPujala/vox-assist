import axios from 'axios';
import { auth } from '../firebase';

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 75000, // 75s timeout to handle Render free-tier cold starts
});

// Safely get Firebase ID token without risking deadlock
const safeGetIdToken = async (user, timeoutMs = 6000) => {
    return Promise.race([
        user.getIdToken(),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Auth token timeout')), timeoutMs))
    ]);
};

api.interceptors.request.use(async (config) => {
    try {
        const user = auth.currentUser;
        if (user && !config.headers.Authorization) {
            const token = await safeGetIdToken(user);
            config.headers.Authorization = `Bearer ${token}`;
        }
    } catch (err) {
        console.warn('Could not attach auth token to request:', err);
    }
    return config;
});

// Response interceptor to format cold-start / timeout errors
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.code === 'ECONNABORTED' || error.message?.toLowerCase().includes('timeout')) {
            error.friendlyMessage = 'Server response timed out. The backend might still be waking up from cold sleep. Please retry.';
        } else if (error.response?.status >= 500) {
            error.friendlyMessage = 'Server is currently waking up or temporarily unavailable. Please retry in a moment.';
        } else if (error.message === 'Network Error') {
            error.friendlyMessage = 'Network connection issue. The backend service may be spinning up from sleep.';
        }
        return Promise.reject(error);
    }
);

export default api;
