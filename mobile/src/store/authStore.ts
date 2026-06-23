import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { login as apiLogin, register as apiRegister } from '../api/client';

interface AuthState {
  user: { username: string; role: string } | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  restore: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (username, password) => {
    const { data } = await apiLogin(username, password);
    await AsyncStorage.setItem('access_token', data.access_token);
    await AsyncStorage.setItem('refresh_token', data.refresh_token);
    set({ user: { username: data.username, role: data.role }, isAuthenticated: true });
  },

  register: async (username, password) => {
    await apiRegister(username, password);
  },

  logout: async () => {
    await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
    set({ user: null, isAuthenticated: false });
  },

  restore: async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (token) {
        set({ isAuthenticated: true });
      }
    } finally {
      set({ isLoading: false });
    }
  },
}));
