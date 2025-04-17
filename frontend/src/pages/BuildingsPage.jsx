import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/api';
import BuildingCard from '../components/BuildingCard';
import AddBuildingCard from '../components/AddBuildingCard';

const BuildingsPage = () => {
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchBuildings = async () => {
      try {
        const response = await apiClient.get('/buildings/');
        setBuildings(response.data);
      } catch (error) {
        // Gérer l'erreur (ex: non connecté)
        setBuildings([]);
      } finally {
        setLoading(false);
      }
    };
    fetchBuildings();
  }, []);

  if (loading) return <div className="p-8 text-center">Chargement...</div>;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
      <h2 className="text-2xl font-bold mb-6">Mes immeubles</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6">
        {buildings.map((building) => (
          <BuildingCard
            key={building.id}
            building={building}
            onClick={() => navigate(`/buildings/${building.id}`)}
          />
        ))}
        {/* Case + pour ajouter un immeuble */}
        <AddBuildingCard onClick={() => navigate('/buildings/new')} />
      </div>
    </div>
  );
};

export default BuildingsPage;
