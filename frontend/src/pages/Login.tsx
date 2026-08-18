import React, { useState } from 'react';
import { Shield, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

export const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading, error } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login(username, password);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md shadow-2xl">

        {/* Brand header */}
        <CardHeader className="text-center pb-6">
          <div className="flex justify-center mb-4">
            <div className="rounded-full bg-risk-low/10 p-3 border border-risk-low/20">
              <Shield className="h-10 w-10 text-risk-low" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight text-textMain">
            BBAC Simulator
          </CardTitle>
          <p className="text-textMuted text-sm mt-2">
            Behavioral-Based Access Control
          </p>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Error message */}
            {error && (
              <div className="bg-risk-high/10 border border-risk-high/20 text-risk-high text-sm p-3 rounded-md flex items-center gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {/* Username */}
            <div className="space-y-2">
              <label
                className="text-sm font-medium text-textMain"
                htmlFor="username"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-textMain placeholder:text-textMuted focus:outline-none focus:border-risk-low focus:ring-1 focus:ring-risk-low transition-colors"
                placeholder="Enter your username"
                required
                disabled={isLoading}
              />
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label
                className="text-sm font-medium text-textMain"
                htmlFor="password"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-textMain placeholder:text-textMuted focus:outline-none focus:border-risk-low focus:ring-1 focus:ring-risk-low transition-colors"
                placeholder="Enter your password"
                required
                disabled={isLoading}
              />
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading || !username || !password}
              className="w-full bg-risk-low text-background font-semibold rounded-md py-2.5 mt-2 flex justify-center items-center hover:bg-risk-low/90 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Demo credentials hint */}
          <div className="mt-8 pt-6 border-t border-border text-center">
            <p className="text-xs text-textMuted mb-3 font-semibold uppercase tracking-wider">
              Demo Credentials
            </p>
            <div className="text-xs text-textMuted space-y-2 font-mono bg-background/50 p-3 rounded border border-border/50 inline-block text-left">
              <div className="flex gap-4">
                <span className="w-12 font-semibold text-textMain">Admin:</span>
                <span>admin / admin_password</span>
              </div>
              <div className="flex gap-4">
                <span className="w-12 font-semibold text-textMain">User:</span>
                <span>user / user_password</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};