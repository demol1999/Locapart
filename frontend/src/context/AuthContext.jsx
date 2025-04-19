import React, { createContext, useContext, useState, useCallback } from 'react';
import apiClient from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchUser = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
      console.log('[fetchUser] Token utilisé pour /me:', token);
      const response = await apiClient.get('/me');
      console.log('[fetchUser] Réponse /me:', response.status, response.data);
      setUser(response.data);
      return response.data;
    } catch (error) {
      console.error('[fetchUser] Erreur /me:', error);
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
      console.log('[login] Token reçu:', access_token);
      // Gestion du stockage du token selon rememberMe
      if (credentials.rememberMe) {
        localStorage.setItem('access_token', access_token);
        sessionStorage.removeItem('access_token');
        // Stocke aussi dans un cookie persistant (30 jours)
        document.cookie = `access_token=${access_token}; path=/; max-age=${60 * 60 * 24 * 30}`;
        console.log('[login] Token stocké dans localStorage et cookie');
      } else {
        sessionStorage.setItem('access_token', access_token);
        localStorage.removeItem('access_token');
        // Supprime le cookie si présent
        document.cookie = 'access_token=; path=/; max-age=0';
        console.log('[login] Token stocké dans sessionStorage');
      }

      await fetchUser();
      return true;
    } catch (error) {
      console.error('[login] Erreur de connexion:', error);
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
      localStorage.removeItem('access_token');
      sessionStorage.removeItem('access_token');
      setUser(null);
      return false;
    }
  }, []);

  // Au démarrage, cherche le token dans localStorage puis sessionStorage
  // Si aucun, tente de le récupérer depuis le cookie (auto-login)
  React.useEffect(() => {
    let storedToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    if (!storedToken) {
      // Cherche dans les cookies
      const match = document.cookie.match(/(?:^|; )access_token=([^;]+)/);
      if (match) {
        storedToken = match[1];
        localStorage.setItem('access_token', storedToken); // On restaure dans le localStorage
      }
    }
    if (storedToken) {
      // Ajoute le token à l'apiClient si besoin
      if (apiClient && apiClient.defaults) {
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
      }
      fetchUser().then(user => {
        if (!user) {
          // Token invalide : déconnexion stricte
          localStorage.removeItem('access_token');
          sessionStorage.removeItem('access_token');
          document.cookie = 'access_token=; path=/; max-age=0';
          setUser(null);
        }
      });
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
