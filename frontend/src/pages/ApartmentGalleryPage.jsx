import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const ApartmentGalleryPage = () => {
  const { apartmentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [apartment, setApartment] = useState(null);
  const [gallery, setGallery] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [allPhotos, setAllPhotos] = useState([]);

  useEffect(() => {
    fetchData();
  }, [apartmentId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [apartmentRes, galleryRes] = await Promise.all([
        api.get(`/apartments/${apartmentId}`),
        api.get(`/photos/apartments/${apartmentId}/gallery?include_url=true&size=medium`)
      ]);
      
      setApartment(apartmentRes.data);
      setGallery(galleryRes.data);
      
      // Créer une liste de toutes les photos pour la navigation
      const photos = [];
      
      // Ajouter les photos d'appartement
      galleryRes.data.apartment.photos.forEach(photo => {
        photos.push({...photo, context: 'Appartement'});
      });
      
      // Ajouter les photos de chaque pièce
      galleryRes.data.rooms.forEach(roomData => {
        roomData.photos.forEach(photo => {
          photos.push({...photo, context: roomData.room.name});
        });
      });
      
      setAllPhotos(photos);
      
    } catch (error) {
      console.error('Erreur lors du chargement:', error);
      setError('Erreur lors du chargement de la galerie');
    } finally {
      setLoading(false);
    }
  };

  const openModal = (photo, context) => {
    const photoIndex = allPhotos.findIndex(p => p.id === photo.id);
    setCurrentPhotoIndex(photoIndex);
    setSelectedPhoto({...photo, context});
  };

  const closeModal = () => {
    setSelectedPhoto(null);
  };

  const navigatePhoto = (direction) => {
    const newIndex = direction === 'next' 
      ? (currentPhotoIndex + 1) % allPhotos.length
      : (currentPhotoIndex - 1 + allPhotos.length) % allPhotos.length;
    
    setCurrentPhotoIndex(newIndex);
    setSelectedPhoto(allPhotos[newIndex]);
  };

  const getTotalPhotos = () => {
    if (!gallery) return 0;
    
    return gallery.apartment.total + 
           gallery.rooms.reduce((sum, room) => sum + room.total, 0);
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
          <p className="mt-4 text-gray-600">Chargement de la galerie...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* En-tête */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Galerie photos
              </h1>
              {apartment && (
                <p className="mt-2 text-gray-600">
                  {apartment.type_logement} - {apartment.layout} • {getTotalPhotos()} photos
                </p>
              )}
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => navigate(`/apartments/${apartmentId}/rooms`)}
                className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
              >
                Gérer les pièces
              </button>
              <button
                onClick={() => navigate(`/apartments/${apartmentId}`)}
                className="bg-gray-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
              >
                Retour à l'appartement
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {gallery && (
          <div className="space-y-8">
            {/* Photos de l'appartement */}
            {gallery.apartment.photos.length > 0 && (
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900">
                    Photos générales de l'appartement ({gallery.apartment.total})
                  </h2>
                  {gallery.apartment.has_main && (
                    <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full">
                      Photo principale définie
                    </span>
                  )}
                </div>
                
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  {gallery.apartment.photos.map((photo) => (
                    <div key={photo.id} className="relative group">
                      <img
                        src={photo.url}
                        alt={photo.title || photo.filename}
                        className="w-full h-24 object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                        onClick={() => openModal(photo, 'Appartement')}
                      />
                      {photo.is_main && (
                        <div className="absolute top-1 right-1 bg-yellow-500 text-white text-xs px-1 py-0.5 rounded">
                          ★
                        </div>
                      )}
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-opacity rounded-lg"></div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Photos par pièce */}
            {gallery.rooms.map((roomData) => (
              roomData.photos.length > 0 && (
                <div key={roomData.room.id} className="bg-white shadow rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {roomData.room.name} - {getRoomTypeLabel(roomData.room.room_type)}
                      </h2>
                      <p className="text-sm text-gray-600">
                        {roomData.total} photo{roomData.total > 1 ? 's' : ''}
                        {roomData.has_main && ' • Photo principale définie'}
                      </p>
                    </div>
                    <button
                      onClick={() => navigate(`/rooms/${roomData.room.id}/photos`)}
                      className="bg-green-600 text-white py-1 px-3 rounded text-sm hover:bg-green-700 transition-colors"
                    >
                      Gérer
                    </button>
                  </div>
                  
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    {roomData.photos.map((photo) => (
                      <div key={photo.id} className="relative group">
                        <img
                          src={photo.url}
                          alt={photo.title || photo.filename}
                          className="w-full h-24 object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                          onClick={() => openModal(photo, roomData.room.name)}
                        />
                        {photo.is_main && (
                          <div className="absolute top-1 right-1 bg-yellow-500 text-white text-xs px-1 py-0.5 rounded">
                            ★
                          </div>
                        )}
                        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-opacity rounded-lg"></div>
                        {photo.title && (
                          <div className="absolute bottom-1 left-1 right-1 bg-black bg-opacity-70 text-white text-xs p-1 rounded truncate opacity-0 group-hover:opacity-100 transition-opacity">
                            {photo.title}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
            ))}

            {/* Message si aucune photo */}
            {getTotalPhotos() === 0 && (
              <div className="text-center py-12 bg-white shadow rounded-lg">
                <div className="text-gray-400 mb-4">
                  <svg className="mx-auto h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Aucune photo dans cet appartement</h3>
                <p className="text-gray-600 mb-4">
                  Commencez par définir les pièces, puis ajoutez des photos pour chaque pièce.
                </p>
                <div className="flex justify-center space-x-4">
                  <button
                    onClick={() => navigate(`/apartments/${apartmentId}/rooms`)}
                    className="bg-indigo-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
                  >
                    Gérer les pièces
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Modal de visualisation avec navigation */}
        {selectedPhoto && (
          <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
            <div className="max-w-6xl max-h-full p-4 w-full">
              <div className="relative">
                {/* Barre de navigation supérieure */}
                <div className="flex items-center justify-between mb-4 text-white">
                  <div>
                    <h3 className="text-lg font-medium">
                      {selectedPhoto.title || selectedPhoto.filename}
                    </h3>
                    <p className="text-sm text-gray-300">
                      {selectedPhoto.context} • {currentPhotoIndex + 1} / {allPhotos.length}
                    </p>
                  </div>
                  <button
                    onClick={closeModal}
                    className="text-white hover:text-gray-300 text-2xl"
                  >
                    ✕
                  </button>
                </div>

                {/* Image principale */}
                <div className="relative">
                  <img
                    src={selectedPhoto.url.replace('/medium/', '/large/')}
                    alt={selectedPhoto.title || selectedPhoto.filename}
                    className="max-w-full max-h-[70vh] object-contain mx-auto rounded-lg"
                  />

                  {/* Boutons de navigation */}
                  {allPhotos.length > 1 && (
                    <>
                      <button
                        onClick={() => navigatePhoto('prev')}
                        className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 text-white p-2 rounded-full hover:bg-opacity-70 transition-opacity"
                      >
                        ←
                      </button>
                      <button
                        onClick={() => navigatePhoto('next')}
                        className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 text-white p-2 rounded-full hover:bg-opacity-70 transition-opacity"
                      >
                        →
                      </button>
                    </>
                  )}
                </div>

                {/* Informations de la photo */}
                {selectedPhoto.description && (
                  <div className="mt-4 bg-black bg-opacity-50 text-white p-4 rounded-lg">
                    <p>{selectedPhoto.description}</p>
                  </div>
                )}

                {/* Miniatures de navigation */}
                {allPhotos.length > 1 && (
                  <div className="mt-4 flex justify-center space-x-2 overflow-x-auto pb-2">
                    {allPhotos.map((photo, index) => (
                      <img
                        key={photo.id}
                        src={photo.url.replace('/medium/', '/thumbnail/')}
                        alt=""
                        className={`w-12 h-12 object-cover rounded cursor-pointer transition-opacity ${
                          index === currentPhotoIndex ? 'opacity-100 ring-2 ring-white' : 'opacity-60 hover:opacity-80'
                        }`}
                        onClick={() => {
                          setCurrentPhotoIndex(index);
                          setSelectedPhoto(photo);
                        }}
                      />
                    ))}
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

export default ApartmentGalleryPage;