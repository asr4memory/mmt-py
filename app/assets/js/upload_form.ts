import { createApp } from "vue";

import ChunkedUploadQueue from "./upload/chunked_upload_queue.vue";
import i18n from "./i18n";
import { readFiles, readInt } from "./read_dataset.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form") as HTMLFormElement | null;
    if (!form) return;

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const app = createApp(ChunkedUploadQueue, {
            projectId: readInt(form, "projectId"),
            chunkSize: readInt(form, "chunkSize"),
            files: readFiles(form),
        });
        app.use(i18n);
        app.mount("#upload-form");
    });

    const submitButton = document.getElementById("upload-form-submit");
    submitButton?.removeAttribute("disabled");
});
