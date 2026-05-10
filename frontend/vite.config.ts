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
    manifest: true,
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Main entry points should NOT have hashes for Django compatibility
        entryFileNames: 'assets/[name].js',
        // Chunks can have hashes for caching
        chunkFileNames: 'assets/[name]-[hash].js',
        // Assets like CSS should also have stable names if possible
        assetFileNames: 'assets/[name].[ext]',
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            // Core Frameworks
            if (id.includes('react/') || id.includes('react-dom/')) return 'vendor-react';
            if (id.includes('@tanstack')) return 'vendor-router';
            
            // UI & Styling
            if (id.includes('@mui') || id.includes('@emotion')) return 'vendor-mui';
            if (id.includes('lucide-react')) return 'vendor-icons';
            
            // Visualization
            if (id.includes('echarts') || id.includes('zrender')) return 'vendor-echarts';
            if (id.includes('apexcharts') || id.includes('react-apexcharts')) return 'vendor-viz';
            
            // Animations & Effects
            if (id.includes('framer-motion') || id.includes('canvas-confetti') || id.includes('animejs')) return 'vendor-effects';
            
            // Utils
            if (id.includes('axios') || id.includes('date-fns') || id.includes('lodash') || id.includes('react-markdown')) return 'vendor-utils';
            
            return 'vendor-base';
          }
        },
      },
    },
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
