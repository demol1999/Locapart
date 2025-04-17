import React from 'react';

export default function ApartmentCard({ apartment, onClick }) {
  return (
    <div
      className="apartment-card"
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
      <div style={{ fontWeight: 'bold', fontSize: 18 }}>{apartment.nom || apartment.name}</div>
      <div style={{ color: '#555', marginTop: 8 }}>{apartment.type_logement || apartment.type}</div>
    </div>
  );
}
