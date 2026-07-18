import { describe, expect, test } from "vitest";

import applyResumableMatches from "./apply_resumable_matches";
import type { ResumableMatch, ResumableUploadsResult, Upload } from "./types";

function makeUpload(name: string, size: number, id = 0): Upload {
    return {
        id,
        file: new File([new Uint8Array(size)], name),
        status: "pending",
        transferred: 0,
        speed: 0,
        eta: null,
        checksumStatus: "pending",
    };
}

function makeMatch(overrides: Partial<ResumableMatch> = {}): ResumableMatch {
    return {
        filename: "a.mp4",
        size: 12,
        id: 55,
        chunks_missing: [2],
        checksum_submitted: false,
        ...overrides,
    };
}

function makeResult(
    matches: ResumableMatch[],
    chunkSize = 5,
): ResumableUploadsResult {
    return { chunk_size: chunkSize, matches };
}

describe("applyResumableMatches", () => {
    test("applies the match fields to the matching upload", () => {
        const upload = makeUpload("a.mp4", 12);

        applyResumableMatches(
            [upload],
            makeResult([
                makeMatch({ id: 55, chunks_missing: [2], checksum_submitted: true }),
            ]),
        );

        expect(upload.resuming).toBe(true);
        expect(upload.fileId).toBe(55);
        expect(upload.chunksMissing).toEqual([2]);
        expect(upload.checksumSubmitted).toBe(true);
    });

    test("pre-fills transferred with the bytes already on the server", () => {
        // 12-byte file, 5-byte chunks: indices 0, 1 (5 bytes) and 2 (2 bytes).
        // Chunk 2 is missing, so 10 bytes are already on the server.
        const upload = makeUpload("a.mp4", 12);

        applyResumableMatches(
            [upload],
            makeResult([makeMatch({ chunks_missing: [2] })], 5),
        );

        expect(upload.transferred).toBe(10);
    });

    test("counts full chunk size for missing chunks before the last", () => {
        // Chunks 0 and 1 are 5 bytes each; only chunk 1 is missing.
        const upload = makeUpload("a.mp4", 12);

        applyResumableMatches(
            [upload],
            makeResult([makeMatch({ chunks_missing: [1] })], 5),
        );

        expect(upload.transferred).toBe(7);
    });

    test("leaves transferred at zero when the chunk size is zero", () => {
        const upload = makeUpload("a.mp4", 12);

        applyResumableMatches(
            [upload],
            makeResult([makeMatch({ chunks_missing: [] })], 0),
        );

        expect(upload.transferred).toBe(0);
    });

    test("does not touch uploads without a match", () => {
        const upload = makeUpload("b.mp4", 12);

        applyResumableMatches([upload], makeResult([makeMatch()]));

        expect(upload.resuming).toBeUndefined();
        expect(upload.fileId).toBeUndefined();
        expect(upload.transferred).toBe(0);
    });

    test("does not apply a match whose size differs", () => {
        const upload = makeUpload("a.mp4", 13);

        applyResumableMatches([upload], makeResult([makeMatch({ size: 12 })]));

        expect(upload.resuming).toBeUndefined();
    });

    test("applies a match to only the first of two identical uploads", () => {
        const first = makeUpload("a.mp4", 12, 0);
        const second = makeUpload("a.mp4", 12, 1);

        applyResumableMatches([first, second], makeResult([makeMatch()]));

        expect(first.resuming).toBe(true);
        expect(second.resuming).toBeUndefined();
    });
});
