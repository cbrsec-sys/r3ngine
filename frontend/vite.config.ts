import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import basicSsl from '@vitejs/plugin-basic-ssl';

// https://vitejs.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [
    react(),
    basicSsl()
  ],
  base: command === 'serve' ? '/' : '/staticfiles/',
  build: {
    chunkSizeWarningLimit: 1000, // raise slightly (optional, not a fix)

    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-[hash].js`,
        chunkFileNames: `assets/[name]-[hash].js`,
        assetFileNames: `assets/[name]-[hash].[ext]`,

        manualChunks(id) {
          if (id.includes('node_modules')) {
            // Core React stack
            if (id.includes('react') || id.includes('react-dom')) {
              return 'vendor-react';
            }

            // Routing
            if (id.includes('react-router')) {
              return 'vendor-router';
            }

            // Charts (VERY important for your use case)
            if (
              id.includes('recharts') ||
              id.includes('echarts') ||
              id.includes('chart.js') ||
              id.includes('d3')
            ) {
              return 'vendor-charts';
            }

            // UI frameworks (if you're using any)
            if (
              id.includes('@mui') ||
              id.includes('tailwind') ||
              id.includes('react-markdown') ||
              id.includes('lucide')
            ) {
              return 'vendor-ui';
            }

            // Utility libs
            if (id.includes('lodash') || id.includes('axios') || id.includes('date-fns') || id.includes('react-markdown') || id.includes('lucide')) {
              return 'vendor-utils';
            }

            // Everything else from node_modules
            return 'vendor';
          }
        }
      }
    }
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/login': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/logout': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/onboarding': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
}));
