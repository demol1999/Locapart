import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import useFormValidation from '../hooks/useFormValidation';
import FormInput from './FormInput';

const initialState = {
  email: '',
  password: '',
  passwordConfirm: '',
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
  const [rememberMe, setRememberMe] = useState(false);
  
  const {
    values,
    handleChange,
    handleBlur,
    validateForm,
    getFieldError,
    hasFieldError
  } = useFormValidation(initialState);

  function handleSubmit(e) {
    e.preventDefault();
    
    // Validation complète du formulaire
    const isValid = validateForm();
    
    if (!isValid) {
      onSubmit(null, 'Veuillez corriger les erreurs dans le formulaire');
      return;
    }

    // Vérification de la confirmation du mot de passe
    if (values.password !== values.passwordConfirm) {
      onSubmit(null, 'Les mots de passe ne correspondent pas');
      return;
    }
    
    // Envoyer les données sans passwordConfirm
    const { passwordConfirm, ...formData } = values;
    onSubmit({ ...formData, rememberMe });
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {/* Prénom */}
      <FormInput
        label={t('registerPage.firstNameLabel')}
        name="first_name"
        type="text"
        value={values.first_name}
        onChange={handleChange}
        onBlur={handleBlur}
        error={getFieldError('first_name')}
        placeholder={t('registerPage.firstNamePlaceholder')}
        required
      />

      {/* Nom */}
      <FormInput
        label={t('registerPage.lastNameLabel')}
        name="last_name"
        type="text"
        value={values.last_name}
        onChange={handleChange}
        onBlur={handleBlur}
        error={getFieldError('last_name')}
        placeholder={t('registerPage.lastNamePlaceholder')}
        required
      />

      {/* Email */}
      <FormInput
        label={t('registerPage.emailLabel')}
        name="email"
        type="email"
        value={values.email}
        onChange={handleChange}
        onBlur={handleBlur}
        error={getFieldError('email')}
        placeholder={t('registerPage.emailPlaceholder')}
        required
      />

      {/* Téléphone */}
      <FormInput
        label={t('registerPage.phoneLabel')}
        name="phone"
        type="tel"
        value={values.phone}
        onChange={handleChange}
        onBlur={handleBlur}
        error={getFieldError('phone')}
        placeholder={t('registerPage.phonePlaceholder')}
        required
      />

      {/* Adresse (numéro et rue) */}
      <div className="grid grid-cols-2 gap-4">
        <FormInput
          label={t('registerPage.streetNumberLabel') || 'N°'}
          name="street_number"
          type="text"
          value={values.street_number}
          onChange={handleChange}
          onBlur={handleBlur}
          error={getFieldError('street_number')}
          placeholder={t('registerPage.streetNumberPlaceholder') || ''}
        />
        <FormInput
          label={t('registerPage.streetNameLabel') || 'Rue'}
          name="street_name"
          type="text"
          value={values.street_name}
          onChange={handleChange}
          onBlur={handleBlur}
          error={getFieldError('street_name')}
          placeholder={t('registerPage.streetNamePlaceholder') || ''}
        />
      </div>

      {/* Complément */}
      <FormInput
        label={t('registerPage.complementLabel') || 'Complément'}
        name="complement"
        type="text"
        value={values.complement}
        onChange={handleChange}
        onBlur={handleBlur}
        error={getFieldError('complement')}
        placeholder={t('registerPage.complementPlaceholder') || ''}
      />

      {/* Code postal, Ville, Pays */}
      <div className="grid grid-cols-3 gap-4">
        <FormInput
          label={t('registerPage.postalCodeLabel')}
          name="postal_code"
          type="text"
          value={values.postal_code}
          onChange={handleChange}
          onBlur={handleBlur}
          error={getFieldError('postal_code')}
          placeholder={t('registerPage.postalCodePlaceholder')}
        />
        <FormInput
          label={t('registerPage.cityLabel')}
          name="city"
          type="text"
          value={values.city}
          onChange={handleChange}
          onBlur={handleBlur}
          error={getFieldError('city')}
          placeholder={t('registerPage.cityPlaceholder')}
        />
        <FormInput
          label={t('registerPage.countryLabel')}
          name="country"
          type="text"
          value={values.country}
          onChange={handleChange}
          onBlur={handleBlur}
          error={getFieldError('country')}
          placeholder={t('registerPage.countryPlaceholder')}
        />
      </div>

      {/* Mot de passe */}
      <FormInput
        label={t('registerPage.passwordLabel')}
        name="password"
        type="password"
        value={values.password}
        onChange={handleChange}
        onBlur={handleBlur}
        error={getFieldError('password')}
        placeholder="••••••••"
        required
      />

      {/* Confirmation mot de passe */}
      <FormInput
        label={t('registerPage.passwordConfirmLabel')}
        name="passwordConfirm"
        type="password"
        value={values.passwordConfirm}
        onChange={handleChange}
        onBlur={handleBlur}
        error={getFieldError('passwordConfirm')}
        placeholder="••••••••"
        required
      />

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
      
      <button type="submit" disabled={loading} className="w-full px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors">
        {loading ? t('registerPage.loadingButton') : t('registerPage.submitButton')}
      </button>
    </form>
  );
}
