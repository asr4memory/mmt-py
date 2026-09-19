import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
    plugins: [vue()],
    test: {
        environment: "jsdom",
        // Without this, vitest builds a new jsdom instance for each of the test
        // files, which accounts for about three quarters of the run time. With
        // isolation turned off, each worker builds one jsdom and reuses it, so
        // module state and globals persist across the files a worker runs.
        isolate: false,
        setupFiles: ["./assets/js/test-setup.ts"],
    },
});
