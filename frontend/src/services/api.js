// src/services/api.js
import axios from 'axios';

// Récupère l'URL de base de l'API depuis les variables d'environnement
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Instance d'axios avec la configuration de base
const apiClient = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour ajouter le token JWT aux requêtes
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur pour gérer les erreurs d'authentification et le refresh automatique
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Ne pas essayer de refresh sur les endpoints d'auth
    const authEndpoints = ['/login/', '/signup/', '/refresh/'];
    const isAuthEndpoint = authEndpoints.some(endpoint => originalRequest.url?.includes(endpoint));
    
    if (error.response && error.response.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;
      
      try {
        // Tenter de rafraîchir le token
        const refresh = localStorage.getItem('refresh_token') || 
                       sessionStorage.getItem('refresh_token') ||
                       document.cookie.match(/(?:^|; )refresh_token=([^;]+)/)?.[1];
        
        if (refresh) {
          const params = new URLSearchParams();
          params.append('refresh_token', refresh);
          
          const response = await apiClient.post('/refresh/', params, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
          });
          
          const { access_token } = response.data;
          
          // Mettre à jour le token
          if (localStorage.getItem('refresh_token')) {
            localStorage.setItem('access_token', access_token);
          } else {
            sessionStorage.setItem('access_token', access_token);
          }
          
          // Retry la requête originale avec le nouveau token
          originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        console.error('Erreur de refresh:', refreshError);
      }
      
      // Si le refresh échoue, déconnecter
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      sessionStorage.removeItem('access_token');
      sessionStorage.removeItem('refresh_token');
      document.cookie = 'refresh_token=; path=/; max-age=0; SameSite=Strict';
      
      // Redirection uniquement si on n'est pas déjà sur la page de login
      if (!window.location.pathname.includes('/login')) {
        window.location.replace('/login');
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;