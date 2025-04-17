import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import apiClient from '../services/api';

const typeOptions = [
  'T1', 'T2', 'T3', 'T4', 'T5', 'Studio', 'Duplex', 'Loft', 'Autre'
];

const layoutOptions = [
  'Classique', 'Traversant', 'Duplex', 'Rez-de-jardin', 'Dernier étage', 'Autre'
];

export default function ApartmentCreatePage() {
  const navigate = useNavigate();
  const { buildingId } = useParams();
  const [form, setForm] = useState({
    type_logement: '',
    layout: '',
    floor: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = e => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await apiClient.post('/apartments/', {
        ...form,
        floor: form.floor ? parseInt(form.floor, 10) : null,
        building_id: parseInt(buildingId, 10),
      });
      navigate(`/buildings/${buildingId}`);
    } catch (err) {
      setError(
        err.response?.data?.detail
        || (err.response?.data && JSON.stringify(err.response.data))
        || err.message
        || "Erreur lors de la création de l'appartement."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto mt-10 bg-white p-8 rounded shadow">
      <h2 className="text-2xl font-bold mb-6">Créer un appartement</h2>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block mb-1 font-medium">Type de logement</label>
          <select
            name="type_logement"
            value={form.type_logement}
            onChange={handleChange}
            required
            className="w-full border rounded px-3 py-2"
          >
            <option value="">Sélectionner</option>
            {typeOptions.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
        <div className="mb-4">
          <label className="block mb-1 font-medium">Disposition</label>
          <select
            name="layout"
            value={form.layout}
            onChange={handleChange}
            required
            className="w-full border rounded px-3 py-2"
          >
            <option value="">Sélectionner</option>
            {layoutOptions.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
        <div className="mb-4">
          <label className="block mb-1 font-medium">Étage (optionnel)</label>
          <input
            type="number"
            name="floor"
            value={form.floor}
            onChange={handleChange}
            className="w-full border rounded px-3 py-2"
            placeholder="Numéro d'étage"
            min="0"
          />
        </div>
        {error && <div className="mb-4 text-red-600">{error}</div>}
        <button
          type="submit"
          className="bg-blue-600 text-white px-6 py-2 rounded font-bold hover:bg-blue-700"
          disabled={loading}
        >
          {loading ? 'Création...' : 'Créer'}
        </button>
        <button
          type="button"
          className="ml-4 px-6 py-2 rounded border border-gray-400 hover:bg-gray-100"
          onClick={() => navigate(`/buildings/${buildingId}`)}
          disabled={loading}
        >
          Annuler
        </button>
      </form>
    </div>
  );
}
