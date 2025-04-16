// src/services/api.js
import axios from 'axios';

// Récupère l'URL de base de l'API depuis les variables d'environnement Vite
// IMPORTANT : Assure-toi de créer un fichier .env à la racine de ton projet
// et d'y définir VITE_API_BASE_URL=http://localhost:8000 (ou l'URL où tourne ton backend)
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'; // Fallback au cas où

// Crée une instance d'axios avec la configuration de base
const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// (Optionnel mais recommandé) Intercepteur pour ajouter le token JWT aux requêtes
apiClient.interceptors.request.use(
  (config) => {
    // Récupère le token depuis le localStorage (ou là où tu le stockeras)
    const token = localStorage.getItem('authToken');
    if (token) {
      // Ajoute l'en-tête Authorization si un token existe
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // Gère les erreurs de requête
    return Promise.reject(error);
  }
);

export default apiClient;