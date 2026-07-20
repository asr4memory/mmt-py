import { describe, expect, test } from "vitest";

import { routes } from "./routes";

describe("routes", () => {
    test("builds project routes", () => {
        expect(routes.project(42)).toBe("/projects/42/");
        expect(routes.createFile(42)).toBe("/projects/42/create-file/");
        expect(routes.resumableUploads(42)).toBe(
            "/projects/42/resumable-uploads/",
        );
    });

    test("builds uploaded-file routes", () => {
        expect(routes.uploadedFile(7)).toBe("/uploaded-files/7/");
        expect(routes.uploadedFileStream(7)).toBe("/uploaded-files/7/stream/");
        expect(routes.uploadedFileWaveform(7)).toBe(
            "/uploaded-files/7/waveform/",
        );
        expect(routes.uploadedFileUpdate(7)).toBe("/uploaded-files/7/update/");
        expect(routes.uploadedFileUploadChunk(7, 3)).toBe(
            "/uploaded-files/7/upload/3/",
        );
    });
});
