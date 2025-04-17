import React, { createContext, useContext, useState, useCallback } from 'react';
import apiClient, { setAuthToken, clearAuthToken } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchUser = useCallback(async () => {
    try {
      const response = await apiClient.get('/me');
      setUser(response.data);
      return response.data;
    } catch (error) {
      setUser(null);
      return null;
    }
  }, []);

  const login = useCallback(async (credentials) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('username', credentials.email);
      params.append('password', credentials.password);
      const response = await apiClient.post('/login/', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      const { access_token } = response.data;
      // Gestion du stockage du token selon rememberMe
      if (credentials.rememberMe) {
        localStorage.setItem('access_token', access_token);
        sessionStorage.removeItem('access_token');
      } else {
        sessionStorage.setItem('access_token', access_token);
        localStorage.removeItem('access_token');
      }
      setAuthToken(access_token);
      await fetchUser();
      return true;
    } catch (error) {
      console.error('Erreur de connexion:', error);
      setUser(null);
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchUser]);

  const logout = useCallback(() => {
    clearAuthToken();
    localStorage.removeItem('access_token');
    sessionStorage.removeItem('access_token');
    setUser(null);
  }, []);

  const checkAuth = useCallback(async () => {
    try {
      const response = await apiClient.get('/me');
      setUser(response.data);
      return true;
    } catch (error) {
      clearAuthToken();
      setUser(null);
      return false;
    }
  }, []);

  // Au démarrage, cherche le token dans localStorage puis sessionStorage
  React.useEffect(() => {
    const storedToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    if (storedToken) {
      setAuthToken(storedToken);
      fetchUser();
    }
  }, [fetchUser]);

  return (
    <AuthContext.Provider value={{ user, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth doit être utilisé à l intérieur d un AuthProvider');
  }
  return context;
};
