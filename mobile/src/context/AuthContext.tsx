import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { api, UserData } from '../api/client';

// SecureStore doesn't work on web, so we use localStorage as fallback
const storage = {
  async getItem(key: string): Promise<string | null> {
    if (Platform.OS === 'web') {
      return localStorage.getItem(key);
    }
    return SecureStore.getItemAsync(key);
  },
  async setItem(key: string, value: string): Promise<void> {
    if (Platform.OS === 'web') {
      localStorage.setItem(key, value);
      return;
    }
    return SecureStore.setItemAsync(key, value);
  },
  async deleteItem(key: string): Promise<void> {
    if (Platform.OS === 'web') {
      localStorage.removeItem(key);
      return;
    }
    return SecureStore.deleteItemAsync(key);
  },
};

interface AuthContextType {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: UserData | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  googleLogin: (idToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'auth_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<UserData | null>(null);

  useEffect(() => {
    loadToken();
  }, []);

  async function loadToken() {
    try {
      const token = await storage.getItem(TOKEN_KEY);
      if (token) {
        api.setToken(token);
        await refreshUser();
        setIsAuthenticated(true);
      }
    } catch (error) {
      console.error('Failed to load token:', error);
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshUser() {
    try {
      const userData = await api.getMe();
      setUser(userData);
    } catch (error) {
      // Token might be invalid
      await logout();
    }
  }

  async function login(email: string, password: string) {
    const response = await api.login(email, password);
    await storage.setItem(TOKEN_KEY, response.access_token);
    api.setToken(response.access_token);
    await refreshUser();
    setIsAuthenticated(true);
  }

  async function register(email: string, password: string) {
    const response = await api.register(email, password);
    await storage.setItem(TOKEN_KEY, response.access_token);
    api.setToken(response.access_token);
    await refreshUser();
    setIsAuthenticated(true);
  }

  async function googleLogin(idToken: string) {
    const response = await api.googleLogin(idToken);
    await storage.setItem(TOKEN_KEY, response.access_token);
    api.setToken(response.access_token);
    await refreshUser();
    setIsAuthenticated(true);
  }

  async function logout() {
    await storage.deleteItem(TOKEN_KEY);
    api.setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  }

  return (
    <AuthContext.Provider
      value={{
        isLoading,
        isAuthenticated,
        user,
        login,
        register,
        googleLogin,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
