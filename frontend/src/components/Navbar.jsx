import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';

const Navbar = () => {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();

  const changeLang = (lang) => {
    i18n.changeLanguage(lang);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex justify-between items-center px-4 sm:px-6 py-3 bg-white dark:bg-gray-800 shadow-md dark:text-white transition-colors duration-200">
      {/* Logo à gauche */}
      <Link to="/" className="flex items-center space-x-3 hover:opacity-80 transition-opacity">
        <img
          src="/logo.png"
          alt="Logo"
          className="h-8 w-8 sm:h-10 sm:w-10 object-contain"
        />
        <span className="text-lg sm:text-xl font-bold">LocAppart</span>
      </Link>

      {/* Actions à droite */}
      <div className="flex items-center space-x-4 sm:space-x-6">
        <div className="flex items-center space-x-2 sm:space-x-3">
          <button 
            onClick={() => changeLang('fr')} 
            className="text-sm hover:opacity-80 transition-opacity"
            aria-label="Changer la langue en français"
          >
            🇫🇷
          </button>
          <button 
            onClick={() => changeLang('en')} 
            className="text-sm hover:opacity-80 transition-opacity"
            aria-label="Change language to English"
          >
            🇬🇧
          </button>
          <ThemeToggle />
        </div>

        {user ? (
          <div className="relative group">
            <button 
              className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition-colors"
              aria-label="Menu profil"
            >
              <span className="hidden sm:inline">{user.first_name} {user.last_name}</span>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
            </button>
            <div className="absolute right-0 mt-2 w-48 py-2 bg-white dark:bg-gray-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
              <Link to="/profile" className="block px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600">
                {t('profile')}
              </Link>
              <button 
                onClick={logout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-600"
              >
                {t('logout')}
              </button>
            </div>
          </div>
        ) : (
          <Link 
            to="/login" 
            className="px-4 py-1.5 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition-colors text-sm font-medium"
          >
            {t('login')}
          </Link>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
