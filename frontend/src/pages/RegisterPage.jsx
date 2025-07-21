// src/pages/RegisterPage.jsx
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import apiClient from '../services/api';
import RegisterForm from '../components/RegisterForm';
import OAuthLogin from '../components/OAuthLogin';

function RegisterPage() {
  // Hooks pour traduction et navigation
  const { login } = useAuth(); // Pour login auto
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);


  const handleRegister = async (form, localError) => {
    if (localError) {
      setError(localError);
      return;
    }
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      await apiClient.post('/signup/', form);
      // Connexion automatique après inscription
      const loginSuccess = await login({ email: form.email, password: form.password });
      if (loginSuccess) {
        navigate('/');
        return;
      } else {
        setSuccess(true); // Affiche le message de succès si login auto échoue
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(typeof err.response.data.detail === 'string'
          ? err.response.data.detail
          : JSON.stringify(err.response.data.detail));
      } else {
        setError(t('registerPage.error.generic'));
      }
    } finally {
      setLoading(false);
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
          <>
            <RegisterForm onSubmit={handleRegister} loading={loading} error={error && t(error, { defaultValue: error })} />
            
            {/* Composant OAuth pour Google, Facebook et Microsoft */}
            <OAuthLogin />
          </>
        )}

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