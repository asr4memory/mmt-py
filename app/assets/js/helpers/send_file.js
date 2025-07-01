import { CHUNK_SIZE } from "../components/constants.js";
import sendChunk from "./send_chunk.js";

export default async function sendFile(uploadedFileId, file, updateCallback) {
    const size = file.size;
    const chunkCount = Math.ceil(size / CHUNK_SIZE);

    for (let i = 0; i < chunkCount; i++) {
        const chunk = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE, file.type);
        await sendChunk(uploadedFileId, i, chunk);
        updateCallback((i + 1) * CHUNK_SIZE);
    }
}
