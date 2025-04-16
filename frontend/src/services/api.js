import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getBuildings = (token) =>
  api.get('/buildings/', {
    headers: { Authorization: `Bearer ${token}` },
  });

// Tu pourras ajouter d'autres appels ici, comme getBuilding, createBuilding, etc.