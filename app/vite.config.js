import { join, resolve } from "path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const INPUT_DIR = "./assets";
const OUTPUT_DIR = "./vite_assets_dist";

export default defineConfig({
    plugins: [vue()],
    define: {
        __VUE_OPTIONS_API__: 'true',
        __VUE_PROD_DEVTOOLS__: 'false',
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
    },
    resolve: {
        alias: {
            "@": resolve(INPUT_DIR),
            "vue": "vue/dist/vue.esm-bundler.js",
        },
    },
    base: "/static/",
    server: {
        watch: {
            // Don't recurse into the Python virtualenv or other non-frontend
            // trees — they hold tens of thousands of files and exhaust the
            // system's inotify watch limit.
            ignored: ["**/.venv/**", "**/__pycache__/**"],
        },
    },
    build: {
        manifest: "manifest.json",
        modulePreload: { polyfill: false },
        emptyOutDir: true,
        outDir: resolve(OUTPUT_DIR),
        rollupOptions: {
            input: {
                main: join(INPUT_DIR, "/js/main.ts"),
                transcript: join(INPUT_DIR, "/js/transcript.ts"),
                upload_form: join(INPUT_DIR, "/js/upload_form.ts"),
            },
            output: {
                // No hashes in filenames, this is done by whitenoise later.
                entryFileNames: "[name].js", // No hash in JavaScript files
                chunkFileNames: "[name].js", // No hash in chunk files
                assetFileNames: "[name][extname]", // No hash in asset files (CSS, images, etc.)
            },
        },
    },
});
