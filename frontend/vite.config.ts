import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import { compression } from 'vite-plugin-compression2';

// https://vitejs.dev/config/
const isAnalyze = process.env.ANALYZE === 'true';

export default defineConfig({
  plugins: [
    react(),
    // Bundle analyzer - only when ANALYZE=true
    isAnalyze &&
      visualizer({ filename: 'dist/stats.html', open: true, gzipSize: true, brotliSize: true }),
    // Gzip compression (keep original files for fallback)
    compression({ algorithm: 'gzip', threshold: 10240, deleteOriginFile: true }),
    // Brotli compression - better than gzip (15-25% smaller)
    compression({ algorithm: 'brotliCompress', threshold: 10240, deleteOriginFile: true }),
  ].filter(Boolean),
  build: {
    target: 'esnext',
    minify: 'esbuild',
    cssMinify: true,
    cssCodeSplit: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        // Автоматическое разделение чанков Vite (безопасное)
        // manualChunks отключён для избежания циклических зависимостей
        // Оптимизация размера чанков
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: info => {
          const infoSrc = info.name || '';
          if (/\.(css)$/i.test(infoSrc)) {
            return 'assets/css/[name]-[hash][extname]';
          }
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(infoSrc)) {
            return 'assets/images/[name]-[hash][extname]';
          }
          if (/\.(woff2?|ttf|otf|eot)$/i.test(infoSrc)) {
            return 'assets/fonts/[name]-[hash][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
    // Увеличиваем лимит для предупреждений о размере
    chunkSizeWarningLimit: 1000,
  },
  optimizeDeps: {
    // Предварительная сборка тяжелых зависимостей
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'antd',
      '@ant-design/icons',
      '@tanstack/react-query',
      'axios',
      'dayjs',
      'zustand',
      'i18next',
      'react-i18next',
    ],
    // Исключаем charts из предварительной сборки (lazy-loaded)
    exclude: ['@ant-design/charts'],
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
