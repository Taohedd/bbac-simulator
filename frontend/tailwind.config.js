/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Core dashboard colors (Dark Slate aesthetic — single fixed theme, no toggle)
        background: '#0f172a',   // slate-900
        surface: '#1e293b',      // slate-800
        surfaceHover: '#334155', // slate-700
        border: '#334155',       // slate-700

        // Typography
        textMain: '#f8fafc',     // slate-50
        textMuted: '#94a3b8',    // slate-400

        // Risk & Decision Colors — kept in sync intentionally:
        // LOW risk = ALLOW, MEDIUM risk = MFA_CHALLENGE, HIGH risk = BLOCK
        risk: {
          low: '#10b981',        // emerald-500
          medium: '#f59e0b',     // amber-500
          high: '#ef4444',       // red-500
        },
        decision: {
          allow: '#10b981',      // emerald-500
          mfa: '#f59e0b',        // amber-500
          block: '#ef4444',      // red-500
        },

        // Focus ring — overrides Tailwind's default blue to match theme
        ring: {
          DEFAULT: '#10b981',    // emerald-500
        },
      },
      fontFamily: {
        // 'Inter' is loaded via a Google Fonts link in index.html (see next file).
        // Falls back cleanly to native system fonts if the link ever fails to load.
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif'
        ],
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'Liberation Mono',
          'Courier New',
          'monospace'
        ],
      },
      borderRadius: {
        'card': '8px',
      },
      boxShadow: {
        // Minimal flat design, no heavy shadows
        'card': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      },
      ringColor: {
        DEFAULT: '#10b981', // emerald-500 — matches theme instead of default blue
      },
    },
  },
  plugins: [],
}