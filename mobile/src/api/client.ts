import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = 'https://your-domain.com';

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// JWT interceptor
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = await AsyncStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_URL}/refresh`, {
            refresh_token: refreshToken,
          });
          await AsyncStorage.setItem('access_token', data.access_token);
          await AsyncStorage.setItem('refresh_token', data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch {
          await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
        }
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const login = (username: string, password: string) =>
  api.post('/login', null, { params: { username, password } });

export const register = (username: string, password: string) =>
  api.post('/register', null, { params: { username, password } });

// Products
export const getProducts = (params?: Record<string, any>) =>
  api.get('/api/products', { params });

export const getProduct = (id: number) =>
  api.get(`/api/products/${id}`);

// Cart
export const getCart = () => api.get('/api/cart');
export const addToCart = (productId: number, quantity = 1) =>
  api.post('/api/cart/add', { product_id: productId, quantity });
export const removeFromCart = (productId: number) =>
  api.delete('/api/cart/remove', { params: { product_id: productId } });

// Orders
export const createOrder = (address: string, promoCode?: string) =>
  api.post('/api/order', { address, promo_code: promoCode });

// Profile
export const getProfile = () => api.get('/api/profile');
export const updateProfile = (data: any) => api.patch('/api/profile', data);

export default api;
