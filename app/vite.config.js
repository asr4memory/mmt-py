import { join, resolve } from "path";
import { defineConfig } from "vite";

const INPUT_DIR = "./assets";
const OUTPUT_DIR = "./vite_assets_dist";

export default defineConfig({
    define: {
        __VUE_OPTIONS_API__: 'true',
        __VUE_PROD_DEVTOOLS__: 'false',
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
    },
    resolve: {
        alias: {
            "@": resolve(INPUT_DIR),
        },
    },
    base: "/static/",
    build: {
        manifest: "manifest.json",
        emptyOutDir: true,
        outDir: resolve(OUTPUT_DIR),
        rollupOptions: {
            input: {
                main: join(INPUT_DIR, "/js/main.js"),
                transcript: join(INPUT_DIR, "/js/transcript.js"),
                upload_form: join(INPUT_DIR, "/js/upload_form.js"),
                resume_upload_form: join(INPUT_DIR, "/js/resume_upload_form.js"),
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
