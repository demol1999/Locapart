import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';

import React, { useState, useRef, useEffect } from 'react';

const Navbar = () => {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const [openMenu, setOpenMenu] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!openMenu) return;
    function handleClick(e) {
      // Ferme le menu si clic en dehors du bouton ou du menu
      const dropdownMenu = document.getElementById('dropdownMenu');
      const menuButton = document.getElementById('menuButton');
      if (
        dropdownMenu &&
        !dropdownMenu.contains(e.target) &&
        menuButton &&
        !menuButton.contains(e.target)
      ) {
        setOpenMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [openMenu]);

  const changeLang = (lang) => {
    i18n.changeLanguage(lang);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white dark:bg-gray-800 shadow-md dark:text-white transition-colors duration-200" style={{ height: '1cm', minHeight: '1cm', maxHeight: '1cm' }}>
      <div className="navbar-inner h-full flex flex-row flex-nowrap w-screen min-w-0 justify-end items-center px-4 sm:px-8">
        {/* Logo et nom du site à gauche */}
        <Link to="/" className="flex items-center space-x-3 hover:opacity-80 transition-opacity select-none mr-auto">
          <img
            src="/logo.png"
            alt="Logo"
            className="h-[0.8cm] w-[0.8cm] object-contain"
            style={{ maxHeight: '0.8cm', maxWidth: '0.8cm' }}
          />
          <span className="text-xl font-bold tracking-wide">LocAppart</span>
        </Link>
        {/* Bloc actions à droite : langues + connexion/profil */}
        <div className="flex flex-row items-center gap-1 ml-auto min-w-0 overflow-x-auto whitespace-nowrap">
          <button 
            onClick={() => changeLang('fr')} 
            className={`text-lg px-2 py-1 rounded transition-all ${i18n.language === 'fr' ? 'bg-blue-600 text-white font-bold border border-blue-700' : 'hover:opacity-80'}`}
            aria-label="Changer la langue en français"
            aria-pressed={i18n.language === 'fr'}
            style={{ lineHeight: 1 }}
          >
            🇫🇷
          </button>
          <button 
            onClick={() => changeLang('en')} 
            className={`text-lg px-2 py-1 rounded transition-all ${i18n.language === 'en' ? 'bg-blue-600 text-white font-bold border border-blue-700' : 'hover:opacity-80'}`}
            aria-label="Change language to English"
            aria-pressed={i18n.language === 'en'}
            style={{ lineHeight: 1 }}
          >
            🇬🇧
          </button>
          {user ? (
            <>
              <button
                ref={menuRef}
                id="menuButton"
                className="flex items-center px-2 py-1 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition-colors text-sm font-medium"
                aria-label="Menu profil"
                onClick={(e) => {
                  setOpenMenu((v) => !v);
                  e.stopPropagation();
                }}
                type="button"
                style={{ userSelect: 'none' }}
              >
                {user.first_name} {user.last_name}
              </button>
              {/* Dropdown logout menu */}
              {openMenu && (
                <div
                  id="dropdownMenu"
                  className="absolute right-0 mt-2 w-40 py-2 bg-white dark:bg-gray-700 rounded-lg shadow-xl z-50 border border-gray-200 dark:border-gray-600 animate-dropdown"
                  style={{ minWidth: '8rem' }}
                >
                  <button
                    id="logoutBtn"
                    onClick={logout}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-600"
                  >
                    {t('logout')}
                  </button>
                </div>
              )}
            </>
          ) : (
            <Link 
              to="/login" 
              className="px-4 py-1.5 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition-colors text-sm font-medium"
              style={{ minHeight: '0.7cm' }}
            >
              {t('login')}
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
