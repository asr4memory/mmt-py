import { createMD5 } from "hash-wasm";

const READ_CHUNK_SIZE = 64 * 1024 * 1024;

export default async function computeChecksum(
    file: File,
    signal?: AbortSignal,
): Promise<string> {
    const hasher = await createMD5();
    const numChunks = Math.ceil(file.size / READ_CHUNK_SIZE);

    for (let i = 0; i < numChunks; i++) {
        if (signal?.aborted) {
            throw new DOMException("Aborted", "AbortError");
        }
        const chunk = file.slice(
            READ_CHUNK_SIZE * i,
            Math.min(READ_CHUNK_SIZE * (i + 1), file.size),
        );
        const buffer = await chunk.arrayBuffer();
        hasher.update(new Uint8Array(buffer));
    }

    return hasher.digest();
}
