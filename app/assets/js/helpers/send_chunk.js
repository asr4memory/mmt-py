import getCookie from "./get_cookie.js";

const csrftoken = getCookie("csrftoken");
const locale = document.documentElement.lang;

export default async function sendChunk(uploadedFileId, chunkNumber, chunk) {
    const uploadChunkEndPoint = `/${locale}/uploaded-files/${uploadedFileId}/upload-chunk/${chunkNumber}/`;

    const response = await fetch(uploadChunkEndPoint, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrftoken,
        },
        credentials: "include",
        body: chunk,
    });

    if (!response.ok) {
        throw new Error(`Response status: ${response.status}`);
    }

    const json = await response.json();
    return json;
}
