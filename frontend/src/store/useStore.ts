import { create } from 'zustand';
import { RiskEvent } from '../types';

const MAX_LIVE_EVENTS = 200;
const MAX_RECENT_ALERTS = 20;

interface AppState {
  // ------------------------------------------------------------------
  // Live WebSocket event stream
  // ------------------------------------------------------------------
  liveEvents: RiskEvent[];
  addLiveEvent: (event: RiskEvent) => void;
  clearLiveEvents: () => void;

  // ------------------------------------------------------------------
  // Simulation status
  // ------------------------------------------------------------------
  isSimulationRunning: boolean;
  setSimulationRunning: (running: boolean) => void;

  // ------------------------------------------------------------------
  // Selected user — shared between UserTable and UserDetailModal
  // ------------------------------------------------------------------
  selectedUserId: string | null;
  setSelectedUserId: (userId: string | null) => void;

  // ------------------------------------------------------------------
  // Authentication state
  // ------------------------------------------------------------------
  authToken: string | null;
  authRole: 'admin' | 'user' | null;
  authUsername: string | null;
  setAuth: (token: string, role: 'admin' | 'user', username: string) => void;
  clearAuth: () => void;
}

export const useStore = create<AppState>((set) => ({
  // ------------------------------------------------------------------
  // Live events
  // ------------------------------------------------------------------
  liveEvents: [],

  addLiveEvent: (event: RiskEvent) =>
    set((state) => {
      const updatedEvents = [event, ...state.liveEvents];
      if (updatedEvents.length > MAX_LIVE_EVENTS) {
        updatedEvents.length = MAX_LIVE_EVENTS;
      }
      return { liveEvents: updatedEvents };
    }),

  clearLiveEvents: () => set({ liveEvents: [] }),

  // ------------------------------------------------------------------
  // Simulation status
  // ------------------------------------------------------------------
  isSimulationRunning: false,
  setSimulationRunning: (running: boolean) =>
    set({ isSimulationRunning: running }),

  // ------------------------------------------------------------------
  // Selected user
  // ------------------------------------------------------------------
  selectedUserId: null,
  setSelectedUserId: (userId: string | null) =>
    set({ selectedUserId: userId }),

  // ------------------------------------------------------------------
  // Authentication
  // ------------------------------------------------------------------
  authToken: null,
  authRole: null,
  authUsername: null,

  setAuth: (token: string, role: 'admin' | 'user', username: string) =>
    set({ authToken: token, authRole: role, authUsername: username }),

  clearAuth: () =>
    set({ authToken: null, authRole: null, authUsername: null }),
}));

// ------------------------------------------------------------------
// Selectors
// ------------------------------------------------------------------

/** Returns only MFA_CHALLENGE and BLOCK events, newest first, capped at MAX_RECENT_ALERTS. */
export const selectRecentAlerts = (state: AppState): RiskEvent[] =>
  state.liveEvents
    .filter((e) => e.decision === 'MFA_CHALLENGE' || e.decision === 'BLOCK')
    .slice(0, MAX_RECENT_ALERTS);

/** True if any BLOCK decision appears in the most recent events — drives the bell badge. */
export const selectHasCriticalAlert = (state: AppState): boolean =>
  state.liveEvents
    .slice(0, MAX_RECENT_ALERTS)
    .some((e) => e.decision === 'BLOCK');

/** True if a valid JWT token is stored — drives route protection in App.tsx. */
export const selectIsAuthenticated = (state: AppState): boolean =>
  state.authToken !== null;
/** Always true — no persist middleware in this project so hydration is instant. */
export const selectIsHydrated = (_state: AppState): boolean => true;