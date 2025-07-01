import { CHUNK_SIZE } from "../components/constants.js";
import getCookie from "./get_cookie.js";

const csrftoken = getCookie("csrftoken");
const locale = document.documentElement.lang;

export default async function sendChunk(uploadedFileId, file, chunkNumber) {
    const uploadChunkEndPoint = `/${locale}/uploaded-files/${uploadedFileId}/upload-chunk/${chunkNumber}/`;

    const chunk = file.slice(chunkNumber * CHUNK_SIZE, (chunkNumber + 1) * CHUNK_SIZE, file.type);

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
