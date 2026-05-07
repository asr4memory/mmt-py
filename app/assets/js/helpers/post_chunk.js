import getCookie from "./get_cookie.js";

export default async function postChunk(fileId, index, blob, checksum, signal) {
    const csrftoken = getCookie(document.cookie, "csrftoken");
    const formData = new FormData();
    formData.append("file", blob);
    formData.append("checksum", checksum);

    const response = await fetch(`/uploaded-files/${fileId}/upload/${index}/`, {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRFToken": csrftoken },
        body: formData,
        signal,
    });

    if (!response.ok) {
        throw new Error(`Chunk upload failed: ${response.statusText}`);
    }

    return response.json();
}
