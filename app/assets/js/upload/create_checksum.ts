import { createMD5, type IHasher } from "hash-wasm";

const CHUNK_SIZE = 64 * 1024 * 1024;
const fileReader = new FileReader();

function hashChunk(hasher: IHasher, chunk: Blob): Promise<void> {
    return new Promise((resolve) => {
        fileReader.onload = () => {
            const result = fileReader.result as ArrayBuffer;
            const view = new Uint8Array(result);
            hasher.update(view);
            resolve();
        };

        fileReader.readAsArrayBuffer(chunk);
    });
}

const readFile = async (
    file: File,
    progressCallback: (progress: number) => void,
): Promise<string> => {
    const hasher = await createMD5();

    const numChunks = Math.ceil(file.size / CHUNK_SIZE);

    for (let i = 0; i < numChunks; i += 1) {
        const chunk = file.slice(
            CHUNK_SIZE * i,
            Math.min(CHUNK_SIZE * (i + 1), file.size),
        );
        await hashChunk(hasher, chunk);

        const progress = i / numChunks;

        progressCallback(progress);
    }

    return hasher.digest();
};

export default async function createChecksum(
    file: File,
    progressCallback: (progress: number) => void,
): Promise<string> {
    return readFile(file, progressCallback);
}
