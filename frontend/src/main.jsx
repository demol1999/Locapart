// src/main.jsx (ou index.js selon ta structure)
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css'; // Assure-toi que ton CSS global (et Tailwind) est importé
import './i18n'; // Importe la configuration i18next pour l'initialiser

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);