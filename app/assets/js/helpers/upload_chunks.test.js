import { describe, expect, test, vi, beforeEach } from "vitest";
import uploadChunks from "./upload_chunks.js";
import createChunkChecksum from "./create_chunk_checksum.js";
import postChunk from "./post_chunk.js";

vi.mock("./create_chunk_checksum.js", () => ({ default: vi.fn() }));
vi.mock("./post_chunk.js", () => ({ default: vi.fn() }));

function makeBlob(size) {
    return new Blob([new Uint8Array(size).fill(1)]);
}

describe("uploadChunks", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        createChunkChecksum.mockResolvedValue("mock-checksum");
        postChunk.mockResolvedValue({ complete: true });
    });

    describe("chunk splitting", () => {
        test("uploads one chunk per chunkSize block", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(10), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledTimes(2);
        });

        test("uploads a single chunk when file is smaller than chunkSize", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(3), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledTimes(1);
        });

        test("last chunk covers the remainder when file size is not divisible", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(11), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledTimes(3);
        });
    });

    describe("postChunk arguments", () => {
        test("passes fileId as first argument", async () => {
            await uploadChunks({ fileId: 42, file: makeBlob(5), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledWith(
                42,
                expect.anything(),
                expect.anything(),
                expect.anything(),
                undefined,
            );
        });

        test("passes index 0 for the first chunk", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(5), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledWith(
                expect.anything(),
                0,
                expect.anything(),
                expect.anything(),
                undefined,
            );
        });

        test("passes correct index for subsequent chunks", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(10), chunkSize: 5 });
            expect(postChunk).toHaveBeenNthCalledWith(
                2,
                expect.anything(),
                1,
                expect.anything(),
                expect.anything(),
                undefined,
            );
        });
    });

    describe("checksum", () => {
        test("computes a checksum for each chunk", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(10), chunkSize: 5 });
            expect(createChunkChecksum).toHaveBeenCalledTimes(2);
        });

        test("passes the computed checksum to postChunk", async () => {
            createChunkChecksum.mockResolvedValue("abc123");
            await uploadChunks({ fileId: 1, file: makeBlob(5), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledWith(
                expect.anything(),
                expect.anything(),
                expect.anything(),
                "abc123",
                undefined,
            );
        });
    });

    describe("completion", () => {
        test("resolves when all chunks are posted", async () => {
            await expect(
                uploadChunks({ fileId: 1, file: makeBlob(5), chunkSize: 5 }),
            ).resolves.toBeUndefined();
        });
    });

    describe("concurrency", () => {
        test("does not start more than 4 chunks simultaneously", async () => {
            const CHUNKS = 8;
            const LIMIT = 4;
            let inFlight = 0;
            let maxInFlight = 0;
            let completed = 0;
            const resolvers = [];

            postChunk.mockImplementation(() => {
                inFlight++;
                maxInFlight = Math.max(maxInFlight, inFlight);
                return new Promise((resolve) => {
                    resolvers.push(() => {
                        inFlight--;
                        completed++;
                        resolve({ complete: completed === CHUNKS });
                    });
                });
            });

            const file = makeBlob(CHUNKS * 5);
            const uploadPromise = uploadChunks({
                fileId: 1,
                file,
                chunkSize: 5,
            });

            // Let the event loop run so the initial batch of 4 starts
            await new Promise((r) => setTimeout(r, 0));
            expect(resolvers.length).toBe(LIMIT);

            // Drain the queue one resolver at a time, letting the pool refill
            for (let i = 0; i < CHUNKS; i++) {
                resolvers[i]();
                await new Promise((r) => setTimeout(r, 0));
            }

            await uploadPromise;
            expect(maxInFlight).toBe(LIMIT);
        });
    });

    describe("onProgress", () => {
        test("calls onProgress after each chunk with completed fraction", async () => {
            const onProgress = vi.fn();
            await uploadChunks({
                fileId: 1,
                file: makeBlob(15),
                chunkSize: 5,
                onProgress,
            });
            expect(onProgress).toHaveBeenCalledTimes(3);
            expect(onProgress).toHaveBeenNthCalledWith(1, 1 / 3);
            expect(onProgress).toHaveBeenNthCalledWith(2, 2 / 3);
            expect(onProgress).toHaveBeenNthCalledWith(3, 1);
        });

        test("onProgress is optional", async () => {
            await expect(
                uploadChunks({ fileId: 1, file: makeBlob(5), chunkSize: 5 }),
            ).resolves.toBeUndefined();
        });
    });

    describe("chunksToUpload", () => {
        test("uploads only the specified chunk indices", async () => {
            await uploadChunks({
                fileId: 1,
                file: makeBlob(15),
                chunkSize: 5,
                chunksToUpload: [1],
            });
            expect(postChunk).toHaveBeenCalledTimes(1);
            expect(postChunk).toHaveBeenCalledWith(
                expect.anything(),
                1,
                expect.anything(),
                expect.anything(),
                undefined,
            );
        });

        test("onProgress accounts for already-uploaded chunks", async () => {
            const onProgress = vi.fn();
            await uploadChunks({
                fileId: 1,
                file: makeBlob(15),
                chunkSize: 5,
                onProgress,
                chunksToUpload: [1, 2],
            });
            expect(onProgress).toHaveBeenCalledTimes(2);
            expect(onProgress).toHaveBeenNthCalledWith(1, 2 / 3);
            expect(onProgress).toHaveBeenNthCalledWith(2, 1);
        });

        test("uploads all chunks when chunksToUpload is omitted", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(15), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledTimes(3);
        });
    });

    describe("error handling", () => {
        test("rejects when a chunk POST fails", async () => {
            postChunk.mockRejectedValue(new Error("Network error"));
            await expect(
                uploadChunks({ fileId: 1, file: makeBlob(5), chunkSize: 5 }),
            ).rejects.toThrow("Network error");
        });

        test("rejects when one chunk among several fails", async () => {
            let callCount = 0;
            postChunk.mockImplementation(() => {
                callCount++;
                if (callCount === 2)
                    return Promise.reject(new Error("Network error"));
                return new Promise(() => {});
            });
            await expect(
                uploadChunks({ fileId: 1, file: makeBlob(15), chunkSize: 5 }),
            ).rejects.toThrow("Network error");
        });
    });
});
