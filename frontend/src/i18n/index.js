import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import fr from './fr.json';
import en from './en.json';

// 📌 Initialisation de la config de i18n
i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr },
    en: { translation: en },
  },
  lng: 'fr', // langue par défaut
  fallbackLng: 'en', // si clé absente en fr → fallback en
  interpolation: {
    escapeValue: false, // Pas besoin d’échapper dans React
  },
});

export default i18n;
