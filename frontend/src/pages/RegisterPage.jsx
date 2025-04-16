// src/pages/RegisterPage.jsx
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../services/api'; // Importe l'instance axios configurée

function RegisterPage() {
  // Hooks pour traduction et navigation
  const { t } = useTranslation();
  const navigate = useNavigate();

  // États pour les champs, chargement, erreurs et succès
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState(''); // Ajout du nom complet
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false); // État pour le message de succès

  // Gestionnaire de soumission du formulaire
  const handleRegister = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false); // Réinitialise le succès

    // Prépare les données pour l'API (endpoint /register attend du JSON)
    const userData = {
      email: email,
      password: password,
      full_name: fullName, // Assure-toi que la clé correspond au schéma Pydantic UserCreate
    };

    try {
      // Appel à l'API d'inscription
      // L'endpoint /register renvoie généralement l'utilisateur créé (statut 200 ou 201)
      await apiClient.post('/register', userData);

      // En cas de succès :
      setSuccess(true); // Affiche le message de succès
      // Optionnel: rediriger vers la page de connexion après un délai
      setTimeout(() => {
        navigate('/login');
      }, 3000); // Redirige après 3 secondes

    } catch (err) {
      // En cas d'erreur :
      console.error("Erreur d'inscription:", err);
      if (err.response && err.response.data && err.response.data.detail) {
        // Gère les erreurs spécifiques (ex: email déjà utilisé)
        setError(typeof err.response.data.detail === 'string'
          ? err.response.data.detail
          : JSON.stringify(err.response.data.detail)); // Affiche les détails si complexe
      } else {
        setError(t('registerPage.error.generic')); // Message générique
      }
    } finally {
      setLoading(false); // Arrête le chargement
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
          {t('registerPage.title')} {/* Traduction */}
        </h2>

        {/* Affiche un message de succès après l'inscription */}
        {success && (
          <div className="p-4 text-sm text-green-700 bg-green-100 rounded-md dark:bg-green-900 dark:text-green-200">
            {t('registerPage.successMessage')} {/* Traduction */}
          </div>
        )}

        {/* Affiche le formulaire seulement si l'inscription n'est pas réussie */}
        {!success && (
          <form className="space-y-6" onSubmit={handleRegister}>
            {/* Champ Nom Complet */}
            <div>
              <label
                htmlFor="fullName"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {t('registerPage.fullNameLabel')} {/* Traduction */}
              </label>
              <input
                id="fullName"
                name="fullName"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="block w-full px-3 py-2 mt-1 text-gray-900 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-indigo-500 dark:focus:border-indigo-500"
                placeholder={t('registerPage.fullNamePlaceholder')}
              />
            </div>

            {/* Champ Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {t('registerPage.emailLabel')} {/* Traduction */}
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
                placeholder={t('registerPage.emailPlaceholder')}
              />
            </div>

            {/* Champ Mot de passe */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {t('registerPage.passwordLabel')} {/* Traduction */}
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password" // Important pour ne pas pré-remplir avec un mdp existant
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
                 {typeof error === 'string' ? t(error, { defaultValue: error }) : t('registerPage.error.generic')}
              </p>
            )}

            {/* Bouton de soumission */}
            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-800"
              >
                {loading ? t('registerPage.loadingButton') : t('registerPage.submitButton')} {/* Traduction */}
              </button>
            </div>
          </form>
        )} {/* Fin du formulaire conditionnel */}

        {/* Lien vers la page de connexion */}
        <p className="mt-4 text-sm text-center text-gray-600 dark:text-gray-400">
          {t('registerPage.alreadyAccount')}{' '}
          <Link
            to="/login"
            className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            {t('registerPage.loginLink')} {/* Traduction */}
          </Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;