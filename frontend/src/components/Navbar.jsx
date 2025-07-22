import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { LogOut, User, Globe, Home } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import NotificationBell from './NotificationBell';

// Single Responsibility: Composant responsable uniquement de la navigation
const Navbar = () => {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const [openMenu, setOpenMenu] = useState(false);
  const menuRef = useRef(null);

  // Single Responsibility: Hook pour gérer la fermeture du menu
  useEffect(() => {
    if (!openMenu) return;
    
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpenMenu(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [openMenu]);

  // Single Responsibility: Fonction pour changer de langue
  const changeLang = (lang) => {
    i18n.changeLanguage(lang);
  };

  // Single Responsibility: Composant pour les boutons de langue
  const LanguageToggle = ({ lang, flag, label }) => (
    <Button
      variant={i18n.language === lang ? "default" : "outline"}
      size="sm"
      onClick={() => changeLang(lang)}
      className="text-sm"
      aria-label={label}
    >
      {flag}
    </Button>
  );

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b">
      <div className="container flex h-16 items-center px-4">
        {/* Logo et navigation principale */}
        <div className="mr-4 flex">
          <Link to="/" className="mr-6 flex items-center space-x-2 hover:opacity-80 transition-opacity">
            <Home className="h-6 w-6 text-primary" />
            <span className="font-bold text-xl">LocAppart</span>
          </Link>
        </div>
        
        {/* Navigation links pour utilisateurs connectés */}
        {user && (
          <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
            <nav className="flex items-center space-x-6 text-sm font-medium">
              <Link
                to="/buildings"
                className="transition-colors hover:text-foreground/80 text-foreground/60"
              >
                Immeubles
              </Link>
              <Link
                to="/subscription"
                className="transition-colors hover:text-foreground/80 text-foreground/60"
              >
                Abonnement
              </Link>
              <Link
                to="/floor-plan-editor"
                className="transition-colors hover:text-foreground/80 text-foreground/60"
              >
                📐 Plans
              </Link>
              <Link
                to="/copros/new"
                className="transition-colors hover:text-foreground/80 text-foreground/60"
              >
                🏢 Copros
              </Link>
            </nav>
          </div>
        )}

        {/* Actions droite */}
        <div className="flex flex-1 items-center justify-end space-x-2">
          {/* Sélecteur de langue moderne */}
          <div className="flex items-center space-x-1">
            <Globe className="h-4 w-4 text-muted-foreground" />
            <LanguageToggle 
              lang="fr" 
              flag="🇫🇷" 
              label="Changer la langue en français" 
            />
            <LanguageToggle 
              lang="en" 
              flag="🇬🇧" 
              label="Change language to English" 
            />
          </div>

          {/* Cloche de notifications (utilisateurs connectés seulement) */}
          {user && <NotificationBell />}

          {/* Menu utilisateur ou bouton de connexion */}
          {user ? (
            <div className="relative" ref={menuRef}>
              <Button
                variant="ghost"
                className="relative h-9 w-9 rounded-full"
                onClick={() => setOpenMenu(!openMenu)}
              >
                <div className="flex items-center justify-center w-full h-full bg-primary text-primary-foreground rounded-full">
                  <User className="h-4 w-4" />
                </div>
              </Button>
              
              {openMenu && (
                <div className="absolute right-0 mt-2 w-56 rounded-md bg-popover shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                  <div className="py-1">
                    <div className="px-4 py-2 text-sm text-muted-foreground border-b">
                      <p className="font-medium text-foreground">
                        {user.first_name} {user.last_name}
                      </p>
                      <p className="text-xs">{user.email}</p>
                    </div>
                    <Link
                      to="/profile"
                      className="flex items-center px-4 py-2 text-sm text-foreground hover:bg-accent"
                      onClick={() => setOpenMenu(false)}
                    >
                      <User className="mr-2 h-4 w-4" />
                      Mon Profil
                    </Link>
                    <Link
                      to="/notifications"
                      className="flex items-center px-4 py-2 text-sm text-foreground hover:bg-accent"
                      onClick={() => setOpenMenu(false)}
                    >
                      🔔 Notifications
                    </Link>
                    <Link
                      to="/notification-settings"
                      className="flex items-center px-4 py-2 text-sm text-foreground hover:bg-accent"
                      onClick={() => setOpenMenu(false)}
                    >
                      ⚙️ Paramètres
                    </Link>
                    <Link
                      to="/payments"
                      className="flex items-center px-4 py-2 text-sm text-foreground hover:bg-accent border-b"
                      onClick={() => setOpenMenu(false)}
                    >
                      💳 Paiements
                    </Link>
                    <Button
                      variant="ghost"
                      className="w-full justify-start px-4 py-2 text-sm text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => {
                        logout();
                        setOpenMenu(false);
                      }}
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      {t('logout')}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <Button asChild size="sm">
              <Link to="/login">
                {t('login')}
              </Link>
            </Button>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
