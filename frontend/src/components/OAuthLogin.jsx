import React from 'react';
import { useAuth } from '../context/AuthContext';
import apiClient from '../services/api';
import '../styles/oauth.css';

const OAuthLogin = () => {
  const { oauthLogin } = useAuth();

  const handleGoogleLogin = async () => {
    try {
      // Utiliser le même flow que Facebook pour la cohérence
      const response = await apiClient.get('/auth/google/login');
      const { authorization_url } = response.data;
      
      // Rediriger vers Google
      window.location.href = authorization_url;
      
    } catch (error) {
      console.error('[OAuth] Google login error:', error);
      alert('Erreur lors de la connexion Google');
    }
  };

  const handleFacebookLogin = async () => {
    try {
      // Initier le processus OAuth Facebook
      const response = await apiClient.get('/auth/facebook/login');
      const { authorization_url } = response.data;
      
      // Rediriger vers Facebook
      window.location.href = authorization_url;
      
    } catch (error) {
      console.error('[OAuth] Facebook login error:', error);
      alert('Erreur lors de la connexion Facebook');
    }
  };

  const handleMicrosoftLogin = async () => {
    try {
      // Initier le processus OAuth Microsoft
      const response = await apiClient.get('/auth/microsoft/login');
      const { authorization_url } = response.data;
      
      // Rediriger vers Microsoft
      window.location.href = authorization_url;
      
    } catch (error) {
      console.error('[OAuth] Microsoft login error:', error);
      alert('Erreur lors de la connexion Microsoft');
    }
  };

  return (
    <div className="oauth-login">
      <div className="oauth-divider">
        <span>ou</span>
      </div>
      
      <div className="oauth-buttons">
        <button 
          type="button"
          className="google-login-btn"
          onClick={handleGoogleLogin}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Continuer avec Google
        </button>
        
        <button 
          type="button"
          className="facebook-login-btn"
          onClick={handleFacebookLogin}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" fill="#1877F2"/>
          </svg>
          Continuer avec Facebook
        </button>

        <button 
          type="button"
          className="microsoft-login-btn"
          onClick={handleMicrosoftLogin}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z" fill="#00BCF2"/>
          </svg>
          Continuer avec Microsoft
        </button>
      </div>
    </div>
  );
};

export default OAuthLogin;