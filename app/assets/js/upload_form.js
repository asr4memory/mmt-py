import "vite/modulepreload-polyfill";
import { createApp } from "vue/dist/vue.esm-bundler";

import UploadQueueStarter from "./components/upload_queue_starter.js";
import i18n from "./i18n.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-job-form");

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = event.target;
        const elements = form.elements;

        const fileInput = elements[1];
        const titleInput = elements[2];
        const descriptionElem = elements[3];
        const languageInput = elements[4];
        const makeAvailableOnPlatformCheckbox = elements[5];
        const transcribeCheckbox = elements[6];
        const checkMediaFilesCheckbox = elements[7];
        const replaceExistingFilesCheckbox = elements[8];

        const files = [...fileInput.files];
        const title = titleInput.value.trim();
        const description = descriptionElem.value.trim();
        const language = languageInput.value.trim();
        const makeAvailableOnPlatform = makeAvailableOnPlatformCheckbox.checked;
        const transcribe = transcribeCheckbox.checked;
        const checkMediaFiles = checkMediaFilesCheckbox.checked;
        const replaceExistingFiles = replaceExistingFilesCheckbox.checked;

        const app = createApp(UploadQueueStarter, {
            files,
            title,
            description,
            language,
            makeAvailableOnPlatform,
            transcribe,
            checkMediaFiles,
            replaceExistingFiles,
        });
        app.use(i18n);
        app.mount("#upload-job-form");
    });
});
