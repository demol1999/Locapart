// src/App.jsx
import React, { Suspense } from 'react'; // Import Suspense pour i18next
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
// Importe d'autres pages/composants ici si nécessaire
// import DashboardPage from './pages/DashboardPage'; // Exemple

// Composant simple pour simuler une page protégée (sera amélioré plus tard)
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('authToken');
  return token ? children : <Navigate to="/login" replace />;
};

// Composant simple pour simuler une page publique (redirige si connecté)
const PublicRoute = ({ children }) => {
    const token = localStorage.getItem('authToken');
    // Si l'utilisateur est connecté et essaie d'accéder à Login/Register, redirige vers le dashboard
    // Tu peux ajuster ce comportement si tu veux autoriser l'accès même connecté
    return !token ? children : <Navigate to="/dashboard" replace />;
};


function App() {
  return (
    // Suspense est nécessaire pour le chargement des traductions i18next
    <Suspense fallback={<div>Loading translations...</div>}>
      <Router>
        <Routes>
          {/* Routes Publiques (Login, Register) */}
          <Route path="/login" element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          } />
          <Route path="/register" element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          } />

          {/* Routes Protégées (Exemple: Dashboard) */}
          {/* Décommente et crée cette page quand tu seras prêt */}
          {/*
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } />
          */}

          {/* Redirection par défaut */}
          {/* Si l'utilisateur est connecté, va au dashboard, sinon au login */}
          <Route path="/" element={
             localStorage.getItem('authToken') ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
           } />

          {/* Route pour gérer les chemins non trouvés */}
          <Route path="*" element={<div>404 - Page Not Found</div>} /> {/* Tu peux créer une page 404 plus stylée */}

        </Routes>
      </Router>
    </Suspense>
  );
}

export default App;