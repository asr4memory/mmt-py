import { createApp } from "vue";

import ResumeUpload from "./upload/resume_upload.js";
import i18n from "./i18n.js";
import { readBool, readInt, readIntList } from "./read_dataset.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("resume-upload-form") as HTMLFormElement | null;
    if (!form) return;

    const submitButton = document.getElementById("resume-upload-form-submit");
    if (!submitButton) return;
    submitButton.removeAttribute("disabled");

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const file = getFileFromForm(form);
        if (!file) return;
        const app = createApp(ResumeUpload, {
            fileId: readInt(form, "fileId"),
            chunkSize: readInt(form, "chunkSize"),
            chunksMissing: readIntList(form, "chunksMissing"),
            file,
            checksumSubmitted: readBool(form, "checksumSubmitted"),
        });
        app.use(i18n);
        app.mount(form);
    });
});

function getFileFromForm(form: HTMLFormElement): File | null {
    const fileInput = form.querySelector<HTMLInputElement>('input[type="file"]');
    return fileInput?.files?.item(0) ?? null;
}
