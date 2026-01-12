import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import { compression } from 'vite-plugin-compression2';
import purgecss from 'vite-plugin-purgecss';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    visualizer({ filename: 'dist/stats.html', open: false, gzipSize: true, brotliSize: true }),
    compression({ algorithm: 'brotliCompress' }),
    purgecss({
      content: ['src/**/*.{js,jsx,ts,tsx}', 'index.html'],
      safelist: [/^ant-/],
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          antd: ['antd'],
          router: ['react-router-dom'],
          charts: ['recharts'],
          utils: ['axios', 'date-fns', '@tanstack/react-query', 'dompurify'],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
