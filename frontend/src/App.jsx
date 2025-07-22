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
import BuildingPage from './pages/BuildingPage';
import ApartmentCreatePage from './pages/ApartmentCreatePage';
import ApartmentDetails from './pages/ApartmentDetails';
import CoproPage from './pages/CoproPage';
import SyndicatCreatePage from './pages/SyndicatCreatePage';
import CoproCreatePage from './pages/CoproCreatePage';
import OAuthCallbackPage from './pages/OAuthCallbackPage';
import SubscriptionPage from './pages/SubscriptionPage';
import PaymentHistoryPage from './pages/PaymentHistoryPage';
import ApartmentRoomsPage from './pages/ApartmentRoomsPage';
import RoomPhotosPage from './pages/RoomPhotosPage';
import ApartmentGalleryPage from './pages/ApartmentGalleryPage';
import FloorPlanEditorPage from './pages/FloorPlanEditorPage';
import NotificationsPage from './pages/NotificationsPage';
import NotificationSettingsPage from './pages/NotificationSettingsPage';

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
            
            {/* Route OAuth callback */}
            <Route path="/auth/:provider/callback" element={<OAuthCallbackPage />} />

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
            {/* Détail appartement */}
            <Route path="/apartments/:apartmentId" element={
              <ProtectedRoute>
                <ApartmentDetails />
              </ProtectedRoute>
            } />
            {/* Détail copropriété */}
            <Route path="/copros/:coproId" element={
              <ProtectedRoute>
                <CoproPage />
              </ProtectedRoute>
            } />
            {/* Création copropriété */}
            <Route path="/copros/new" element={
              <ProtectedRoute>
                <CoproCreatePage />
              </ProtectedRoute>
            } />
            {/* Création immeuble */}
            <Route path="/buildings/new" element={
              <ProtectedRoute>
                <BuildingCreatePage />
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

            <Route path="/syndicats_copro/create/:coproId" element={
              <ProtectedRoute>
                <SyndicatCreatePage />
              </ProtectedRoute>
            } />

            {/* Routes d'abonnement et paiement */}
            <Route path="/subscription" element={
              <ProtectedRoute>
                <SubscriptionPage />
              </ProtectedRoute>
            } />
            <Route path="/payments" element={
              <ProtectedRoute>
                <PaymentHistoryPage />
              </ProtectedRoute>
            } />

            {/* Routes de gestion des pièces et photos */}
            <Route path="/apartments/:apartmentId/rooms" element={
              <ProtectedRoute>
                <ApartmentRoomsPage />
              </ProtectedRoute>
            } />
            <Route path="/rooms/:roomId/photos" element={
              <ProtectedRoute>
                <RoomPhotosPage />
              </ProtectedRoute>
            } />
            <Route path="/apartments/:apartmentId/gallery" element={
              <ProtectedRoute>
                <ApartmentGalleryPage />
              </ProtectedRoute>
            } />

            {/* Routes de l'éditeur de plans 2D */}
            <Route path="/floor-plan-editor" element={
              <ProtectedRoute>
                <FloorPlanEditorPage />
              </ProtectedRoute>
            } />
            <Route path="/floor-plan-editor/:planId" element={
              <ProtectedRoute>
                <FloorPlanEditorPage />
              </ProtectedRoute>
            } />

            {/* Routes de notifications */}
            <Route path="/notifications" element={
              <ProtectedRoute>
                <NotificationsPage />
              </ProtectedRoute>
            } />
            <Route path="/notification-settings" element={
              <ProtectedRoute>
                <NotificationSettingsPage />
              </ProtectedRoute>
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