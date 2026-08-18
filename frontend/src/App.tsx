import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useStore, selectIsAuthenticated, selectIsHydrated } from './store/useStore';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { Users } from './pages/Users';
import { Logs } from './pages/Logs';
import { Policies } from './pages/Policies';
import { Simulation } from './pages/Simulation';
import { Login } from './pages/Login';
import { UserPanel } from './pages/UserPanel';

const App: React.FC = () => {
  const isAuthenticated = useStore(selectIsAuthenticated);
  const authRole = useStore((state) => state.authRole);

  return (
    <Router>
      {!isAuthenticated && <Login />}
      {isAuthenticated && authRole !== 'admin' && <UserPanel />}
      {isAuthenticated && authRole === 'admin' && (
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="users" element={<Users />} />
            <Route path="logs" element={<Logs />} />
            <Route path="policies" element={<Policies />} />
            <Route path="simulation" element={<Simulation />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      )}
    </Router>
  );
};

export default App;