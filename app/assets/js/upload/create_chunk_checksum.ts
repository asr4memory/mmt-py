import { createMD5 } from "hash-wasm";

export default async function createChunkChecksum(blob: Blob): Promise<string> {
    const hasher = await createMD5();
    const buffer = await blob.arrayBuffer();
    hasher.update(new Uint8Array(buffer));
    return hasher.digest();
}
