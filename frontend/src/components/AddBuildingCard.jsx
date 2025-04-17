import React from 'react';

export default function AddBuildingCard({ onClick }) {
  return (
    <div
      className="add-building-card"
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
        minWidth: 220,
        minHeight: 120,
        color: '#1976d2',
        fontWeight: 'bold',
        fontSize: 22,
        transition: 'background 0.2s',
      }}
      onClick={onClick}
    >
      <span style={{ fontSize: 40, marginBottom: 8 }}>+</span>
      <span>Ajouter un immeuble</span>
    </div>
  );
}
