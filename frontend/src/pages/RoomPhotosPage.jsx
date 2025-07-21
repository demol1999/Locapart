import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const RoomPhotosPage = () => {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const fileInputRef = useRef(null);
  
  const [room, setRoom] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [showUploadForm, setShowUploadForm] = useState(false);
  
  // Formulaire d'upload
  const [uploadData, setUploadData] = useState({
    title: '',
    description: '',
    is_main: false
  });

  useEffect(() => {
    fetchData();
  }, [roomId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [roomRes, photosRes] = await Promise.all([
        api.get(`/rooms/rooms/${roomId}`),
        api.get(`/photos/rooms/${roomId}?include_url=true`)
      ]);
      
      setRoom(roomRes.data);
      setPhotos(photosRes.data.photos || []);
    } catch (error) {
      console.error('Erreur lors du chargement:', error);
      setError('Erreur lors du chargement des données');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      handleUpload(files[0]);
    }
  };

  const handleUpload = async (file) => {
    if (!file) return;

    // Validation côté client
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      setError('Format de fichier non supporté. Utilisez JPEG, PNG ou WebP.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB
      setError('Le fichier est trop volumineux (maximum 10MB).');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', 'room');
      formData.append('room_id', roomId);
      
      if (uploadData.title) {
        formData.append('title', uploadData.title);
      }
      if (uploadData.description) {
        formData.append('description', uploadData.description);
      }
      formData.append('is_main', uploadData.is_main);

      await api.post('/photos/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Réinitialiser le formulaire
      setUploadData({
        title: '',
        description: '',
        is_main: false
      });
      setShowUploadForm(false);
      
      // Recharger les photos
      fetchData();
      
    } catch (error) {
      console.error('Erreur lors de l\'upload:', error);
      setError(error.response?.data?.detail || 'Erreur lors de l\'upload');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeletePhoto = async (photoId) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer cette photo ?')) {
      return;
    }

    try {
      await api.delete(`/photos/${photoId}`);
      fetchData();
    } catch (error) {
      console.error('Erreur lors de la suppression:', error);
      setError('Erreur lors de la suppression de la photo');
    }
  };

  const handleSetMainPhoto = async (photoId) => {
    try {
      await api.put(`/photos/${photoId}`, {
        is_main: true
      });
      fetchData();
    } catch (error) {
      console.error('Erreur lors de la définition de la photo principale:', error);
      setError('Erreur lors de la définition de la photo principale');
    }
  };

  const openModal = (photo) => {
    setSelectedPhoto(photo);
  };

  const closeModal = () => {
    setSelectedPhoto(null);
  };

  const getRoomTypeLabel = (type) => {
    const labels = {
      kitchen: 'Cuisine',
      bedroom: 'Chambre',
      living_room: 'Salon',
      bathroom: 'Salle de bain',
      office: 'Bureau',
      storage: 'Rangement',
      balcony: 'Balcon/Terrasse',
      dining_room: 'Salle à manger',
      entrance: 'Entrée/Hall',
      toilet: 'WC',
      laundry: 'Buanderie',
      cellar: 'Cave',
      garage: 'Garage',
      other: 'Autre'
    };
    return labels[type] || type;
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
                Photos de la pièce
              </h1>
              {room && (
                <p className="mt-2 text-gray-600">
                  {room.name} - {getRoomTypeLabel(room.room_type)}
                  {room.area_m2 && ` - ${room.area_m2} m²`}
                </p>
              )}
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => navigate(`/apartments/${room?.apartment_id}/rooms`)}
                className="bg-gray-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
              >
                Retour aux pièces
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Actions d'upload */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">
              Ajouter des photos ({photos.length})
            </h2>
            <button
              onClick={() => setShowUploadForm(!showUploadForm)}
              className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              {showUploadForm ? 'Annuler' : '+ Ajouter une photo'}
            </button>
          </div>

          {showUploadForm && (
            <div className="border-t pt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Titre de la photo
                  </label>
                  <input
                    type="text"
                    value={uploadData.title}
                    onChange={(e) => setUploadData({...uploadData, title: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Ex: Vue d'ensemble, Coin cuisine..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={uploadData.description}
                    onChange={(e) => setUploadData({...uploadData, description: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Description détaillée..."
                  />
                </div>
              </div>

              <div className="flex items-center mb-4">
                <input
                  type="checkbox"
                  id="is_main"
                  checked={uploadData.is_main}
                  onChange={(e) => setUploadData({...uploadData, is_main: e.target.checked})}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <label htmlFor="is_main" className="ml-2 block text-sm text-gray-900">
                  Définir comme photo principale de la pièce
                </label>
              </div>

              <div className="flex items-center space-x-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/jpg,image/png,image/webp"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="bg-green-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  {uploading ? 'Upload en cours...' : 'Choisir un fichier'}
                </button>
                <span className="text-sm text-gray-500">
                  Formats acceptés: JPEG, PNG, WebP (max 10MB)
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Galerie de photos */}
        {photos.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {photos.map((photo) => (
              <div key={photo.id} className="bg-white shadow rounded-lg overflow-hidden">
                <div className="relative">
                  <img
                    src={photo.url}
                    alt={photo.title || photo.filename}
                    className="w-full h-48 object-cover cursor-pointer hover:opacity-90 transition-opacity"
                    onClick={() => openModal(photo)}
                  />
                  {photo.is_main && (
                    <div className="absolute top-2 right-2 bg-yellow-500 text-white text-xs px-2 py-1 rounded">
                      Principale
                    </div>
                  )}
                </div>

                <div className="p-4">
                  <h3 className="font-medium text-gray-900 mb-1">
                    {photo.title || 'Sans titre'}
                  </h3>
                  {photo.description && (
                    <p className="text-sm text-gray-600 mb-2">{photo.description}</p>
                  )}
                  
                  <div className="text-xs text-gray-500 mb-3">
                    {photo.width} × {photo.height}px
                    {photo.file_size && ` • ${Math.round(photo.file_size / 1024)}KB`}
                  </div>

                  <div className="flex space-x-2">
                    {!photo.is_main && (
                      <button
                        onClick={() => handleSetMainPhoto(photo.id)}
                        className="flex-1 bg-yellow-600 text-white py-1 px-2 rounded text-xs hover:bg-yellow-700 transition-colors"
                      >
                        Principale
                      </button>
                    )}
                    <button
                      onClick={() => handleDeletePhoto(photo.id)}
                      className="bg-red-600 text-white py-1 px-2 rounded text-xs hover:bg-red-700 transition-colors"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-white shadow rounded-lg">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Aucune photo</h3>
            <p className="text-gray-600 mb-4">Ajoutez des photos pour documenter cette pièce.</p>
            <button
              onClick={() => setShowUploadForm(true)}
              className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              Ajouter la première photo
            </button>
          </div>
        )}

        {/* Modal de visualisation */}
        {selectedPhoto && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50" onClick={closeModal}>
            <div className="max-w-4xl max-h-full p-4" onClick={e => e.stopPropagation()}>
              <div className="bg-white rounded-lg overflow-hidden">
                <div className="flex items-center justify-between p-4 border-b">
                  <h3 className="text-lg font-medium">
                    {selectedPhoto.title || selectedPhoto.filename}
                  </h3>
                  <button
                    onClick={closeModal}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    ✕
                  </button>
                </div>
                
                <img
                  src={selectedPhoto.url.replace('/medium/', '/large/')}
                  alt={selectedPhoto.title || selectedPhoto.filename}
                  className="max-w-full max-h-96 object-contain mx-auto"
                />
                
                {selectedPhoto.description && (
                  <div className="p-4 border-t bg-gray-50">
                    <p className="text-gray-700">{selectedPhoto.description}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RoomPhotosPage;