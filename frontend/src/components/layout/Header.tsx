import React from 'react';
import { useLocation } from 'react-router-dom';
import { Wifi, WifiOff, Bell } from 'lucide-react';
import { useStore, selectHasCriticalAlert } from '../../store/useStore';
import { cn } from '../ui/Card';

interface HeaderProps {
  // Passed from AppLayout.tsx which calls useWebSocket() once at the layout
  // level so the WebSocket connection is established exactly one time for
  // the entire app, not recreated each time Header re-renders.
  isConnected: boolean;
}

const PAGE_TITLES: Record<string, string> = {
  '/':          'Dashboard Overview',
  '/users':     'User Management',
  '/logs':      'Logs & Events',
  '/policies':  'Security Policies',
  '/simulation':'Simulation Controls',
};

const getPageTitle = (pathname: string): string => {
  if (pathname.startsWith('/users/')) return 'User Details';
  return PAGE_TITLES[pathname] ?? 'Dashboard';
};

export const Header: React.FC<HeaderProps> = ({ isConnected }) => {
  const location = useLocation();
  const hasCriticalAlert = useStore(selectHasCriticalAlert);

  return (
    <header className="h-16 bg-background border-b border-border flex items-center justify-between px-6 flex-shrink-0">

      {/* Page title */}
      <h1 className="text-lg font-semibold text-textMain tracking-tight">
        {getPageTitle(location.pathname)}
      </h1>

      <div className="flex items-center space-x-3">

        {/* WebSocket connection status */}
        <div
          className={cn(
            'flex items-center space-x-2 px-3 py-1.5 rounded-md border text-xs font-medium',
            isConnected
              ? 'bg-decision-allow/10 border-decision-allow/20 text-decision-allow'
              : 'bg-decision-block/10 border-decision-block/20 text-decision-block'
          )}
        >
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4" />
              <span>Live Stream Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4" />
              <span>Disconnected</span>
            </>
          )}
        </div>

        {/* Alert bell — dot is driven by selectHasCriticalAlert,
            not a hardcoded mock, so it only appears when BLOCK decisions
            are actually present in the live event stream. */}
        <button
          aria-label={hasCriticalAlert ? 'Critical alerts present' : 'No active alerts'}
          className="relative p-2 text-textMuted hover:text-textMain hover:bg-surface rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-border"
        >
          <Bell className="w-5 h-5" />
          {hasCriticalAlert && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-decision-block rounded-full border border-background" />
          )}
        </button>
      </div>
    </header>
  );
};