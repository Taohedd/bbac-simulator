import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
    // Proxies frontend requests to the FastAPI backend during development.
    // Lets api/client.ts and useWebSocket.ts use relative paths
    // ('/api/...', '/ws/stream') instead of hardcoding http://localhost:8000,
    // and avoids any CORS friction entirely since requests appear same-origin.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true, // Required — enables WebSocket proxying, not just HTTP
      },
    },
  },
});