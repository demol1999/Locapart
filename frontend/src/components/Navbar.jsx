import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ThemeToggle from './ThemeToggle';

const Navbar = () => {
  const { t, i18n } = useTranslation();

  const changeLang = (lang) => {
    i18n.changeLanguage(lang);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex justify-between items-center px-4 sm:px-6 py-3 bg-white dark:bg-gray-800 shadow-md dark:text-white">
      {/* Logo à gauche */}
      <Link to="/" className="flex items-center space-x-2">
        <img
          src="/logo.png"
          alt="Logo"
          className="h-4 w-4 sm:h-5 sm:w-5 object-contain"
        />
        <span className="text-lg sm:text-xl font-bold">LocAppart</span>
      </Link>

      {/* Actions à droite */}
      <div className="flex items-center space-x-4 mt-2 sm:mt-0">
        <button onClick={() => changeLang('fr')} className="text-sm">🇫🇷</button>
        <button onClick={() => changeLang('en')} className="text-sm">🇬🇧</button>
        <ThemeToggle />
        <Link to="/login" className="text-sm underline hover:text-blue-600 dark:hover:text-blue-400">
          {t('login')}
        </Link>
      </div>
    </nav>
  );
};

export default Navbar;
