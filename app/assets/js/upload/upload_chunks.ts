import createChunkChecksum from "./create_chunk_checksum";
import postChunk from "./post_chunk";

const CONCURRENCY_LIMIT = 4;

interface Chunk {
    index: number;
    blob: Blob;
}

export interface UploadChunksOptions {
    fileId: number;
    file: Blob;
    chunkSize: number;
    signal?: AbortSignal;
    onProgress?: (progress: number) => void;
    chunksToUpload?: number[];
}

export default async function uploadChunks({
    fileId,
    file,
    chunkSize,
    signal,
    onProgress,
    chunksToUpload,
}: UploadChunksOptions): Promise<void> {
    const allChunks = splitIntoChunks(file, chunkSize);
    const pending = chunksToUpload
        ? allChunks.filter(({ index }) => chunksToUpload.includes(index))
        : allChunks;
    let completed = allChunks.length - pending.length;
    if (completed > 0) onProgress?.(completed / allChunks.length);
    await runWithConcurrency(
        pending,
        CONCURRENCY_LIMIT,
        async ({ index, blob }) => {
            const checksum = await createChunkChecksum(blob);
            const result = await postChunk(
                fileId,
                index,
                blob,
                checksum,
                signal,
            );
            onProgress?.(++completed / allChunks.length);
            return result;
        },
    );
}

function splitIntoChunks(file: Blob, chunkSize: number): Chunk[] {
    const chunks: Chunk[] = [];
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

async function runWithConcurrency<T>(
    items: T[],
    limit: number,
    fn: (item: T) => Promise<unknown>,
): Promise<void> {
    const executing = new Set<Promise<unknown>>();
    for (const item of items) {
        const promise = fn(item).finally(() => executing.delete(promise));
        executing.add(promise);
        if (executing.size >= limit) {
            await Promise.race(executing);
        }
    }
    await Promise.all(executing);
}
