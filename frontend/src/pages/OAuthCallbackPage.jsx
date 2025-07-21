import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import apiClient from '../services/api';

const OAuthCallbackPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { oauthLogin } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        const code = searchParams.get('code');
        const provider = window.location.pathname.split('/')[2]; // Extraire le provider de l'URL
        
        if (!code) {
          throw new Error('Code d\'autorisation manquant');
        }

        console.log(`[OAuth Callback] Processing ${provider} callback with code:`, code);

        // Appeler notre endpoint de callback backend
        const response = await apiClient.get(`/auth/${provider}/callback`, {
          params: { code }
        });

        const { access_token, refresh_token, user } = response.data;
        
        // Utiliser la fonction oauthLogin du contexte
        await oauthLogin({ access_token, refresh_token }, user);
        
        console.log(`[OAuth Callback] ${provider} login successful`);
        
        // Rediriger vers la page des immeubles
        navigate('/buildings');
        
      } catch (error) {
        console.error('[OAuth Callback] Error:', error);
        setError(error.response?.data?.detail || error.message || 'Erreur lors de l\'authentification OAuth');
        setLoading(false);
      }
    };

    handleOAuthCallback();
  }, [searchParams, navigate, oauthLogin]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
            Connexion en cours...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md dark:bg-gray-800">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
              <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.502 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="mt-2 text-lg font-medium text-gray-900 dark:text-white">
              Erreur d'authentification
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {error}
            </p>
            <div className="mt-6">
              <button
                onClick={() => navigate('/login')}
                className="w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Retour à la connexion
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default OAuthCallbackPage;