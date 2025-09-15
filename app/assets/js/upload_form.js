import "vite/modulepreload-polyfill";
import { createApp } from "vue/dist/vue.esm-bundler";

import UploadQueueStarter from "./components/upload_queue_starter.js";
import i18n from "./i18n.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form");

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = event.target;
        const app = createApp(UploadQueueStarter, {
            projectId: getProjectIdFromForm(form),
            files: getFilesFromForm(form),
        });
        app.use(i18n);
        app.mount("#upload-form");
    });
});

function getProjectIdFromForm(form) {
    return Number.parseInt(form.dataset.projectId, 10);
}

function getFilesFromForm(form) {
    const elements = form.elements;
    const fileInput = elements[1];
    const files = [...fileInput.files];
    return files;
}
