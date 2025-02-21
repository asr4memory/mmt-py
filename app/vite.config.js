import { defineConfig, loadEnv } from 'vite';
import { join, resolve } from 'path';

const INPUT_DIR = './assets';
const OUTPUT_DIR = './vite_assets_dist';

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(INPUT_DIR),
    },
  },
  base: '/static/',
  build: {
    manifest: 'manifest.json',
    emptyOutDir: true,
    outDir: resolve(OUTPUT_DIR),
    rollupOptions: {
      input: {
        main: join(INPUT_DIR, '/js/main.js'),
        upload_form: join(INPUT_DIR, '/js/upload_form.js'),
      },
      output: {
        // No hashes in filenames, this is done by whitenoise later.
        entryFileNames: '[name].js',      // No hash in JavaScript files
        chunkFileNames: '[name].js',      // No hash in chunk files
        assetFileNames: '[name][extname]', // No hash in asset files (CSS, images, etc.)
      },
    },
  },
});
