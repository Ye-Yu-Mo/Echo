import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

export default defineConfig({
  plugins: [preact()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: false, // dev 可用 http，生产请挂 Nginx + 证书
  },
});
