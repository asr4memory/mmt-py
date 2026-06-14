import postChunk from "./post_chunk";

const CONCURRENCY_LIMIT = 3;

interface Chunk {
    index: number;
    blob: Blob;
}

export interface UploadChunksOptions {
    fileId: number;
    file: Blob;
    chunkSize: number;
    signal?: AbortSignal;
    onProgress?: (transferred: number) => void;
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
    const pendingBytes = pending.reduce((sum, { blob }) => sum + blob.size, 0);

    // Total transferred is the bytes of fully-settled chunks plus the live
    // progress of the chunks currently in flight (up to CONCURRENCY_LIMIT).
    let completedBytes = file.size - pendingBytes;
    const inFlight = new Map<number, number>();

    function report() {
        let live = 0;
        for (const loaded of inFlight.values()) live += loaded;
        onProgress?.(completedBytes + live);
    }

    if (completedBytes > 0) report();

    await runWithConcurrency(
        pending,
        CONCURRENCY_LIMIT,
        async ({ index, blob }) => {
            inFlight.set(index, 0);
            const result = await postChunk(
                fileId,
                index,
                blob,
                signal,
                (loaded) => {
                    // The multipart body is slightly larger than the blob, so
                    // clamp to avoid reporting more than the chunk's size.
                    inFlight.set(index, Math.min(loaded, blob.size));
                    report();
                },
            );
            inFlight.delete(index);
            completedBytes += blob.size;
            report();
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
