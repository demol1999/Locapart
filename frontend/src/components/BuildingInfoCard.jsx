import React from 'react';

export default function BuildingInfoCard({ building, onEdit }) {
  if (!building) return null;

  return (
    <div className="building-info-card" style={{
      border: '1px solid #ddd', borderRadius: 8, padding: 24, marginBottom: 32, position: 'relative', background: '#fff'
    }}>
      <button
        style={{
          position: 'absolute', top: 16, right: 16, padding: '8px 16px', borderRadius: 4, background: '#1976d2', color: 'white', border: 'none', cursor: 'pointer'
        }}
        onClick={onEdit}
      >
        Modifier
      </button>
      <h2>{building.name}</h2>
      <div>
        <strong>Adresse :</strong> {building.street_number} {building.street_name}, {building.complement ? building.complement + ', ' : ''}{building.postal_code} {building.city}, {building.country}
      </div>
      <div>
        <strong>Nombre d'étages :</strong> {building.floors}
      </div>
      <div>
        <strong>Copropriété :</strong> {building.is_copro ? 'Oui' : 'Non'}
      </div>
    </div>
  );
}
