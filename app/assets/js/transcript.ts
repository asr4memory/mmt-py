import { createPinia } from "pinia";
import { createApp } from "vue";

import i18n from "./i18n";
import { readInt, readString } from "./read_dataset.js";
import TranscriptTable from "./transcript/transcript_table.vue";

document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("transcript-container");
    if (!container) return;

    const pinia = createPinia();
    const app = createApp(TranscriptTable, {
        id: readInt(container, "id"),
        initialLabel: readString(container, "label"),
        mediaType: readString(container, "mediaType"),
        uploadedFile: readString(container, "uploadedFile"),
        uploadedFileId: readInt(container, "uploadedFileId"),
        mediaUrl: readString(container, "mediaUrl"),
        projectId: readInt(container, "projectId"),
    });
    app.use(pinia);
    app.use(i18n);
    app.mount("#transcript-container");
});
