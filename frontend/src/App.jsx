// src/App.jsx
import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import BuildingsPage from './pages/BuildingsPage';
import BuildingCreatePage from './pages/BuildingCreatePage';
import BuildingDetailPage from './pages/BuildingDetailPage';
import BuildingPage from './pages/BuildingPage';
import ApartmentCreatePage from './pages/ApartmentCreatePage';

// Composant pour les routes protégées
const ProtectedRoute = ({ children }) => {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
};

// Composant pour les routes publiques
const PublicRoute = ({ children }) => {
  const { user } = useAuth();
  return !user ? children : <Navigate to="/" replace />;
};

function App() {
  const { user } = useAuth();

  return (
    <Suspense fallback={<div>Chargement...</div>}>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navbar />
        <main style={{ paddingTop: '1cm' }}> {/* Espace pour la navbar fixe (1cm, identique à la hauteur de la navbar) */}
          <Routes>
            {/* Routes publiques */}
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

            {/* Routes protégées */}
            <Route path="/profile" element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            } />

            {/* Immeubles - mosaïque */}
            <Route path="/buildings" element={
              <ProtectedRoute>
                <BuildingsPage />
              </ProtectedRoute>
            } />
            {/* Détail immeuble */}
            <Route path="/buildings/:buildingId" element={
              <ProtectedRoute>
                <BuildingPage />
              </ProtectedRoute>
            } />
            {/* Création appartement */}
            <Route path="/buildings/:buildingId/apartments/new" element={
              <ProtectedRoute>
                <ApartmentCreatePage />
              </ProtectedRoute>
            } />
            {/* Création immeuble */}
            <Route path="/buildings/new" element={
              <ProtectedRoute>
                <BuildingCreatePage />
              </ProtectedRoute>
            } />
            {/* Détail immeuble */}
            <Route path="/buildings/:id" element={
              <ProtectedRoute>
                <BuildingDetailPage />
              </ProtectedRoute>
            } />

            {/* Page d'accueil */}
            <Route path="/" element={
              user ? <Navigate to="/buildings" replace /> : (
                <div className="container mx-auto px-4 py-8">
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    Bienvenue sur LocAppart
                  </h1>
                </div>
              )
            } />

            {/* Route pour gérer les chemins non trouvés */}
            <Route path="*" element={
              <div className="container mx-auto px-4 py-8 text-center">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  404 - Page non trouvée
                </h1>
              </div>
            } />
          </Routes>
        </main>
      </div>
    </Suspense>
  );
}

export default App;