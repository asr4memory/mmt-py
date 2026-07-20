import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createI18n } from "vue-i18n";

import ChunkedUploadQueue from "./chunked_upload_queue.vue";
import registerUpload from "./register_upload.js";
import fetchResumableUploads from "./fetch_resumable_uploads";
import uploadChunks from "./upload_chunks";
import type { UploadChunksOptions } from "./upload_chunks";
import computeChecksum from "./compute_checksum";
import submitChecksum from "./submit_checksum";
import type {
    ResumableMatch,
    ResumableUploadsResult,
    ServerResult,
} from "./types";
import en from "../locales/en.js";
import de from "../locales/de.js";

const i18n = createI18n({ legacy: false, locale: "en", messages: { en, de } });

vi.mock("./register_upload.js", () => ({ default: vi.fn() }));
vi.mock("./fetch_resumable_uploads", () => ({ default: vi.fn() }));
vi.mock("./upload_chunks", () => ({ default: vi.fn() }));
vi.mock("./compute_checksum", () => ({
    default: vi.fn().mockResolvedValue("abc123"),
}));
vi.mock("./submit_checksum", () => ({
    default: vi.fn().mockResolvedValue(null),
}));

function makeFile(name = "test.mp4", size = 7) {
    return new File([new Uint8Array(size)], name);
}

function makeServerResult(overrides: Partial<ServerResult> = {}): ServerResult {
    return { id: 1, filename: "server.mp4", ...overrides };
}

function makeMatch(overrides: Partial<ResumableMatch> = {}): ResumableMatch {
    return {
        filename: "test.mp4",
        size: 7,
        id: 1,
        chunks_missing: [0],
        checksum_submitted: false,
        ...overrides,
    };
}

function mockResumable(matches: ResumableMatch[]) {
    const result: ResumableUploadsResult = { matches };
    vi.mocked(fetchResumableUploads).mockResolvedValue(result);
}

function mountComponent(files: File[], projectId = 1, chunkSize = 5242880) {
    return mount(ChunkedUploadQueue, {
        props: { files, projectId, chunkSize },
        global: { plugins: [i18n] },
    });
}

