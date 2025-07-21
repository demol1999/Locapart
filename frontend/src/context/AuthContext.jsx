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
      const { access_token, refresh_token } = response.data;
      console.log('[login] Tokens reçus');
      
      // Gestion du stockage selon rememberMe
      if (credentials.rememberMe) {
        // Connexion persistante : localStorage + cookie pour refresh token
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('refresh_token');
        
        const isSecure = window.location.protocol === 'https:';
        document.cookie = `refresh_token=${refresh_token}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Strict${isSecure ? '; Secure' : ''}`;
        console.log('[login] Tokens stockés en persistant');
      } else {
        // Session temporaire : sessionStorage seulement
        sessionStorage.setItem('access_token', access_token);
        sessionStorage.setItem('refresh_token', refresh_token);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        document.cookie = 'refresh_token=; path=/; max-age=0; SameSite=Strict';
        console.log('[login] Tokens stockés en session');
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

  // Fonction utilitaire pour nettoyer tous les tokens
  const clearAllTokens = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    document.cookie = 'refresh_token=; path=/; max-age=0; SameSite=Strict';
  }, []);

  const logout = useCallback(() => {
    clearAllTokens();
    setUser(null);
  }, [clearAllTokens]);

  const checkAuth = useCallback(async () => {
    try {
      const response = await apiClient.get('/me');
      setUser(response.data);
      return true;
    } catch (error) {
      clearAllTokens();
      setUser(null);
      return false;
    }
  }, [clearAllTokens]);

  // Fonction pour rafraîchir l'access token
  const refreshToken = useCallback(async () => {
    try {
      let refresh = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
      if (!refresh) {
        // Essayer de récupérer depuis le cookie
        const match = document.cookie.match(/(?:^|; )refresh_token=([^;]+)/);
        if (!match) {
          throw new Error('Aucun refresh token trouvé');
        }
        refresh = match[1];
      }

      const params = new URLSearchParams();
      params.append('refresh_token', refresh);
      
      const response = await apiClient.post('/refresh/', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      const { access_token } = response.data;
      
      // Mettre à jour le token d'accès dans le même storage qu'avant
      if (localStorage.getItem('refresh_token')) {
        localStorage.setItem('access_token', access_token);
      } else {
        sessionStorage.setItem('access_token', access_token);
      }

      console.log('[refresh] Access token mis à jour');
      return access_token;
    } catch (error) {
      console.error('[refresh] Erreur de rafraîchissement:', error);
      clearAllTokens();
      setUser(null);
      throw error;
    }
  }, [clearAllTokens]);

  // Au démarrage, cherche le token dans localStorage puis sessionStorage
  // Si aucun, tente de le récupérer depuis le cookie (auto-login)
  React.useEffect(() => {
    let storedToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    if (!storedToken) {
      // Cherche dans les cookies
      const match = document.cookie.match(/(?:^|; )access_token=([^;]+)/);
      if (match) {
        storedToken = match[1];
        // On restaure dans le localStorage pour la session courante
        localStorage.setItem('access_token', storedToken);
      }
    }
    if (storedToken) {
      fetchUser().then(user => {
        if (!user) {
          // Token invalide : nettoyage complet
          clearAllTokens();
          setUser(null);
        }
      });
    }
  }, [fetchUser, clearAllTokens]);

  const oauthLogin = useCallback(async (tokens, userData) => {
    const { access_token, refresh_token } = tokens;
    
    // Stocker les tokens en persistant pour OAuth
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    
    const isSecure = window.location.protocol === 'https:';
    document.cookie = `refresh_token=${refresh_token}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Strict${isSecure ? '; Secure' : ''}`;
    
    setUser(userData);
    console.log('[oauthLogin] Connexion OAuth réussie');
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, checkAuth, oauthLogin }}>
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
