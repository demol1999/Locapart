import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';

const ProfilePage = () => {
  const { t } = useTranslation();
  const { user, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: user?.phone || ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      await updateUser(formData);
      setSuccess(t('profilePage.updateSuccess'));
      setIsEditing(false);
    } catch (err) {
      setError(t('profilePage.updateError'));
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          {t('profilePage.title')}
        </h1>

        <div className="space-y-6">
          {/* Informations personnelles */}
          <section>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4">
              {t('profilePage.personalInfo')}
            </h2>

            {!isEditing ? (
              // Mode affichage
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-600 dark:text-gray-400">
                    {t('profilePage.nameLabel')}
                  </label>
                  <p className="mt-1 text-gray-900 dark:text-white">{user?.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600 dark:text-gray-400">
                    {t('profilePage.emailLabel')}
                  </label>
                  <p className="mt-1 text-gray-900 dark:text-white">{user?.email}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600 dark:text-gray-400">
                    {t('profilePage.phoneLabel')}
                  </label>
                  <p className="mt-1 text-gray-900 dark:text-white">{user?.phone || '-'}</p>
                </div>
                <button
                  onClick={() => setIsEditing(true)}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  {t('profilePage.editButton')}
                </button>
              </div>
            ) : (
              // Mode édition
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-600 dark:text-gray-400">
                    {t('profilePage.nameLabel')}
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    className="mt-1 block w-full rounded border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600 dark:text-gray-400">
                    {t('profilePage.emailLabel')}
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className="mt-1 block w-full rounded border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600 dark:text-gray-400">
                    {t('profilePage.phoneLabel')}
                  </label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    className="mt-1 block w-full rounded border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                {error && (
                  <div className="text-red-600 dark:text-red-400 text-sm mt-2">
                    {error}
                  </div>
                )}

                {success && (
                  <div className="text-green-600 dark:text-green-400 text-sm mt-2">
                    {success}
                  </div>
                )}

                <div className="flex space-x-4">
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                  >
                    {t('profilePage.saveButton')}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditing(false);
                      setFormData({
                        name: user?.name || '',
                        email: user?.email || '',
                        phone: user?.phone || ''
                      });
                    }}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-white rounded hover:bg-gray-300 dark:hover:bg-gray-700 transition-colors"
                  >
                    {t('profilePage.cancelButton')}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
