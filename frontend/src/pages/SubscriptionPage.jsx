import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const SubscriptionPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [subscription, setSubscription] = useState(null);
  const [apartmentLimit, setApartmentLimit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchSubscriptionData();
  }, []);

  const fetchSubscriptionData = async () => {
    try {
      const [subResponse, limitResponse] = await Promise.all([
        api.get('/stripe/subscription'),
        api.get('/stripe/apartment-limit')
      ]);
      
      setSubscription(subResponse.data);
      setApartmentLimit(limitResponse.data);
    } catch (error) {
      console.error('Erreur lors du chargement:', error);
      setError('Erreur lors du chargement des données');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async () => {
    setUpgrading(true);
    setError('');

    try {
      const response = await api.post('/stripe/create-checkout-session', {
        subscription_type: 'PREMIUM',
        success_url: `${window.location.origin}/subscription?success=true`,
        cancel_url: `${window.location.origin}/subscription?cancelled=true`
      });

      // Rediriger vers Stripe Checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      console.error('Erreur lors de la création de la session:', error);
      setError('Erreur lors de la création de la session de paiement');
      setUpgrading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm('Êtes-vous sûr de vouloir annuler votre abonnement ?')) {
      return;
    }

    try {
      await api.post('/stripe/cancel-subscription');
      setError('');
      fetchSubscriptionData(); // Recharger les données
      alert('Abonnement annulé avec succès');
    } catch (error) {
      console.error('Erreur lors de l\'annulation:', error);
      setError('Erreur lors de l\'annulation de l\'abonnement');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Chargement...</p>
        </div>
      </div>
    );
  }

  const isPremium = subscription?.subscription_type === 'PREMIUM';
  const isActive = subscription?.status === 'ACTIVE';

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-gray-900">Mon Abonnement</h1>
          <p className="mt-4 text-lg text-gray-600">
            Gérez votre abonnement et consultez vos limites
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Informations de l'abonnement actuel */}
        <div className="bg-white shadow-lg rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Abonnement Actuel</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center mb-4">
                <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                  isPremium 
                    ? 'bg-purple-100 text-purple-800' 
                    : 'bg-green-100 text-green-800'
                }`}>
                  {isPremium ? 'Premium' : 'Gratuit'}
                </div>
                <div className={`ml-3 px-2 py-1 rounded-full text-xs ${
                  isActive 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {isActive ? 'Actif' : 'Inactif'}
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <p><strong>Type:</strong> {subscription?.subscription_type}</p>
                <p><strong>Statut:</strong> {subscription?.status}</p>
                {subscription?.current_period_end && (
                  <p><strong>Renouvellement:</strong> {new Date(subscription.current_period_end).toLocaleDateString()}</p>
                )}
              </div>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-2">Limites d'appartements</h3>
              {apartmentLimit && (
                <div className="space-y-2 text-sm">
                  <p><strong>Appartements actuels:</strong> {apartmentLimit.current_count}</p>
                  <p><strong>Limite:</strong> {apartmentLimit.limit === -1 ? 'Illimité' : apartmentLimit.limit}</p>
                  <div className={`px-2 py-1 rounded text-xs ${
                    apartmentLimit.can_add 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {apartmentLimit.can_add ? 'Peut ajouter des appartements' : 'Limite atteinte'}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Plans d'abonnement */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          {/* Plan Gratuit */}
          <div className={`bg-white rounded-lg shadow-lg p-6 ${!isPremium ? 'ring-2 ring-green-500' : ''}`}>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900">Plan Gratuit</h3>
              <div className="mt-4 flex items-baseline justify-center">
                <span className="text-4xl font-bold text-gray-900">0€</span>
                <span className="text-sm font-medium text-gray-500 ml-1">/mois</span>
              </div>
            </div>
            
            <ul className="mt-6 space-y-4">
              <li className="flex items-start">
                <svg className="h-5 w-5 text-green-500 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-gray-700">Jusqu'à 3 appartements</span>
              </li>
              <li className="flex items-start">
                <svg className="h-5 w-5 text-green-500 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-gray-700">Fonctionnalités de base</span>
              </li>
            </ul>

            {!isPremium && isActive && (
              <div className="mt-6 text-center">
                <span className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-green-100 text-green-800">
                  Plan actuel
                </span>
              </div>
            )}
          </div>

          {/* Plan Premium */}
          <div className={`bg-white rounded-lg shadow-lg p-6 ${isPremium ? 'ring-2 ring-purple-500' : ''}`}>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900">Plan Premium</h3>
              <div className="mt-4 flex items-baseline justify-center">
                <span className="text-4xl font-bold text-gray-900">9,99€</span>
                <span className="text-sm font-medium text-gray-500 ml-1">/mois</span>
              </div>
            </div>
            
            <ul className="mt-6 space-y-4">
              <li className="flex items-start">
                <svg className="h-5 w-5 text-green-500 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-gray-700">Appartements illimités</span>
              </li>
              <li className="flex items-start">
                <svg className="h-5 w-5 text-green-500 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-gray-700">Toutes les fonctionnalités</span>
              </li>
              <li className="flex items-start">
                <svg className="h-5 w-5 text-green-500 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-gray-700">Support prioritaire</span>
              </li>
            </ul>

            <div className="mt-6">
              {isPremium && isActive ? (
                <div className="text-center">
                  <span className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-purple-100 text-purple-800 mb-3">
                    Plan actuel
                  </span>
                  <button
                    onClick={handleCancelSubscription}
                    className="block w-full bg-red-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-red-700 transition-colors"
                  >
                    Annuler l'abonnement
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleUpgrade}
                  disabled={upgrading}
                  className="w-full bg-purple-600 text-white py-3 px-4 rounded-md text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {upgrading ? 'Redirection...' : 'Passer au Premium'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Boutons de navigation */}
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => navigate('/buildings')}
            className="bg-gray-600 text-white py-2 px-6 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
          >
            Retour aux immeubles
          </button>
          <button
            onClick={() => navigate('/payments')}
            className="bg-indigo-600 text-white py-2 px-6 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Historique des paiements
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionPage;