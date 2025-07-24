import "vite/modulepreload-polyfill";
import { createApp } from "vue/dist/vue.esm-bundler";

import UploadQueueStarter from "./components/upload_queue_starter.js";
import i18n from "./i18n.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form");

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = event.target;
        const projectId = Number.parseInt(form.dataset.projectId)
        const elements = form.elements;
        const fileInput = elements[1];
        const files = [...fileInput.files];

        const app = createApp(UploadQueueStarter, {
            projectId,
            files,
        });
        app.use(i18n);
        app.mount("#upload-form");
    });
});
