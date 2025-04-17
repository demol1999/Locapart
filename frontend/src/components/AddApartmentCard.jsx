import React from 'react';

export default function AddApartmentCard({ onClick }) {
  return (
    <div
      className="add-apartment-card"
      style={{
        border: '2px dashed #1976d2',
        borderRadius: 8,
        padding: 20,
        background: '#f5faff',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        minWidth: 180,
        minHeight: 120,
        color: '#1976d2',
        fontWeight: 'bold',
        fontSize: 18,
        transition: 'background 0.2s',
      }}
      onClick={onClick}
    >
      <span style={{ fontSize: 36, marginBottom: 6 }}>+</span>
      <span>Créer un appartement</span>
    </div>
  );
}
