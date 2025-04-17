import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import BuildingInfoCard from '../components/BuildingInfoCard';
import ApartmentCard from '../components/ApartmentCard';
import AddApartmentCard from '../components/AddApartmentCard';

export default function BuildingPage() {
  const { buildingId } = useParams();
  const navigate = useNavigate();

  const [building, setBuilding] = useState(null);
  const [apartments, setApartments] = useState([]);

  useEffect(() => {
    fetch(`/api/buildings/${buildingId}`)
      .then(res => res.json())
      .then(data => setBuilding(data));

    const token =
      localStorage.getItem('access_token') ||
      sessionStorage.getItem('access_token');

    fetch(`http://localhost:8000/buildings/${buildingId}/apartments`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(async res => {
        const text = await res.text();
        try {
          return JSON.parse(text);
        } catch {
          throw new Error("Réponse inattendue du serveur : " + text.slice(0, 100));
        }
      })
      .then(data => setApartments(data))
      .catch(err => {
        setApartments([]);
        if (err.message.startsWith("Réponse inattendue du serveur")) {
          console.error("Réponse brute du serveur (copie/colle ce bloc pour le support) :", err.message);
        }
        alert(err.message);
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
