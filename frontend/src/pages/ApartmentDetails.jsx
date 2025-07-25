import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import BuildingInfoCard from '../components/BuildingInfoCard';

export default function ApartmentDetails() {
  const { apartmentId } = useParams();
  const navigate = useNavigate();
  const [apartment, setApartment] = useState(null);
  const [building, setBuilding] = useState(null);

  useEffect(() => {
    import('../services/api').then(({ default: apiClient }) => {
      apiClient.get(`/apartments/${apartmentId}`)
        .then(res => {
          setApartment(res.data);
          // Ensuite, fetch le bâtiment parent
          if (res.data && res.data.building_id) {
            apiClient.get(`/buildings/${res.data.building_id}`)
              .then(res2 => setBuilding(res2.data))
              .catch(() => setBuilding(null));
          }
        })
        .catch(() => setApartment(null));
    });
  }, [apartmentId]);

  if (!apartment) {
    return <div style={{ padding: 32 }}>Chargement des données de l'appartement...</div>;
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 32 }}>
      <button
        onClick={() => building && navigate(`/buildings/${building.id}`)}
        style={{
          marginBottom: 24,
          background: '#eee',
          border: 'none',
          borderRadius: 4,
          padding: '8px 18px',
          cursor: 'pointer',
          fontWeight: 'bold',
        }}
      >
        ← Retour à l'immeuble
      </button>
      <BuildingInfoCard building={building} onEdit={() => building && navigate(`/buildings/${building.id}/edit`)} />
      
      <div style={{ display: 'flex', gap: '12px', margin: '20px 0' }}>
        <button
          onClick={() => navigate(`/apartments/${apartmentId}/rooms`)}
          style={{
            background: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            padding: '10px 16px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          🚪 Gérer les pièces
        </button>
        <button
          onClick={() => navigate(`/apartments/${apartmentId}/gallery`)}
          style={{
            background: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            padding: '10px 16px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          📸 Galerie photos
        </button>
        <button
          onClick={() => navigate(`/floor-plan-editor?type=apartment&apartmentId=${apartmentId}`)}
          style={{
            background: '#ffc107',
            color: 'black',
            border: 'none',
            borderRadius: 4,
            padding: '10px 16px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          📐 Créer un plan
        </button>
      </div>
      
      <h2>Détail de l'appartement 🏠</h2>
      {/* Ici tu pourras ajouter l'affichage détaillé de l'appartement */}
      <pre style={{ background: '#f7f7f7', padding: 16, borderRadius: 8 }}>
        {JSON.stringify(apartment, null, 2)}
      </pre>
    </div>
  );
}
