import "vite/modulepreload-polyfill";
import { createApp } from "vue/dist/vue.esm-bundler";
import { createPinia } from "pinia";

import TranscriptTable from "./components/transcript_table.js";
import i18n from "./i18n.js";

document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("transcript-container");
    const id = Number.parseInt(container.dataset.id);
    const uploadedFileId = Number.parseInt(container.dataset.uploadedFileId);
    const projectId = Number.parseInt(container.dataset.projectId);
    const pinia = createPinia();
    const app = createApp(TranscriptTable, { id, uploadedFileId, projectId });
    app.use(pinia);
    app.use(i18n);
    app.mount("#transcript-container");
});