describe("ChunkedUploadQueue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockResumable([]);
        vi.stubGlobal("location", { href: "" });
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.useRealTimers();
    });

    describe("initial state", () => {
        test("first file starts uploading once the resumable lookup resolves", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockImplementation(
                () => new Promise<void>(() => {}),
            );

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);

            expect(wrapper.vm.uploads[0].status).toBe("pending");

            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("uploading");
        });

        test("remaining files stay pending while the first uploads", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockImplementation(
                () => new Promise<void>(() => {}),
            );

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
                makeFile("c.mp4"),
            ]);
            await flushPromises();

            expect(wrapper.vm.uploads[1].status).toBe("pending");
            expect(wrapper.vm.uploads[2].status).toBe("pending");
        });
    });

    describe("upload coordination", () => {
        test("registers upload with the correct file and projectId", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();

            const file = makeFile("video.mp4");
            mountComponent([file], 7);
            await flushPromises();

            expect(registerUpload).toHaveBeenCalledWith(file, 7);
        });

        test("calls uploadChunks with fileId from server", async () => {
            vi.mocked(registerUpload).mockResolvedValue(
                makeServerResult({ id: 99 }),
            );
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent([makeFile()]);
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ fileId: 99 }),
            );
        });

        test("calls uploadChunks with chunkSize from the prop", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent([makeFile()], 1, 1048576);
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ chunkSize: 1048576 }),
            );
        });

        test("transferred reaches file size when upload completes", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            const file = makeFile();
            vi.mocked(uploadChunks).mockImplementation(
                ({ onProgress }: UploadChunksOptions) => {
                    onProgress?.(file.size);
                    return Promise.resolve();
                },
            );

            const wrapper = mountComponent([file]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].transferred).toBe(file.size);
        });

        test("file becomes uploaded when uploadChunks resolves", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("uploaded");
        });

        test("next file starts uploading when current one completes", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            let resolveFirst: () => void;
            vi.mocked(uploadChunks)
                .mockImplementationOnce(
                    () =>
                        new Promise<void>((resolve) => {
                            resolveFirst = resolve;
                        }),
                )
                .mockImplementation(() => new Promise<void>(() => {}));

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("uploading");
            expect(wrapper.vm.uploads[1].status).toBe("pending");

            resolveFirst!();
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("uploaded");
            expect(wrapper.vm.uploads[1].status).toBe("uploading");
        });

        test("redirects to the file page when a single file is uploaded", async () => {
            vi.useFakeTimers();
            vi.mocked(registerUpload).mockResolvedValue(
                makeServerResult({ id: 7 }),
            );
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent([makeFile()], 42);
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/uploaded-files/7/");
        });

        test("redirects to the project page when several files are uploaded", async () => {
            vi.useFakeTimers();
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent([makeFile("a.mp4"), makeFile("b.mp4")], 42);
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/projects/42/");
        });
    });

    describe("cancellation", () => {
        function makeCancellableMock() {
            return ({ signal }: UploadChunksOptions): Promise<void> =>
                new Promise((_, reject) => {
                    signal!.addEventListener("abort", () => {
                        reject(new DOMException("Aborted", "AbortError"));
                    });
                });
        }

        test("marks active upload as cancelled", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockImplementation(makeCancellableMock());

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            wrapper.vm.cancelActive();
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("cancelled");
        });

        test("starts next file after active upload is cancelled", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks)
                .mockImplementationOnce(makeCancellableMock())
                .mockImplementation(() => new Promise<void>(() => {}));

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);
            await flushPromises();

            wrapper.vm.cancelActive();
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("cancelled");
            expect(wrapper.vm.uploads[1].status).toBe("uploading");
        });

        test("removes a pending upload from the list", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockImplementation(
                () => new Promise<void>(() => {}),
            );

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);
            await flushPromises();

            const pendingId = wrapper.vm.uploads[1].id;
            wrapper.vm.cancelPending(pendingId!);

            expect(wrapper.vm.uploads).toHaveLength(1);
            expect(wrapper.vm.uploads[0].status).toBe("uploading");
        });
    });

    describe("currentUploadNumber", () => {
        test("returns 1-based index of the uploading file", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockImplementation(
                () => new Promise<void>(() => {}),
            );

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);
            await flushPromises();

            expect(wrapper.vm.currentUploadNumber).toBe(1);
        });

        test("returns null when no file is uploading", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            expect(wrapper.vm.currentUploadNumber).toBeNull();
        });
    });

    describe("overallProgress", () => {
        function makeCancellableMock() {
            return ({ signal }: UploadChunksOptions): Promise<void> =>
                new Promise((_, reject) => {
                    signal!.addEventListener("abort", () => {
                        reject(new DOMException("Aborted", "AbortError"));
                    });
                });
        }

        test("is byte-weighted across files", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            let resolveFirst: () => void;
            vi.mocked(uploadChunks)
                .mockImplementationOnce(
                    () =>
                        new Promise<void>((resolve) => {
                            resolveFirst = resolve;
                        }),
                )
                .mockImplementation(() => new Promise<void>(() => {}));

            const wrapper = mountComponent([
                makeFile("a.mp4", 30),
                makeFile("b.mp4", 10),
            ]);
            await flushPromises();
            resolveFirst!();
            await flushPromises();

            // First file (30 bytes) uploaded, second (10 bytes) uploading at 0
            // → 30 / 40.
            expect(wrapper.vm.overallProgress).toBe(75);
        });

        test("reflects partial transfer of the active file", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockImplementation(
                ({ onProgress }: UploadChunksOptions) => {
                    onProgress?.(5);
                    return new Promise<void>(() => {});
                },
            );

            const wrapper = mountComponent([makeFile("a.mp4", 10)]);
            await flushPromises();

            expect(wrapper.vm.overallProgress).toBe(50);
        });

        test("counts cancelled uploads as fully transferred", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks)
                .mockImplementationOnce(makeCancellableMock())
                .mockImplementation(() => new Promise<void>(() => {}));

            const wrapper = mountComponent([
                makeFile("a.mp4", 10),
                makeFile("b.mp4", 10),
            ]);
            await flushPromises();

            wrapper.vm.cancelActive();
            await flushPromises();

            // First file cancelled (counts as 10), second uploading at 0
            // → 10 / 20.
            expect(wrapper.vm.uploads[0].status).toBe("cancelled");
            expect(wrapper.vm.overallProgress).toBe(50);
        });

        test("counts incomplete uploads as fully transferred", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockRejectedValue(
                new Error("Network error"),
            );

            const wrapper = mountComponent([makeFile("a.mp4", 10)]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("incomplete");
            expect(wrapper.vm.overallProgress).toBe(100);
        });
    });

    describe("tab title", () => {
        test("shows overall progress while uploading", async () => {
            document.title = "MMT";
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockImplementation(
                () => new Promise<void>(() => {}),
            );

            mountComponent([makeFile("a.mp4", 10), makeFile("b.mp4", 10)]);
            await flushPromises();

            expect(document.title).toBe("↑ 0% · 1/2");
        });

        test("restores the original title when uploads finish", async () => {
            document.title = "MMT";
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent([makeFile("a.mp4", 10)]);
            await flushPromises();

            expect(document.title).toBe("MMT");
        });

        test("restores the original title on unmount", async () => {
            document.title = "MMT";
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockImplementation(
                () => new Promise<void>(() => {}),
            );

            const wrapper = mountComponent([makeFile("a.mp4", 10)]);
            await flushPromises();

            expect(document.title).not.toBe("MMT");

            wrapper.unmount();

            expect(document.title).toBe("MMT");
        });
    });

    describe("resuming", () => {
        test("resumed file skips registration and uploads only missing chunks", async () => {
            vi.mocked(uploadChunks).mockResolvedValue();
            mockResumable([
                makeMatch({
                    filename: "a.mp4",
                    size: 12,
                    id: 55,
                    chunks_missing: [2],
                }),
            ]);

            mountComponent([makeFile("a.mp4", 12)], 1, 5);
            await flushPromises();

            expect(registerUpload).not.toHaveBeenCalled();
            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({
                    fileId: 55,
                    chunkSize: 5,
                    chunksToUpload: [2],
                }),
            );
        });

        test("pre-fills transferred bytes before a resumed file starts", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            // The first file uploads indefinitely so the second stays pending.
            vi.mocked(uploadChunks).mockImplementation(
                () => new Promise<void>(() => {}),
            );
            // 12-byte file, 5-byte chunks: indices 0, 1 (5 bytes) and 2 (2 bytes).
            // Chunk 2 is still missing, so 10 bytes are already on the server.
            mockResumable([
                makeMatch({
                    filename: "b.mp4",
                    size: 12,
                    chunks_missing: [2],
                }),
            ]);

            const wrapper = mountComponent(
                [makeFile("a.mp4", 12), makeFile("b.mp4", 12)],
                1,
                5,
            );
            await flushPromises();

            expect(wrapper.vm.uploads[1].status).toBe("pending");
            expect(wrapper.vm.uploads[1].transferred).toBe(10);
        });

        test("skips the checksum when it was already submitted", async () => {
            vi.mocked(uploadChunks).mockResolvedValue();
            mockResumable([
                makeMatch({
                    filename: "a.mp4",
                    size: 7,
                    checksum_submitted: true,
                }),
            ]);

            mountComponent([makeFile("a.mp4", 7)]);
            await flushPromises();

            expect(computeChecksum).not.toHaveBeenCalled();
            expect(submitChecksum).not.toHaveBeenCalled();
        });

        test("only the first of two identical selections resumes", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();
            mockResumable([makeMatch({ filename: "a.mp4", size: 7, id: 88 })]);

            mountComponent([makeFile("a.mp4", 7), makeFile("a.mp4", 7)]);
            await flushPromises();

            // The first file resumes onto id 88; the second has no match left
            // and is registered as a new upload.
            expect(registerUpload).toHaveBeenCalledTimes(1);
            expect(registerUpload).toHaveBeenCalledWith(
                expect.objectContaining({ name: "a.mp4" }),
                1,
            );
        });
    });

    describe("error handling", () => {
        test("marks file as incomplete when uploadChunks rejects", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockRejectedValue(
                new Error("Network error"),
            );

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("incomplete");
        });

        test("starts next file after an upload error", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks)
                .mockRejectedValueOnce(new Error("Network error"))
                .mockImplementation(() => new Promise<void>(() => {}));

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("incomplete");
            expect(wrapper.vm.uploads[1].status).toBe("uploading");
        });
    });
});
