import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import ChunkedUploadQueue from "./chunked_upload_queue.js";
import registerUpload from "../helpers/register_upload.js";
import uploadChunks from "../helpers/upload_chunks.js";

vi.mock("../helpers/register_upload.js", () => ({ default: vi.fn() }));
vi.mock("../helpers/upload_chunks.js", () => ({ default: vi.fn() }));

function makeFile(name = "test.mp4") {
    return new File(["content"], name);
}

function makeServerResult(overrides = {}) {
    return { id: 1, filename: "server.mp4", chunk_size: 5242880, ...overrides };
}

function mountComponent(files, projectId = 1) {
    return mount(ChunkedUploadQueue, {
        props: { files, projectId },
        global: {
            mocks: { $t: (key) => key, $i18n: { locale: "en" } },
        },
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
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockResolvedValue();

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);

            expect(wrapper.vm.uploads[0].status).toBe("uploading");
        });

        test("remaining files are pending on mount", () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockResolvedValue();

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
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockResolvedValue();

            const file = makeFile("video.mp4");
            mountComponent([file], 7);
            await flushPromises();

            expect(registerUpload).toHaveBeenCalledWith(file, 7);
        });

        test("calls uploadChunks with fileId from server", async () => {
            registerUpload.mockResolvedValue(makeServerResult({ id: 99 }));
            uploadChunks.mockResolvedValue();

            mountComponent([makeFile()]);
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ fileId: 99 }),
            );
        });

        test("calls uploadChunks with chunk_size from server", async () => {
            registerUpload.mockResolvedValue(
                makeServerResult({ chunk_size: 1048576 }),
            );
            uploadChunks.mockResolvedValue();

            mountComponent([makeFile()]);
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ chunkSize: 1048576 }),
            );
        });

        test("progress reaches 1 when upload completes", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockImplementation(({ onProgress }) => {
                onProgress(1);
                return Promise.resolve();
            });

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].progress).toBe(1);
        });

        test("file becomes uploaded when uploadChunks resolves", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockResolvedValue();

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("uploaded");
        });

        test("next file starts uploading when current one completes", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            let resolveFirst;
            uploadChunks
                .mockImplementationOnce(
                    () =>
                        new Promise((resolve) => {
                            resolveFirst = resolve;
                        }),
                )
                .mockImplementation(() => new Promise(() => {}));

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("uploading");
            expect(wrapper.vm.uploads[1].status).toBe("pending");

            resolveFirst();
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("uploaded");
            expect(wrapper.vm.uploads[1].status).toBe("uploading");
        });

        test("redirects to project page after all files are uploaded", async () => {
            vi.useFakeTimers();
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockResolvedValue();

            mountComponent([makeFile()], 42);
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/projects/42/");
        });
    });

    describe("cancellation", () => {
        function makeCancellableMock() {
            return ({ signal }) =>
                new Promise((_, reject) => {
                    signal.addEventListener("abort", () => {
                        reject(new DOMException("Aborted", "AbortError"));
                    });
                });
        }

        test("marks active upload as cancelled", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockImplementation(makeCancellableMock());

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            wrapper.vm.cancelActive();
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("cancelled");
        });

        test("starts next file after active upload is cancelled", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks
                .mockImplementationOnce(makeCancellableMock())
                .mockImplementation(() => new Promise(() => {}));

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
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockImplementation(() => new Promise(() => {}));

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);
            await flushPromises();

            const pendingId = wrapper.vm.uploads[1].id;
            wrapper.vm.cancelPending(pendingId);

            expect(wrapper.vm.uploads).toHaveLength(1);
            expect(wrapper.vm.uploads[0].status).toBe("uploading");
        });
    });

    describe("currentUploadNumber", () => {
        test("returns 1-based index of the uploading file", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockImplementation(() => new Promise(() => {}));

            const wrapper = mountComponent([
                makeFile("a.mp4"),
                makeFile("b.mp4"),
            ]);
            await flushPromises();

            expect(wrapper.vm.currentUploadNumber).toBe(1);
        });

        test("returns null when no file is uploading", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockResolvedValue();

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            expect(wrapper.vm.currentUploadNumber).toBeNull();
        });
    });

    describe("error handling", () => {
        test("marks file as incomplete when uploadChunks rejects", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks.mockRejectedValue(new Error("Network error"));

            const wrapper = mountComponent([makeFile()]);
            await flushPromises();

            expect(wrapper.vm.uploads[0].status).toBe("incomplete");
        });

        test("starts next file after an upload error", async () => {
            registerUpload.mockResolvedValue(makeServerResult());
            uploadChunks
                .mockRejectedValueOnce(new Error("Network error"))
                .mockImplementation(() => new Promise(() => {}));

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
