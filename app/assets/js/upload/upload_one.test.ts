import { describe, expect, test, vi, beforeEach } from "vitest";

import uploadOne from "./upload_one";
import type { UploadOneArgs } from "./upload_one";
import uploadChunks from "./upload_chunks";
import type { UploadChunksOptions } from "./upload_chunks";
import computeChecksum from "./compute_checksum";
import submitChecksum from "./submit_checksum";

vi.mock("./upload_chunks", () => ({ default: vi.fn() }));
vi.mock("./compute_checksum", () => ({
    default: vi.fn().mockResolvedValue("abc123"),
}));
vi.mock("./submit_checksum", () => ({
    default: vi.fn().mockResolvedValue(null),
}));

function makeFile(size = 10) {
    return new File([new Uint8Array(size)], "test.mp4");
}

function baseArgs(overrides: Partial<UploadOneArgs> = {}): UploadOneArgs {
    return {
        fileId: 1,
        file: makeFile(),
        chunkSize: 5,
        signal: new AbortController().signal,
        onProgress: vi.fn(),
        onChecksumStatus: vi.fn(),
        ...overrides,
    };
}

describe("uploadOne", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    test("passes fileId, file, chunkSize, chunksToUpload and signal to uploadChunks", async () => {
        vi.mocked(uploadChunks).mockResolvedValue();
        const file = makeFile();
        const signal = new AbortController().signal;

        await uploadOne(
            baseArgs({
                fileId: 42,
                file,
                chunkSize: 7,
                chunksToUpload: [1, 2],
                signal,
            }),
        );

        expect(uploadChunks).toHaveBeenCalledWith(
            expect.objectContaining({
                fileId: 42,
                file,
                chunkSize: 7,
                chunksToUpload: [1, 2],
                signal,
            }),
        );
    });

    test("reports transferred bytes via onProgress", async () => {
        vi.mocked(uploadChunks).mockImplementation(
            ({ onProgress }: UploadChunksOptions) => {
                onProgress?.(4);
                return Promise.resolve();
            },
        );
        const onProgress = vi.fn();

        await uploadOne(baseArgs({ onProgress }));

        expect(onProgress).toHaveBeenCalledWith(
            expect.objectContaining({ transferred: 4 }),
        );
    });

    test("computes and submits the checksum when not already submitted", async () => {
        vi.mocked(uploadChunks).mockResolvedValue();
        const onChecksumStatus = vi.fn();

        await uploadOne(
            baseArgs({ fileId: 9, checksumSubmitted: false, onChecksumStatus }),
        );

        expect(computeChecksum).toHaveBeenCalled();
        expect(submitChecksum).toHaveBeenCalledWith(9, "abc123");
        expect(onChecksumStatus.mock.calls.map((call) => call[0])).toEqual([
            "generating",
            "transferring",
            "complete",
        ]);
    });

    test("skips the checksum when it was already submitted", async () => {
        vi.mocked(uploadChunks).mockResolvedValue();
        const onChecksumStatus = vi.fn();

        await uploadOne(
            baseArgs({ checksumSubmitted: true, onChecksumStatus }),
        );

        expect(computeChecksum).not.toHaveBeenCalled();
        expect(submitChecksum).not.toHaveBeenCalled();
        expect(onChecksumStatus).not.toHaveBeenCalled();
    });

    test("rejects when uploadChunks rejects", async () => {
        vi.mocked(uploadChunks).mockRejectedValue(new Error("Network error"));

        await expect(uploadOne(baseArgs())).rejects.toThrow("Network error");
    });
});
