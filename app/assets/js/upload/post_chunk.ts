import getCookie from "../shared/get_cookie.js";

export default function postChunk(
    fileId: number,
    index: number,
    blob: Blob,
    signal?: AbortSignal,
    onProgress?: (loaded: number) => void,
): Promise<unknown> {
    const csrftoken = getCookie(document.cookie, "csrftoken") ?? "";
    const formData = new FormData();
    formData.append("file", blob);

    return new Promise((resolve, reject) => {
        if (signal?.aborted) {
            reject(abortError());
            return;
        }

        const xhr = new XMLHttpRequest();
        xhr.open("POST", `/uploaded-files/${fileId}/upload/${index}/`);
        xhr.withCredentials = true;
        xhr.responseType = "json";
        xhr.setRequestHeader("X-CSRFToken", csrftoken);

        function onAbort() {
            xhr.abort();
        }

        if (onProgress) {
            xhr.upload.addEventListener("progress", (event) => {
                if (event.lengthComputable) onProgress(event.loaded);
            });
        }

        xhr.addEventListener("load", () => {
            signal?.removeEventListener("abort", onAbort);
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(xhr.response);
            } else {
                reject(new Error(`Chunk upload failed: ${xhr.statusText}`));
            }
        });

        xhr.addEventListener("error", () => {
            signal?.removeEventListener("abort", onAbort);
            reject(new Error("Chunk upload failed"));
        });

        xhr.addEventListener("abort", () => {
            signal?.removeEventListener("abort", onAbort);
            reject(abortError());
        });

        signal?.addEventListener("abort", onAbort);
        xhr.send(formData);
    });
}

function abortError(): Error {
    const error = new Error("Aborted");
    error.name = "AbortError";
    return error;
}
