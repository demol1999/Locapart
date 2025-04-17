import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

const initialState = {
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  phone: '',
  street_number: '',
  street_name: '',
  complement: '',
  postal_code: '',
  city: '',
  country: '',
};

export default function RegisterForm({ onSubmit, loading, error }) {
  const { t } = useTranslation();
  const [form, setForm] = useState(initialState);
  const [confirmPassword, setConfirmPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (form.password !== confirmPassword) {
      onSubmit(null, t('registerPage.error.passwordMismatch'));
      return;
    }
    onSubmit({ ...form, rememberMe });
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {/* Prénom */}
      <div>
        <label className="block text-sm font-medium" htmlFor="first_name">{t('registerPage.firstNameLabel')}</label>
        <input name="first_name" id="first_name" type="text" required value={form.first_name} onChange={handleChange}
          className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.firstNamePlaceholder')} />
      </div>
      {/* Nom */}
      <div>
        <label className="block text-sm font-medium" htmlFor="last_name">{t('registerPage.lastNameLabel')}</label>
        <input name="last_name" id="last_name" type="text" required value={form.last_name} onChange={handleChange}
          className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.lastNamePlaceholder')} />
      </div>
      {/* Email */}
      <div>
        <label className="block text-sm font-medium" htmlFor="email">{t('registerPage.emailLabel')}</label>
        <input name="email" id="email" type="email" required value={form.email} onChange={handleChange}
          className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.emailPlaceholder')} />
      </div>
      {/* Téléphone */}
      <div>
        <label className="block text-sm font-medium" htmlFor="phone">{t('registerPage.phoneLabel')}</label>
        <input name="phone" id="phone" type="tel" required value={form.phone} onChange={handleChange}
          className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.phonePlaceholder')} />
      </div>
      {/* Adresse (numéro et rue) */}
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-sm font-medium" htmlFor="street_number">{t('registerPage.streetNumberLabel') || 'N°'}</label>
          <input name="street_number" id="street_number" type="text" value={form.street_number} onChange={handleChange}
            className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.streetNumberPlaceholder') || ''} />
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium" htmlFor="street_name">{t('registerPage.streetNameLabel') || 'Rue'}</label>
          <input name="street_name" id="street_name" type="text" value={form.street_name} onChange={handleChange}
            className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.streetNamePlaceholder') || ''} />
        </div>
      </div>
      {/* Complément */}
      <div>
        <label className="block text-sm font-medium" htmlFor="complement">{t('registerPage.complementLabel') || 'Complément'}</label>
        <input name="complement" id="complement" type="text" value={form.complement} onChange={handleChange}
          className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.complementPlaceholder') || ''} />
      </div>
      {/* Code postal, Ville, Pays */}
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-sm font-medium" htmlFor="postal_code">{t('registerPage.postalCodeLabel')}</label>
          <input name="postal_code" id="postal_code" type="text" value={form.postal_code} onChange={handleChange}
            className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.postalCodePlaceholder')} />
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium" htmlFor="city">{t('registerPage.cityLabel')}</label>
          <input name="city" id="city" type="text" value={form.city} onChange={handleChange}
            className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.cityPlaceholder')} />
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium" htmlFor="country">{t('registerPage.countryLabel')}</label>
          <input name="country" id="country" type="text" value={form.country} onChange={handleChange}
            className="w-full px-3 py-2 border rounded" placeholder={t('registerPage.countryPlaceholder')} />
        </div>
      </div>
      {/* Mot de passe */}
      <div>
        <label className="block text-sm font-medium" htmlFor="password">{t('registerPage.passwordLabel')}</label>
        <input name="password" id="password" type="password" required value={form.password} onChange={handleChange}
          className="w-full px-3 py-2 border rounded" placeholder="••••••••" />
      </div>
      {/* Confirmation mot de passe */}
      <div>
        <label className="block text-sm font-medium" htmlFor="passwordConfirm">{t('registerPage.passwordConfirmLabel')}</label>
        <input name="passwordConfirm" id="passwordConfirm" type="password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
          className="w-full px-3 py-2 border rounded" placeholder="••••••••" />
      </div>
      {error && <p className="text-sm text-red-600 text-center">{error}</p>}
      <div className="flex items-center">
        <input
          id="rememberMe"
          name="rememberMe"
          type="checkbox"
          checked={rememberMe}
          onChange={e => setRememberMe(e.target.checked)}
          className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
        />
        <label htmlFor="rememberMe" className="ml-2 block text-sm text-gray-900 dark:text-gray-300">
          {t('registerPage.rememberMe')}
        </label>
      </div>
      <button type="submit" disabled={loading} className="w-full px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">
        {loading ? t('registerPage.loadingButton') : t('registerPage.submitButton')}
      </button>
    </form>
  );
}
