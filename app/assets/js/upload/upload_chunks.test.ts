import { describe, expect, test, vi, beforeEach } from "vitest";

import uploadChunks from "./upload_chunks";
import postChunk from "./post_chunk";

vi.mock("./post_chunk", () => ({ default: vi.fn() }));

function makeBlob(size: number) {
    return new Blob([new Uint8Array(size).fill(1)]);
}

describe("uploadChunks", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(postChunk).mockResolvedValue({ complete: true });
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
                undefined,
                expect.any(Function),
            );
        });

        test("passes index 0 for the first chunk", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(5), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledWith(
                expect.anything(),
                0,
                expect.anything(),
                undefined,
                expect.any(Function),
            );
        });

        test("passes correct index for subsequent chunks", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(10), chunkSize: 5 });
            expect(postChunk).toHaveBeenNthCalledWith(
                2,
                expect.anything(),
                1,
                expect.anything(),
                undefined,
                expect.any(Function),
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
        test("does not start more than 3 chunks simultaneously", async () => {
            const CHUNKS = 8;
            const LIMIT = 3;
            let inFlight = 0;
            let maxInFlight = 0;
            let completed = 0;
            const resolvers: Array<() => void> = [];

            vi.mocked(postChunk).mockImplementation(() => {
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
            const uploadPromise = uploadChunks({ fileId: 1, file, chunkSize: 5 });

            await new Promise((r) => setTimeout(r, 0));
            expect(resolvers.length).toBe(LIMIT);

            for (let i = 0; i < CHUNKS; i++) {
                resolvers[i]();
                await new Promise((r) => setTimeout(r, 0));
            }

            await uploadPromise;
            expect(maxInFlight).toBe(LIMIT);
        });
    });

    describe("onProgress", () => {
        test("calls onProgress after each chunk with transferred bytes", async () => {
            const onProgress = vi.fn();
            await uploadChunks({
                fileId: 1,
                file: makeBlob(15),
                chunkSize: 5,
                onProgress,
            });
            expect(onProgress).toHaveBeenCalledTimes(3);
            expect(onProgress).toHaveBeenNthCalledWith(1, 5);
            expect(onProgress).toHaveBeenNthCalledWith(2, 10);
            expect(onProgress).toHaveBeenNthCalledWith(3, 15);
        });

        test("reports the smaller final chunk size on the last call", async () => {
            const onProgress = vi.fn();
            await uploadChunks({
                fileId: 1,
                file: makeBlob(11),
                chunkSize: 5,
                onProgress,
            });
            expect(onProgress).toHaveBeenCalledTimes(3);
            expect(onProgress).toHaveBeenNthCalledWith(1, 5);
            expect(onProgress).toHaveBeenNthCalledWith(2, 10);
            expect(onProgress).toHaveBeenNthCalledWith(3, 11);
        });

        test("onProgress is optional", async () => {
            await expect(
                uploadChunks({ fileId: 1, file: makeBlob(5), chunkSize: 5 }),
            ).resolves.toBeUndefined();
        });

        test("aggregates in-flight progress across concurrent chunks", async () => {
            const onProgress = vi.fn();
            const progressCallbacks: Array<(loaded: number) => void> = [];
            const resolvers: Array<() => void> = [];

            vi.mocked(postChunk).mockImplementation(
                (_fileId, _index, _blob, _signal, onChunkProgress) => {
                    progressCallbacks.push(onChunkProgress!);
                    return new Promise((resolve) => {
                        resolvers.push(() => resolve({ complete: false }));
                    });
                },
            );

            const uploadPromise = uploadChunks({
                fileId: 1,
                file: makeBlob(10),
                chunkSize: 5,
                onProgress,
            });

            await new Promise((r) => setTimeout(r, 0));
            expect(progressCallbacks).toHaveLength(2);

            progressCallbacks[0](2);
            expect(onProgress).toHaveBeenLastCalledWith(2);
            progressCallbacks[1](3);
            expect(onProgress).toHaveBeenLastCalledWith(5);
            progressCallbacks[0](5);
            expect(onProgress).toHaveBeenLastCalledWith(8);

            resolvers[0]();
            resolvers[1]();
            await uploadPromise;
            expect(onProgress).toHaveBeenLastCalledWith(10);
        });

        test("clamps reported progress to the chunk size", async () => {
            const onProgress = vi.fn();
            let progressCb!: (loaded: number) => void;
            let resolveChunk!: () => void;

            vi.mocked(postChunk).mockImplementation(
                (_fileId, _index, _blob, _signal, onChunkProgress) => {
                    progressCb = onChunkProgress!;
                    return new Promise((resolve) => {
                        resolveChunk = () => resolve({ complete: true });
                    });
                },
            );

            const uploadPromise = uploadChunks({
                fileId: 1,
                file: makeBlob(5),
                chunkSize: 5,
                onProgress,
            });

            await new Promise((r) => setTimeout(r, 0));
            progressCb(99);
            expect(onProgress).toHaveBeenLastCalledWith(5);

            resolveChunk();
            await uploadPromise;
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
                undefined,
                expect.any(Function),
            );
        });

        test("emits initial transferred bytes for already-uploaded chunks", async () => {
            const onProgress = vi.fn();
            await uploadChunks({
                fileId: 1,
                file: makeBlob(15),
                chunkSize: 5,
                onProgress,
                chunksToUpload: [1, 2],
            });
            expect(onProgress).toHaveBeenNthCalledWith(1, 5);
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
            expect(onProgress).toHaveBeenCalledTimes(3);
            expect(onProgress).toHaveBeenNthCalledWith(1, 5);
            expect(onProgress).toHaveBeenNthCalledWith(2, 10);
            expect(onProgress).toHaveBeenNthCalledWith(3, 15);
        });

        test("uploads all chunks when chunksToUpload is omitted", async () => {
            await uploadChunks({ fileId: 1, file: makeBlob(15), chunkSize: 5 });
            expect(postChunk).toHaveBeenCalledTimes(3);
        });
    });

    describe("error handling", () => {
        test("rejects when a chunk POST fails", async () => {
            vi.mocked(postChunk).mockRejectedValue(new Error("Network error"));
            await expect(
                uploadChunks({ fileId: 1, file: makeBlob(5), chunkSize: 5 }),
            ).rejects.toThrow("Network error");
        });

        test("rejects when one chunk among several fails", async () => {
            let callCount = 0;
            vi.mocked(postChunk).mockImplementation(() => {
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
