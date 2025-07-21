import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import FloorPlanEditor from '../components/FloorPlanEditor';
import api from '../services/api';

const FloorPlanEditorPage = () => {
  const { planId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  
  // Paramètres d'URL
  const planType = searchParams.get('type') || 'room'; // room ou apartment
  const roomId = searchParams.get('roomId');
  const apartmentId = searchParams.get('apartmentId');
  
  const [planData, setPlanData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [planName, setPlanName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // Informations contextuelles
  const [contextInfo, setContextInfo] = useState(null);

  useEffect(() => {
    loadPlan();
  }, [planId, roomId, apartmentId]);

  const loadPlan = async () => {
    try {
      setLoading(true);
      
      if (planId) {
        // Charger un plan existant
        const response = await api.get(`/floor-plans/${planId}`);
        setPlanData(response.data);
        setPlanName(response.data.name);
      }
      
      // Charger les informations contextuelles
      if (roomId) {
        const roomResponse = await api.get(`/rooms/rooms/${roomId}`);
        setContextInfo({
          type: 'room',
          data: roomResponse.data,
          name: roomResponse.data.name
        });
        if (!planName && !planId) {
          setPlanName(`Plan - ${roomResponse.data.name}`);
        }
      } else if (apartmentId) {
        const apartmentResponse = await api.get(`/apartments/${apartmentId}`);
        setContextInfo({
          type: 'apartment',
          data: apartmentResponse.data,
          name: `${apartmentResponse.data.type_logement} - ${apartmentResponse.data.layout}`
        });
        if (!planName && !planId) {
          setPlanName(`Plan - ${apartmentResponse.data.type_logement}`);
        }
      }
      
    } catch (error) {
      console.error('Erreur lors du chargement:', error);
      setError('Erreur lors du chargement du plan');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (elements) => {
    setSaving(true);
    
    try {
      const saveData = {
        name: planName,
        type: planType,
        room_id: roomId ? parseInt(roomId) : null,
        apartment_id: apartmentId ? parseInt(apartmentId) : null,
        elements: elements, // Les éléments seront convertis en XML côté backend
        scale: 1,
        grid_size: 20
      };

      let response;
      if (planId) {
        response = await api.put(`/floor-plans/${planId}`, saveData);
      } else {
        response = await api.post('/floor-plans', saveData);
      }

      setPlanData(response.data);
      setShowSaveDialog(false);
      
      // Rediriger vers l'URL avec l'ID du plan
      if (!planId) {
        const newUrl = `/floor-plan-editor/${response.data.id}?type=${planType}${roomId ? `&roomId=${roomId}` : ''}${apartmentId ? `&apartmentId=${apartmentId}` : ''}`;
        navigate(newUrl, { replace: true });
      }
      
    } catch (error) {
      console.error('Erreur lors de la sauvegarde:', error);
      setError('Erreur lors de la sauvegarde du plan');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async (format = 'svg') => {
    try {
      if (!planId) {
        setError('Veuillez d\'abord sauvegarder le plan');
        return;
      }

      const response = await api.get(`/floor-plans/${planId}/export/${format}`, {
        responseType: 'blob'
      });

      // Télécharger le fichier
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${planName}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Erreur lors de l\'export:', error);
      setError('Erreur lors de l\'export du plan');
    }
  };

  const getBackUrl = () => {
    if (roomId) {
      return `/apartments/${contextInfo?.data?.apartment_id}/rooms`;
    } else if (apartmentId) {
      return `/apartments/${apartmentId}`;
    }
    return '/buildings';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Chargement de l'éditeur...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* En-tête */}
      <div className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(getBackUrl())}
                className="text-gray-500 hover:text-gray-700"
              >
                ← Retour
              </button>
              
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  Éditeur de plans 2D
                </h1>
                {contextInfo && (
                  <p className="text-sm text-gray-600">
                    {contextInfo.type === 'room' ? 'Pièce' : 'Appartement'}: {contextInfo.name}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {/* Nom du plan */}
              <input
                type="text"
                value={planName}
                onChange={(e) => setPlanName(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded-md text-sm"
                placeholder="Nom du plan"
              />

              {/* Boutons d'action */}
              <button
                onClick={() => setShowSaveDialog(true)}
                disabled={saving}
                className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {saving ? 'Sauvegarde...' : 'Sauvegarder'}
              </button>

              <div className="relative">
                <button
                  onClick={() => handleExport('svg')}
                  className="bg-green-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-green-700 transition-colors"
                >
                  Exporter
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
              <button
                onClick={() => setError('')}
                className="mt-2 text-sm text-red-600 hover:text-red-500"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Éditeur principal */}
      <div className="flex-1">
        <FloorPlanEditor
          planData={planData}
          onSave={handleSave}
          onExport={handleExport}
          width={1200}
          height={800}
        />
      </div>

      {/* Dialog de sauvegarde */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Sauvegarder le plan
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom du plan
                </label>
                <input
                  type="text"
                  value={planName}
                  onChange={(e) => setPlanName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Entrez un nom pour le plan"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Type de plan
                </label>
                <p className="text-sm text-gray-600">
                  {planType === 'room' ? 'Plan de pièce' : 'Plan d\'appartement'}
                </p>
              </div>

              {contextInfo && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Contexte
                  </label>
                  <p className="text-sm text-gray-600">
                    {contextInfo.name}
                  </p>
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="bg-gray-300 text-gray-700 py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-400 transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={() => {
                  // Demander au composant FloorPlanEditor de sauvegarder
                  const editorComponent = document.querySelector('[data-floor-plan-editor]');
                  if (editorComponent && editorComponent.saveElements) {
                    const elements = editorComponent.saveElements();
                    handleSave(elements);
                  } else {
                    handleSave([]);
                  }
                }}
                disabled={!planName.trim() || saving}
                className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {saving ? 'Sauvegarde...' : 'Sauvegarder'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FloorPlanEditorPage;