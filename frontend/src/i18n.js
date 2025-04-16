// src/i18n.js
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Importe les fichiers de traduction
import translationEN from './locales/en/translation.json';
import translationFR from './locales/fr/translation.json';

const resources = {
  en: {
    translation: translationEN
  },
  fr: {
    translation: translationFR
  }
};

i18n
  // Détecte la langue du navigateur
  .use(LanguageDetector)
  // Passe l'instance i18n à react-i18next.
  .use(initReactI18next)
  // Initialise i18next
  .init({
    resources,
    fallbackLng: 'en', // Langue par défaut si la langue détectée n'est pas dispo
    debug: import.meta.env.DEV, // Active les logs en mode développement

    interpolation: {
      escapeValue: false, // React échappe déjà par défaut
    },

    detection: {
      // Ordre et méthodes de détection de langue
      order: ['querystring', 'cookie', 'localStorage', 'sessionStorage', 'navigator', 'htmlTag', 'path', 'subdomain'],
      caches: ['cookie', 'localStorage'], // Où stocker la langue choisie
    }
  });

export default i18n;