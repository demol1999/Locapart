import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../services/api';

const Toast = ({ message, onClose }) => (
  <div className="fixed top-5 right-5 bg-green-600 text-white px-4 py-2 rounded shadow-lg z-50 animate-fadein">
    {message}
    <button className="ml-4 text-white font-bold" onClick={onClose}>×</button>
  </div>
);

const BuildingCreatePage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [form, setForm] = useState({
    name: '',
    street_number: '',
    street_name: '',
    complement: '',
    postal_code: '',
    city: '',
    country: '',
    floors: '',
    is_copro: false,
  });
  const [photos, setPhotos] = useState([]); // {file, title, description}
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handlePhotoChange = (idx, field, value) => {
    setPhotos((prev) => prev.map((p, i) => i === idx ? { ...p, [field]: value } : p));
  };

  const handlePhotoFile = (idx, file) => {
    setPhotos((prev) => prev.map((p, i) => i === idx ? { ...p, file } : p));
  };

  const addPhotoField = () => {
    setPhotos((prev) => [...prev, { file: null, title: '', description: '' }]);
  };

  const removePhotoField = (idx) => {
    setPhotos((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        ...form,
        floors: Number(form.floors),
      };
      // 1. Créer l'immeuble
      const res = await apiClient.post('/buildings/', payload);
      const buildingId = res.data.id;
      // 2. Uploader les photos si besoin
      for (const photo of photos) {
        if (photo.file) {
          const formData = new FormData();
          formData.append('file', photo.file);
          formData.append('type', 'building');
          formData.append('target_id', buildingId);
          if (photo.title) formData.append('title', photo.title);
          if (photo.description) formData.append('description', photo.description);
          await apiClient.post('/upload-photo/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
        }
      }
      setShowSuccess(true);
      setTimeout(() => {
        setShowSuccess(false);
        navigate('/buildings');
      }, 1500);
    } catch (err) {
      setError(err?.response?.data?.detail || t('buildingForm.error', 'Erreur lors de la création de l\'immeuble'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-lg p-8 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-4">{t('buildingForm.title')}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block font-medium mb-1">{t('buildingForm.name')} *</label>
            <input type="text" name="name" value={form.name} onChange={handleChange} required className="w-full px-3 py-2 border rounded" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-medium mb-1">{t('buildingForm.streetNumber')}</label>
              <input type="text" name="street_number" value={form.street_number} onChange={handleChange} className="w-full px-3 py-2 border rounded" />
            </div>
            <div>
              <label className="block font-medium mb-1">{t('buildingForm.streetName')}</label>
              <input type="text" name="street_name" value={form.street_name} onChange={handleChange} className="w-full px-3 py-2 border rounded" />
            </div>
          </div>
          <div>
            <label className="block font-medium mb-1">{t('buildingForm.complement')}</label>
            <input type="text" name="complement" value={form.complement} onChange={handleChange} className="w-full px-3 py-2 border rounded" />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block font-medium mb-1">{t('buildingForm.postalCode')}</label>
              <input type="text" name="postal_code" value={form.postal_code} onChange={handleChange} className="w-full px-3 py-2 border rounded" />
            </div>
            <div>
              <label className="block font-medium mb-1">{t('buildingForm.city')}</label>
              <input type="text" name="city" value={form.city} onChange={handleChange} className="w-full px-3 py-2 border rounded" />
            </div>
            <div>
              <label className="block font-medium mb-1">{t('buildingForm.country')}</label>
              <input type="text" name="country" value={form.country} onChange={handleChange} className="w-full px-3 py-2 border rounded" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-medium mb-1">{t('buildingForm.floors')} *</label>
              <input type="number" name="floors" value={form.floors} onChange={handleChange} min="1" required className="w-full px-3 py-2 border rounded" />
            </div>
            <div className="flex items-center mt-6">
              <input type="checkbox" name="is_copro" checked={form.is_copro} onChange={handleChange} id="is_copro" className="mr-2" />
              <label htmlFor="is_copro">{t('buildingForm.isCopro')}</label>
            </div>
          </div>

          {/* Photos upload */}
          <div>
            <label className="block font-medium mb-2">{t('buildingForm.addPhoto')}</label>
            {photos.map((photo, idx) => (
              <div key={idx} className="mb-4 border p-2 rounded bg-gray-50">
                <input
                  type="file"
                  accept="image/*"
                  onChange={e => handlePhotoFile(idx, e.target.files[0])}
                  className="mb-2"
                />
                <input
                  type="text"
                  placeholder={t('buildingForm.photoTitle')}
                  value={photo.title}
                  onChange={e => handlePhotoChange(idx, 'title', e.target.value)}
                  className="w-full px-3 py-2 border rounded mb-1"
                />
                <input
                  type="text"
                  placeholder={t('buildingForm.photoDescription')}
                  value={photo.description}
                  onChange={e => handlePhotoChange(idx, 'description', e.target.value)}
                  className="w-full px-3 py-2 border rounded"
                />
                <button type="button" onClick={() => removePhotoField(idx)} className="text-red-600 mt-1">Supprimer</button>
              </div>
            ))}
            <button type="button" onClick={addPhotoField} className="bg-gray-200 px-3 py-1 rounded">{t('buildingForm.addPhoto')}</button>
          </div>

          {error && <div className="text-red-500 text-sm">{error}</div>}
          <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            {loading ? t('buildingForm.creating') : t('buildingForm.create')}
          </button>
        </form>
        {showSuccess && <Toast message={t('buildingForm.success')} onClose={() => setShowSuccess(false)} />}
      </div>
    </div>
  );
};

export default BuildingCreatePage;
