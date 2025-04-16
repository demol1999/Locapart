import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Login from './pages/Login';
import Signup from './pages/Signup';
import BuildingDetails from './pages/BuildingDetails';
import ApartmentDetails from './pages/ApartmentDetails';
import './i18n';

function App() {
  const token = localStorage.getItem('token');

  return (
    <Router>
      <div className="min-h-screen pt-16 bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-white">
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/building/:id" element={<BuildingDetails />} />
          <Route path="/apartment/:id" element={<ApartmentDetails />} />

          {/* 🔐 Protéger la création d’immeuble */}
          <Route
            path="/building/new"
            element={token ? <BuildingDetails /> : <Navigate to="/login" />}
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
