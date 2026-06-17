import { createApp } from "vue";

import UploadQueueStarter from "./upload/upload_queue_starter.js";
import i18n from "./i18n";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form");
    if (!form) return;
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = event.target;
        const app = createApp(UploadQueueStarter, {
            projectId: getProjectIdFromForm(form),
            chunkedUpload: getChunkedUploadFromForm(form),
            files: getFilesFromForm(form),
        });
        app.use(i18n);
        app.mount("#upload-form");
    });

    const submitButton = document.getElementById("upload-form-submit");
    submitButton.removeAttribute("disabled");
});

function getProjectIdFromForm(form) {
    return Number.parseInt(form.dataset.projectId, 10);
}

function getChunkedUploadFromForm(form) {
    return form.dataset.chunkedUpload === "true";
}

function getFilesFromForm(form) {
    const fileInput = form.querySelector('input[type="file"]');
    return [...fileInput.files];
}
