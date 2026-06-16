import { createApp } from "vue";
import { createPinia } from "pinia";

import TranscriptTable from "./transcript/transcript_table.vue";
import i18n from "./i18n.js";
import { readInt, readString } from "./read_dataset.js";

document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("transcript-container");
    if (!container) return;

    const pinia = createPinia();
    const app = createApp(TranscriptTable, {
        id: readInt(container, "id"),
        label: readString(container, "label"),
        mediaType: readString(container, "mediaType"),
        duration: readString(container, "duration"),
        language: readString(container, "language"),
        uploadedFile: readString(container, "uploadedFile"),
        uploadedFileId: readInt(container, "uploadedFileId"),
        projectId: readInt(container, "projectId"),
    });
    app.use(pinia);
    app.use(i18n);
    app.mount("#transcript-container");
});
