import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const PaymentHistoryPage = () => {
  const navigate = useNavigate();
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    status: '',
    start_date: '',
    end_date: '',
    limit: 50,
    offset: 0
  });

  useEffect(() => {
    fetchPayments();
  }, [filters]);

  const fetchPayments = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          params.append(key, value);
        }
      });

      const response = await api.get(`/stripe/payments?${params.toString()}`);
      setPayments(response.data);
    } catch (error) {
      console.error('Erreur lors du chargement des paiements:', error);
      setError('Erreur lors du chargement de l\'historique des paiements');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      SUCCEEDED: { bg: 'bg-green-100', text: 'text-green-800', label: 'Réussi' },
      PENDING: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'En attente' },
      FAILED: { bg: 'bg-red-100', text: 'text-red-800', label: 'Échoué' },
      CANCELLED: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Annulé' },
      REFUNDED: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Remboursé' }
    };

    const config = statusConfig[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status };

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatAmount = (amount, currency = 'EUR') => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: currency
    }).format(amount);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      offset: 0 // Reset offset when filters change
    }));
  };

  if (loading && payments.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Chargement des paiements...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Historique des Paiements</h1>
          <p className="mt-2 text-gray-600">Consultez l'historique de vos paiements et factures</p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Filtres */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Filtres</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Statut
              </label>
              <select
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Tous les statuts</option>
                <option value="SUCCEEDED">Réussi</option>
                <option value="PENDING">En attente</option>
                <option value="FAILED">Échoué</option>
                <option value="CANCELLED">Annulé</option>
                <option value="REFUNDED">Remboursé</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date de début
              </label>
              <input
                type="date"
                value={filters.start_date}
                onChange={(e) => handleFilterChange('start_date', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date de fin
              </label>
              <input
                type="date"
                value={filters.end_date}
                onChange={(e) => handleFilterChange('end_date', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={() => setFilters({
                  status: '',
                  start_date: '',
                  end_date: '',
                  limit: 50,
                  offset: 0
                })}
                className="w-full bg-gray-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
              >
                Réinitialiser
              </button>
            </div>
          </div>
        </div>

        {/* Liste des paiements */}
        <div className="bg-white shadow rounded-lg overflow-hidden">
          {payments.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-gray-400 mb-4">
                <svg className="mx-auto h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Aucun paiement trouvé</h3>
              <p className="text-gray-600">Vous n'avez pas encore effectué de paiements ou aucun paiement ne correspond aux filtres sélectionnés.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Montant
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Statut
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {payments.map((payment) => (
                    <tr key={payment.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(payment.created_at)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        <div>
                          <div className="font-medium">{payment.description || 'Paiement'}</div>
                          {payment.failure_reason && (
                            <div className="text-red-600 text-xs mt-1">{payment.failure_reason}</div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {formatAmount(payment.amount, payment.currency)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(payment.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {payment.receipt_url && payment.status === 'SUCCEEDED' && (
                          <a
                            href={payment.receipt_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-600 hover:text-indigo-900 text-sm font-medium"
                          >
                            Voir le reçu
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="mt-8 flex justify-between items-center">
          <button
            onClick={() => navigate('/subscription')}
            className="bg-gray-600 text-white py-2 px-6 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
          >
            Retour à l'abonnement
          </button>

          {payments.length === filters.limit && (
            <button
              onClick={() => setFilters(prev => ({ ...prev, offset: prev.offset + prev.limit }))}
              disabled={loading}
              className="bg-indigo-600 text-white py-2 px-6 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Chargement...' : 'Charger plus'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default PaymentHistoryPage;