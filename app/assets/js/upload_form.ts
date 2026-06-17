import { createApp } from "vue";

import UploadQueueStarter from "./upload/upload_queue_starter.js";
import i18n from "./i18n";
import { readBool, readFiles, readInt } from "./read_dataset.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form") as HTMLFormElement | null;
    if (!form) return;

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const app = createApp(UploadQueueStarter, {
            projectId: readInt(form, "projectId"),
            chunkedUpload: readBool(form, "chunkedUpload"),
            files: readFiles(form),
        });
        app.use(i18n);
        app.mount("#upload-form");
    });

    const submitButton = document.getElementById("upload-form-submit");
    submitButton?.removeAttribute("disabled");
});
