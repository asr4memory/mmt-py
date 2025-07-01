import { createMD5 } from "hash-wasm";

const CHUNK_SIZE = 64 * 1024 * 1024;
const fileReader = new FileReader();

function hashChunk(hasher, chunk) {
    return new Promise((resolve, reject) => {
        fileReader.onload = async (event) => {
            const result = fileReader.result;
            const view = new Uint8Array(result);
            hasher.update(view);
            resolve();
        };

        fileReader.readAsArrayBuffer(chunk);
    });
}

const readFile = async (file, progressCallback) => {
    const hasher = await createMD5();

    const numChunks = Math.ceil(file.size / CHUNK_SIZE);

    for (let i = 0; i < numChunks; i += 1) {
        const chunk = file.slice(CHUNK_SIZE * i, Math.min(CHUNK_SIZE * (i + 1), file.size));
        await hashChunk(hasher, chunk);

        const progress = i / numChunks;

        progressCallback(progress);
    }

    const hash = hasher.digest();
    return Promise.resolve(hash);
};

export default async function createChecksum(file, progressCallback) {
    const hash = await readFile(file, progressCallback);
    return Promise.resolve(hash);
}
