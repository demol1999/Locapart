import { useTranslation } from 'react-i18next';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getBuildings } from '../services/api';

const Home = () => {
  const { t } = useTranslation();
  const [buildings, setBuildings] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    getBuildings(token)
      .then((res) => setBuildings(res.data))
      .catch((err) => console.error(err));
  }, []);

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">{t('welcome')} 👋</h1>
        <Link
          to="/building/new"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          ➕ {t('create_building') || 'Créer un immeuble'}
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
        {buildings.map((b) => (
          <Link
            key={b.id}
            to={`/building/${b.id}`}
            className="block border rounded-lg overflow-hidden bg-white dark:bg-gray-700 shadow hover:shadow-lg transition"
          >
            <img
              src={`${import.meta.env.VITE_API_URL}/${b.photos?.[0]?.filename || 'uploads/default.jpg'}`}
              alt={b.name}
              className="h-40 w-full object-cover"
            />
            <div className="p-4">
              <h2 className="text-lg font-semibold">{b.name}</h2>
              <p className="text-sm text-gray-500 dark:text-gray-300">
                {b.street_number} {b.street_name}, {b.city}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default Home;