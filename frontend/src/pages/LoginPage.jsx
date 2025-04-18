// src/pages/LoginPage.jsx
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../services/api'; // Importe l'instance axios configurée

function LoginPage() {
  // Hook pour la traduction
  const { t } = useTranslation();
  // Hook pour la navigation programmatique
  const navigate = useNavigate();

  // États pour les champs du formulaire, le chargement et les erreurs
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Gestionnaire de soumission du formulaire
  const handleLogin = async (event) => {
    event.preventDefault(); // Empêche le rechargement de la page
    setLoading(true); // Active l'indicateur de chargement
    setError(null); // Réinitialise les erreurs précédentes

    try {
      // Prépare les données pour l'API (FastAPI attend souvent du 'x-www-form-urlencoded' pour le login OAuth2)
      // Vérifie ton endpoint /login dans FastAPI. S'il attend du JSON, utilise { email, password } directement.
      // Si c'est bien OAuth2PasswordRequestForm, il faut form-data.
      const formData = new FormData();
      formData.append('username', email); // FastAPI OAuth2 utilise 'username' par défaut
      formData.append('password', password);

      // Appel à l'API de connexion via axios
      const response = await apiClient.post('/login', formData, {
         // Important: Spécifier le Content-Type pour FormData si nécessaire par FastAPI OAuth2
         headers: {
           'Content-Type': 'application/x-www-form-urlencoded',
         },
       });


      // En cas de succès :
      const { access_token } = response.data; // Récupère le token JWT
      // Stocke le token (localStorage est simple mais a des implications de sécurité - XSS)
      // Pour une meilleure sécurité, envisage des cookies HttpOnly côté backend.
      localStorage.setItem('authToken', access_token);

      // Redirige l'utilisateur vers le tableau de bord (ou autre page protégée)
      navigate('/dashboard'); // Assure-toi que cette route existe ou adapte la destination

    } catch (err) {
      // En cas d'erreur :
      console.error("Erreur de connexion:", err);
      // Essaye d'afficher un message d'erreur pertinent de l'API, sinon un message générique
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError(t('loginPage.error.generic')); // Message d'erreur générique traduit
      }
    } finally {
      // Dans tous les cas (succès ou échec), désactive le chargement
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
          {t('loginPage.title')} {/* Clé de traduction pour le titre */}
        </h2>
        <form className="space-y-6" onSubmit={handleLogin}>
          {/* Champ Email */}
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              {t('loginPage.emailLabel')} {/* Traduction */}
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="block w-full px-3 py-2 mt-1 text-gray-900 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-indigo-500 dark:focus:border-indigo-500"
              placeholder={t('loginPage.emailPlaceholder')}
            />
          </div>

          {/* Champ Mot de passe */}
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              {t('loginPage.passwordLabel')} {/* Traduction */}
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="block w-full px-3 py-2 mt-1 text-gray-900 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-indigo-500 dark:focus:border-indigo-500"
              placeholder="••••••••"
            />
          </div>

          {/* Affichage des erreurs */}
          {error && (
            <p className="text-sm text-center text-red-600 dark:text-red-400">
              {/* Essaye de traduire l'erreur si possible, sinon affiche telle quelle */}
              {typeof error === 'string' ? t(error, { defaultValue: error }) : t('loginPage.error.generic')}
            </p>
          )}

          {/* Bouton de soumission */}
          <div>
            <button
              type="submit"
              disabled={loading} // Désactive le bouton pendant le chargement
              className="w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-800"
            >
              {loading ? t('loginPage.loadingButton') : t('loginPage.submitButton')} {/* Traduction */}
            </button>
          </div>
        </form>

        {/* Lien vers la page d'inscription */}
        <p className="mt-4 text-sm text-center text-gray-600 dark:text-gray-400">
          {t('loginPage.noAccount')}{' '}
          <Link
            to="/register"
            className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            {t('loginPage.registerLink')} {/* Traduction */}
          </Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;