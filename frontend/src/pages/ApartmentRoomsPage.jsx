import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const ApartmentRoomsPage = () => {
  const { apartmentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [apartment, setApartment] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [roomTypes, setRoomTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingRoom, setEditingRoom] = useState(null);
  
  // Formulaire de création/édition
  const [formData, setFormData] = useState({
    name: '',
    room_type: '',
    area_m2: '',
    description: '',
    floor_level: 0
  });

  useEffect(() => {
    fetchData();
  }, [apartmentId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [apartmentRes, roomsRes, typesRes] = await Promise.all([
        api.get(`/apartments/${apartmentId}`),
        api.get(`/rooms/apartments/${apartmentId}/rooms`),
        api.get('/rooms/room-types')
      ]);
      
      setApartment(apartmentRes.data);
      setRooms(roomsRes.data);
      setRoomTypes(typesRes.data.room_types);
    } catch (error) {
      console.error('Erreur lors du chargement:', error);
      setError('Erreur lors du chargement des données');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    
    try {
      const roomData = {
        ...formData,
        apartment_id: parseInt(apartmentId),
        area_m2: formData.area_m2 ? parseFloat(formData.area_m2) : null
      };

      await api.post(`/rooms/apartments/${apartmentId}/rooms`, roomData);
      
      setShowCreateForm(false);
      resetForm();
      fetchData();
    } catch (error) {
      console.error('Erreur lors de la création:', error);
      setError('Erreur lors de la création de la pièce');
    }
  };

  const handleUpdateRoom = async (e) => {
    e.preventDefault();
    
    try {
      const updateData = {
        ...formData,
        area_m2: formData.area_m2 ? parseFloat(formData.area_m2) : null
      };

      await api.put(`/rooms/rooms/${editingRoom.id}`, updateData);
      
      setEditingRoom(null);
      resetForm();
      fetchData();
    } catch (error) {
      console.error('Erreur lors de la mise à jour:', error);
      setError('Erreur lors de la mise à jour de la pièce');
    }
  };

  const handleDeleteRoom = async (room) => {
    if (!window.confirm(`Êtes-vous sûr de vouloir supprimer la pièce "${room.name}" ?`)) {
      return;
    }

    try {
      await api.delete(`/rooms/rooms/${room.id}`);
      fetchData();
    } catch (error) {
      console.error('Erreur lors de la suppression:', error);
      if (error.response?.data?.detail?.includes('photo')) {
        setError('Impossible de supprimer la pièce : des photos sont associées. Supprimez d\'abord les photos.');
      } else {
        setError('Erreur lors de la suppression de la pièce');
      }
    }
  };

  const handleCreateFromTemplate = async (template) => {
    if (rooms.length > 0) {
      if (!window.confirm('Créer des pièces depuis un template supprimera les pièces existantes. Continuer ?')) {
        return;
      }
    }

    try {
      await api.post(`/rooms/apartments/${apartmentId}/rooms/templates/${template}`);
      fetchData();
    } catch (error) {
      console.error('Erreur lors de la création depuis template:', error);
      setError(`Erreur lors de la création depuis le template ${template}`);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      room_type: '',
      area_m2: '',
      description: '',
      floor_level: 0
    });
  };

  const startEdit = (room) => {
    setEditingRoom(room);
    setFormData({
      name: room.name,
      room_type: room.room_type,
      area_m2: room.area_m2 || '',
      description: room.description || '',
      floor_level: room.floor_level
    });
    setShowCreateForm(false);
  };

  const getRoomTypeLabel = (type) => {
    const roomType = roomTypes.find(rt => rt.value === type);
    return roomType ? roomType.label : type;
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

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* En-tête */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Gestion des pièces
              </h1>
              {apartment && (
                <p className="mt-2 text-gray-600">
                  Appartement: {apartment.type_logement} - {apartment.layout}
                </p>
              )}
            </div>
            <button
              onClick={() => navigate(`/apartments/${apartmentId}`)}
              className="bg-gray-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
            >
              Retour à l'appartement
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Templates rapides */}
        {rooms.length === 0 && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Créer des pièces rapidement
            </h2>
            <p className="text-gray-600 mb-4">
              Utilisez un template pour créer automatiquement les pièces selon le type d'appartement :
            </p>
            <div className="flex flex-wrap gap-2">
              {['T1', 'T2', 'T3', 'T4', 'T5'].map(template => (
                <button
                  key={template}
                  onClick={() => handleCreateFromTemplate(template)}
                  className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
                >
                  Template {template}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-gray-900">
            Pièces ({rooms.length})
          </h2>
          <button
            onClick={() => {
              setShowCreateForm(true);
              setEditingRoom(null);
              resetForm();
            }}
            className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            + Ajouter une pièce
          </button>
        </div>

        {/* Formulaire de création/édition */}
        {(showCreateForm || editingRoom) && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              {editingRoom ? 'Modifier la pièce' : 'Nouvelle pièce'}
            </h3>
            
            <form onSubmit={editingRoom ? handleUpdateRoom : handleCreateRoom}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nom de la pièce *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Ex: Salon, Chambre 1..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Type de pièce *
                  </label>
                  <select
                    required
                    value={formData.room_type}
                    onChange={(e) => setFormData({...formData, room_type: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Sélectionner un type</option>
                    {roomTypes.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Surface (m²)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.area_m2}
                    onChange={(e) => setFormData({...formData, area_m2: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Ex: 25.50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Étage
                  </label>
                  <input
                    type="number"
                    min="-5"
                    max="50"
                    value={formData.floor_level}
                    onChange={(e) => setFormData({...formData, floor_level: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Description de la pièce..."
                />
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false);
                    setEditingRoom(null);
                    resetForm();
                  }}
                  className="bg-gray-300 text-gray-700 py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-400 transition-colors"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
                >
                  {editingRoom ? 'Mettre à jour' : 'Créer'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Liste des pièces */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {rooms.map((room, index) => (
            <div key={room.id} className="bg-white shadow rounded-lg p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{room.name}</h3>
                  <p className="text-sm text-gray-600">{getRoomTypeLabel(room.room_type)}</p>
                </div>
                <span className="bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded-full">
                  #{index + 1}
                </span>
              </div>

              <div className="space-y-2 text-sm text-gray-600 mb-4">
                {room.area_m2 && (
                  <p><strong>Surface:</strong> {room.area_m2} m²</p>
                )}
                <p><strong>Étage:</strong> {room.floor_level}</p>
                {room.description && (
                  <p><strong>Description:</strong> {room.description}</p>
                )}
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={() => navigate(`/rooms/${room.id}/photos`)}
                  className="flex-1 bg-green-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-green-700 transition-colors"
                >
                  📸 Photos
                </button>
                <button
                  onClick={() => navigate(`/floor-plan-editor?type=room&roomId=${room.id}&apartmentId=${apartmentId}`)}
                  className="flex-1 bg-yellow-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-yellow-700 transition-colors"
                >
                  📐 Plan
                </button>
                <button
                  onClick={() => startEdit(room)}
                  className="flex-1 bg-indigo-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
                >
                  ✏️ Modifier
                </button>
                <button
                  onClick={() => handleDeleteRoom(room)}
                  className="bg-red-600 text-white py-2 px-3 rounded-md text-sm font-medium hover:bg-red-700 transition-colors"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>

        {rooms.length === 0 && !showCreateForm && (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m2 0h3M9 7h6m-6 4h6m-6 4h6" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Aucune pièce définie</h3>
            <p className="text-gray-600 mb-4">Commencez par ajouter des pièces à cet appartement.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ApartmentRoomsPage;