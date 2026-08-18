import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Activity,
  Shield,
  PlaySquare,
  ShieldCheck,
  Circle,
} from 'lucide-react';
import { useStore } from '../../store/useStore';

interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { name: 'Dashboard',    path: '/',           icon: LayoutDashboard },
  { name: 'Users',        path: '/users',      icon: Users           },
  { name: 'Logs & Events',path: '/logs',       icon: Activity        },
  { name: 'Policies',     path: '/policies',   icon: Shield          },
  { name: 'Simulation',   path: '/simulation', icon: PlaySquare      },
];

export const Sidebar: React.FC = () => {
  const isSimulationRunning = useStore((state) => state.isSimulationRunning);

  return (
    <aside className="w-64 h-screen bg-background border-r border-border flex flex-col flex-shrink-0">

      {/* Brand */}
      <div className="h-16 flex items-center px-6 border-b border-border">
        <ShieldCheck className="w-6 h-6 text-risk-low mr-3 flex-shrink-0" />
        <div>
          <span className="text-textMain font-bold text-base tracking-wide">BBAC Sim</span>
          <p className="text-textMuted text-xs leading-none mt-0.5">Security Dashboard</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-surface text-textMain'
                    : 'text-textMuted hover:text-textMain hover:bg-surface/50'
                }`
              }
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {item.name}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer — shows live simulation status from Zustand store */}
      <div className="p-4 border-t border-border space-y-2">
        <div className="flex items-center gap-2">
          <Circle
            className={`w-2 h-2 flex-shrink-0 fill-current ${
              isSimulationRunning ? 'text-risk-low' : 'text-textMuted'
            }`}
          />
          <span className="text-xs font-mono text-textMuted">
            {isSimulationRunning ? 'Simulation running' : 'Simulation stopped'}
          </span>
        </div>
        <div className="text-xs font-mono text-textMuted opacity-50">
          v1.0.0-beta
        </div>
      </div>
    </aside>
  );
};