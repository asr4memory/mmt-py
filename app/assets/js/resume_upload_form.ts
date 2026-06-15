import { createApp } from "vue";

import ResumeUpload from "./upload/resume_upload.js";
import i18n from "./i18n.js";
import { readBool, readInt, readIntList, readString } from "./read_dataset.js";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("resume-upload-form") as HTMLFormElement | null;
    if (!form) return;

    const submitButton = document.getElementById("resume-upload-form-submit");
    if (!submitButton) return;

    const feedback = document.getElementById("resume-upload-feedback");
    if (!feedback) return;

    const expectedFilename = readString(form, "filename");
    const expectedFileSize = readInt(form, "fileSize");

    const fileInput = form.querySelector<HTMLInputElement>('input[type="file"]');
    if (!fileInput) return;

    fileInput.addEventListener("change", () => {
        const file = fileInput.files?.item(0) ?? null;
        if (file === null) {
            feedback.textContent = "";
            submitButton.setAttribute("disabled", "");
            return;
        }
        const matches = file.name === expectedFilename && file.size === expectedFileSize;
        feedback.textContent = i18n.global.t(
            matches ? "resume_upload.file_matches" : "resume_upload.file_does_not_match",
        );
        if (matches) {
            submitButton.removeAttribute("disabled");
        } else {
            submitButton.setAttribute("disabled", "");
        }
    });

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
