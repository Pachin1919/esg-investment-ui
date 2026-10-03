import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import path from 'node:path';

// Dentio pattern: Vite on 8001, API on 8000, both overridable for parallel instances.
const port = Number(process.env.PORT ?? 8001);
const backendPort = Number(process.env.BACKEND_PORT ?? 8000);

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    host: '::',
    port,
    proxy: { '/api': { target: `http://127.0.0.1:${backendPort}`, changeOrigin: true } },
  },
  preview: { port },
});
