import createChunkChecksum from "./create_chunk_checksum.js";
import postChunk from "./post_chunk.js";

const CONCURRENCY_LIMIT = 4;

export default async function uploadChunks({ fileId, file, chunkSize }) {
    const chunks = splitIntoChunks(file, chunkSize);
    await runWithConcurrency(
        chunks,
        CONCURRENCY_LIMIT,
        async ({ index, blob }) => {
            const checksum = await createChunkChecksum(blob);
            return postChunk(fileId, index, blob, checksum);
        },
    );
}

function splitIntoChunks(file, chunkSize) {
    const chunks = [];
    let start = 0;
    let index = 0;
    while (start < file.size) {
        const end = Math.min(start + chunkSize, file.size);
        chunks.push({ index, blob: file.slice(start, end) });
        start = end;
        index++;
    }
    return chunks;
}

async function runWithConcurrency(items, limit, fn) {
    const executing = new Set();
    for (const item of items) {
        const promise = fn(item).finally(() => executing.delete(promise));
        executing.add(promise);
        if (executing.size >= limit) {
            await Promise.race(executing);
        }
    }
    await Promise.all(executing);
}
