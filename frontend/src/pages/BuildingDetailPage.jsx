import React from 'react';
import { useParams } from 'react-router-dom';

const BuildingDetailPage = () => {
  const { id } = useParams();
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="p-8 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-4">Immeuble #{id}</h2>
        <p>Page de description de l'immeuble (à compléter).</p>
      </div>
    </div>
  );
};

export default BuildingDetailPage;
