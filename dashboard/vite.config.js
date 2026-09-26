import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const redirectRootPlugin = {
  name: 'redirect-root',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const url = req.url?.split('?')[0];
      if (url === '/' || url === '/index.html') {
        const query = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
        res.writeHead(302, { Location: `/THE_MATREX/${query}` });
        res.end();
        return;
      }
      next();
    });
  }
};

// https://vite.dev/config/
export default defineConfig({
  base: '/THE_MATREX/',
  plugins: [redirectRootPlugin, react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: false,
    cors: true,
    proxy: {
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
