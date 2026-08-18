import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useWebSocket } from '../../hooks/useWebSocket';

export const AppLayout: React.FC = () => {
  // Establish one WebSocket connection for the entire app.
  // isConnected is passed to Header so it can display the live
  // stream status indicator without managing its own connection.
  const { isConnected } = useWebSocket();

  return (
    <div className="flex h-screen w-screen bg-background text-textMain overflow-hidden font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header isConnected={isConnected} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};