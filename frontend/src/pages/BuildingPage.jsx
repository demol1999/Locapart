import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import BuildingInfoCard from '../components/BuildingInfoCard';
import ApartmentCard from '../components/ApartmentCard';

export default function BuildingPage() {
  const { buildingId } = useParams();
  const navigate = useNavigate();

  const [building, setBuilding] = useState(null);
  const [apartments, setApartments] = useState([]);

  useEffect(() => {
    fetch(`/api/buildings/${buildingId}`)
      .then(res => res.json())
      .then(data => setBuilding(data));

    fetch(`/api/buildings/${buildingId}/apartments`)
      .then(res => res.json())
      .then(data => setApartments(data));
  }, [buildingId]);

  const handleEdit = () => {
    navigate(`/buildings/${buildingId}/edit`);
  };

  const handleApartmentClick = (apartmentId) => {
    navigate(`/apartments/${apartmentId}`);
  };

  const handleCreateApartment = () => {
    navigate(`/buildings/${buildingId}/apartments/create`);
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
        <div
          style={{
            border: '2px dashed #bbb',
            borderRadius: 8,
            padding: 20,
            background: '#f5f5f5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            minHeight: 120,
            minWidth: 180,
            fontWeight: 'bold',
            color: '#1976d2',
            fontSize: 18,
          }}
          onClick={handleCreateApartment}
        >
          + Créer un appartement
        </div>
      </div>
    </div>
  );
}
