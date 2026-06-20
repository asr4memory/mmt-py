import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createI18n } from "vue-i18n";

import ChunkedUploadQueue from "./chunked_upload_queue.vue";
import registerUpload from "./register_upload.js";
import uploadChunks from "./upload_chunks";
import type { UploadChunksOptions } from "./upload_chunks";
import computeChecksum from "./compute_checksum";
import submitChecksum from "./submit_checksum";
import type { ServerResult } from "./types";
import en from "../locales/en.js";
import de from "../locales/de.js";

const i18n = createI18n({ legacy: false, locale: "en", messages: { en, de } });

vi.mock("./register_upload.js", () => ({ default: vi.fn() }));
vi.mock("./upload_chunks", () => ({ default: vi.fn() }));
vi.mock("./compute_checksum", () => ({ default: vi.fn().mockResolvedValue("abc123") }));
vi.mock("./submit_checksum", () => ({ default: vi.fn().mockResolvedValue(null) }));

function makeFile(name = "test.mp4") {
    return new File(["content"], name);
}

function makeServerResult(overrides: Partial<ServerResult> = {}): ServerResult {
    return { id: 1, filename: "server.mp4", chunk_size: 5242880, ...overrides };
}

function mountComponent(files: File[], projectId = 1) {
    return mount(ChunkedUploadQueue, {
        props: { files, projectId },
        global: { plugins: [i18n] },
    });
}

describe("ChunkedUploadQueue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.stubGlobal("location", { href: "" });
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.useRealTimers();
    });

    describe("initial state", () => {
        test("first file is uploading immediately on mount", () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);

            expect(wrapper.vm.uploads[0].status).toBe("uploading");
        });

        test("remaining files are pending on mount", () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockResolvedValue();

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
                makeFile("c.mp4"),
            ]);

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
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult({ id: 99 }));
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent([makeFile()]);
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ fileId: 99 }),
            );
        });

        test("calls uploadChunks with chunk_size from server", async () => {
            vi.mocked(registerUpload).mockResolvedValue(
                makeServerResult({ chunk_size: 1048576 }),
            );
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent([makeFile()]);
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ chunkSize: 1048576 }),
            );
        });

        test("transferred reaches file size when upload completes", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            const file = makeFile();
            vi.mocked(uploadChunks).mockImplementation(({ onProgress }: UploadChunksOptions) => {
                onProgress?.(file.size);
                return Promise.resolve();
            });

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
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult({ id: 7 }));
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
            vi.mocked(uploadChunks).mockImplementation(() => new Promise<void>(() => {}));

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
            vi.mocked(uploadChunks).mockImplementation(() => new Promise<void>(() => {}));

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

    describe("error handling", () => {
        test("marks file as incomplete when uploadChunks rejects", async () => {
            vi.mocked(registerUpload).mockResolvedValue(makeServerResult());
            vi.mocked(uploadChunks).mockRejectedValue(new Error("Network error"));

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
