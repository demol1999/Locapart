import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';

const BuildingDetails = () => {
  const { id } = useParams(); // id du bâtiment, ou "new"
  const isNew = id === 'new';
  const [building, setBuilding] = useState({
    name: '',
    street_number: '',
    street_name: '',
    complement: '',
    postal_code: '',
    city: '',
    country: '',
    floors: '',
    is_copro: false
  });
  const navigate = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    if (!isNew) {
      axios.get(`${import.meta.env.VITE_API_URL}/buildings/${id}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        }
      })
      .then(res => setBuilding(res.data))
      .catch(err => console.error(err));
    }
  }, [id, isNew]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setBuilding(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    const method = isNew ? axios.post : axios.put;
    const url = isNew
      ? `${import.meta.env.VITE_API_URL}/buildings/`
      : `${import.meta.env.VITE_API_URL}/buildings/${id}`;

    method(url, building, {
      headers: {
        Authorization: `Bearer ${token}`,
      }
    })
    .then(() => navigate('/'))
    .catch(err => console.error(err));
  };

  const handleDelete = () => {
    axios.delete(`${import.meta.env.VITE_API_URL}/buildings/${id}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      }
    })
    .then(() => navigate('/'))
    .catch(err => console.error(err));
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">
        {isNew ? t('create_building') : t('edit_building')}
      </h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input type="text" name="name" value={building.name} onChange={handleChange} placeholder="Nom" className="w-full p-2 border" />
        <input type="text" name="street_number" value={building.street_number} onChange={handleChange} placeholder="N°" className="w-full p-2 border" />
        <input type="text" name="street_name" value={building.street_name} onChange={handleChange} placeholder="Rue" className="w-full p-2 border" />
        <input type="text" name="complement" value={building.complement} onChange={handleChange} placeholder="Complément" className="w-full p-2 border" />
        <input type="text" name="postal_code" value={building.postal_code} onChange={handleChange} placeholder="Code postal" className="w-full p-2 border" />
        <input type="text" name="city" value={building.city} onChange={handleChange} placeholder="Ville" className="w-full p-2 border" />
        <input type="text" name="country" value={building.country} onChange={handleChange} placeholder="Pays" className="w-full p-2 border" />
        <input type="number" name="floors" value={building.floors} onChange={handleChange} placeholder="Nombre d'étages" className="w-full p-2 border" />
        <label className="flex items-center">
          <input type="checkbox" name="is_copro" checked={building.is_copro} onChange={handleChange} className="mr-2" />
          {t('copro')}
        </label>

        <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded">
          {isNew ? t('create') : t('save')}
        </button>

        {!isNew && (
          <button type="button" onClick={handleDelete} className="ml-4 bg-red-600 text-white px-4 py-2 rounded">
            {t('delete')}
          </button>
        )}
      </form>
    </div>
  );
};

export default BuildingDetails;
