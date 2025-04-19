import React from 'react';

export default function BuildingCard({ building, onClick }) {
  return (
    <div
      className="building-card"
      style={{
        border: '1px solid #eee',
        borderRadius: 8,
        padding: 20,
        background: '#fafbfc',
        cursor: 'pointer',
        minWidth: 180,
        minHeight: 120,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        transition: 'box-shadow 0.2s',
      }}
      onClick={onClick}
    >
      <div style={{ fontWeight: 'bold', fontSize: 20, marginBottom: 6, textAlign: 'center' }}>{building.name}</div>
      <div style={{ color: '#555', fontSize: 15, textAlign: 'center' }}>{building.street_number} {building.street_name}, {building.city}</div>
      <div style={{ color: '#888', fontSize: 13, marginTop: 8, textAlign: 'center' }}>
        {building.floors} étage{building.floors > 1 ? 's' : ''} • Copropriété : {building.is_copro ? 'Oui' : 'Non'}
      </div>
    </div>
  );
}
