import React, { useState } from 'react';
import { Users as UsersIcon, Search, RefreshCw, AlertCircle } from 'lucide-react';
import { useUsers } from '../hooks/useUsers';
import { useStore } from '../store/useStore';
import { UserTable } from '../components/users/UserTable';
import { UserDetailModal } from '../components/users/UserDetailModal';

export const Users: React.FC = () => {
  const { users, isLoading, error, refetch } = useUsers();
  const [searchQuery, setSearchQuery] = useState('');

  // Use Zustand store for selectedUserId so other pages (Dashboard, Logs)
  // can deep-link into a user profile without prop drilling
  const selectedUserId = useStore((state) => state.selectedUserId);
  const setSelectedUserId = useStore((state) => state.setSelectedUserId);

  const handleViewUser = (userId: string) => {
    setSelectedUserId(userId);
  };

  const handleCloseModal = () => {
    // Small delay so the modal can animate out before state clears
    setTimeout(() => setSelectedUserId(null), 200);
  };

  // Client-side filtering by username, user_id prefix, or role
  const filteredUsers = users.filter((user) => {
    const q = searchQuery.toLowerCase();
    return (
      user.username.toLowerCase().includes(q) ||
      user.user_id.toLowerCase().includes(q) ||
      user.role.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 h-full flex flex-col">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-surfaceHover rounded-lg border border-border">
            <UsersIcon className="w-5 h-5 text-textMuted" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-textMain">User Directory</h2>
            <p className="text-sm text-textMuted">
              {users.length} user{users.length !== 1 ? 's' : ''} — risk profiles update every 5s
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Search */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-textMuted" />
            </div>
            <input
              type="text"
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-9 pr-3 py-2 border border-border rounded-lg bg-surface text-textMain placeholder-textMuted focus:outline-none focus:ring-1 focus:ring-border text-sm transition-colors"
            />
          </div>

          {/* Refresh */}
          <button
            onClick={() => void refetch()}
            disabled={isLoading}
            title="Refresh Users"
            className="flex items-center space-x-2 px-3 py-2 bg-surfaceHover hover:bg-border text-textMuted text-sm font-medium rounded-lg border border-border transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Error banner — non-blocking so existing data still shows */}
      {error && (
        <div className="p-4 bg-decision-block/10 border border-decision-block/20 rounded-lg flex items-start space-x-3 text-decision-block">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium">Failed to load users</p>
            <p className="text-sm mt-1 opacity-80">{error}</p>
          </div>
        </div>
      )}

      {/* User table */}
      <div className="flex-1 min-h-0">
        <UserTable
          users={filteredUsers}
          isLoading={isLoading}
          onViewUser={handleViewUser}
        />
      </div>

      {/* User detail modal */}
      <UserDetailModal
        userId={selectedUserId}
        isOpen={selectedUserId !== null}
        onClose={handleCloseModal}
      />
    </div>
  );
};