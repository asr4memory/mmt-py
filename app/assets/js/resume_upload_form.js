import "vite/modulepreload-polyfill";
import { createApp } from "vue/dist/vue.esm-bundler";

import ResumeUpload from "./components/resume_upload.js";
import i18n from "./i18n.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("resume-upload-form");
    if (!form) return;
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = event.target;
        const app = createApp(ResumeUpload, {
            fileId: getFileIdFromForm(form),
            chunkSize: getChunkSizeFromForm(form),
            chunksMissing: getChunksMissingFromForm(form),
            file: getFileFromForm(form),
        });
        app.use(i18n);
        app.mount("#resume-upload-form");
    });

    const submitButton = document.getElementById("resume-upload-form-submit");
    submitButton.removeAttribute("disabled");
});

function getFileIdFromForm(form) {
    return Number.parseInt(form.dataset.fileId, 10);
}

function getChunkSizeFromForm(form) {
    return Number.parseInt(form.dataset.chunkSize, 10);
}

function getChunksMissingFromForm(form) {
    return form.dataset.chunksMissing.split(',').map((chunk) => Number.parseInt(chunk, 10));
}

function getFileFromForm(form) {
    const fileInput = form.querySelector('input[type="file"]');
    return fileInput.files.item(0);
}
