import { createApp } from "vue";

import UploadQueueStarter from "./upload/upload_queue_starter.js";
import i18n from "./i18n";
import { readBool, readInt } from "./read_dataset.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form") as HTMLFormElement | null;
    if (!form) return;

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const app = createApp(UploadQueueStarter, {
            projectId: readInt(form, "projectId"),
            chunkedUpload: readBool(form, "chunkedUpload"),
            files: getFilesFromForm(form),
        });
        app.use(i18n);
        app.mount("#upload-form");
    });

    const submitButton = document.getElementById("upload-form-submit");
    submitButton?.removeAttribute("disabled");
});

function getFilesFromForm(form: HTMLFormElement): File[] {
    const fileInput = form.querySelector<HTMLInputElement>('input[type="file"]');
    return [...(fileInput?.files ?? [])];
}
