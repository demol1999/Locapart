import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import BuildingInfoCard from '../components/BuildingInfoCard';
import ApartmentCard from '../components/ApartmentCard';
import AddApartmentCard from '../components/AddApartmentCard';
import CoproSummary from '../components/CoproSummary';

export default function BuildingPage() {
  const { buildingId } = useParams();
  const navigate = useNavigate();

  const [building, setBuilding] = useState(null);
  const [apartments, setApartments] = useState([]);

  useEffect(() => {
    // Utilise apiClient pour la bonne baseURL et le token automatique
    import('../services/api').then(({ default: apiClient }) => {
      apiClient.get(`/buildings/${buildingId}`)
        .then(res => setBuilding(res.data))
        .catch(() => setBuilding(null));
      apiClient.get(`/buildings/${buildingId}/apartments`)
        .then(res => setApartments(res.data))
        .catch(() => setApartments([]));
    });
  }, [buildingId]);

  const handleEdit = () => {
    navigate(`/buildings/${buildingId}/edit`);
  };

  const handleApartmentClick = (apartmentId) => {
    navigate(`/apartments/${apartmentId}`);
  };

  const handleCreateApartment = () => {
    navigate(`/buildings/${buildingId}/apartments/new`);
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 32 }}>
      <button
        onClick={() => navigate('/buildings')}
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
        ← Retour à la liste des immeubles
      </button>
      <BuildingInfoCard building={building} onEdit={handleEdit} />

      {/* Encart Copropriété */}
      {building && building.copro_id ? (
        <CoproSummary coproId={building.copro_id} navigate={navigate} />
      ) : (
        <div style={{marginBottom:32}}>
          <button
            style={{background:'#1976d2',color:'white',padding:'8px 18px',border:'none',borderRadius:4,cursor:'pointer',fontWeight:'bold'}}
            onClick={() => navigate(`/copros/new?buildingId=${buildingId}`)}
          >
            + Associer une copropriété
          </button>
        </div>
      )}

      <h3>Appartements</h3>
      <div
        className="apartment-mosaic"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 24,
        }}
      >
        {apartments.map(apartment => (
          <ApartmentCard
            key={apartment.id}
            apartment={apartment}
            onClick={() => handleApartmentClick(apartment.id)}
          />
        ))}
        <AddApartmentCard onClick={handleCreateApartment} />
      </div>
    </div>
  );
}
