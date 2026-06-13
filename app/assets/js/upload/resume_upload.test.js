import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import ResumeUpload from "./resume_upload.js";
import uploadChunks from "./upload_chunks.js";

vi.mock("./upload_chunks.js", () => ({ default: vi.fn() }));

function makeFile(name = "test.mp4") {
    return new File(["content"], name);
}

function mountComponent(overrides = {}) {
    return mount(ResumeUpload, {
        props: {
            fileId: 1,
            chunkSize: 5242880,
            chunksMissing: [0, 1, 2],
            file: makeFile(),
            ...overrides,
        },
        global: {
            mocks: { $t: (key) => key, $i18n: { locale: "en" } },
        },
    });
}

function makeCancellableMock() {
    return ({ signal }) =>
        new Promise((_, reject) => {
            signal.addEventListener("abort", () => {
                reject(new DOMException("Aborted", "AbortError"));
            });
        });
}

describe("ResumeUpload", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.stubGlobal("location", { href: "" });
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.useRealTimers();
    });

    describe("initial state", () => {
        test("status is uploading immediately on mount", () => {
            uploadChunks.mockResolvedValue();

            const wrapper = mountComponent();

            expect(wrapper.vm.status).toBe("uploading");
        });
    });

    describe("uploadChunks call", () => {
        test("calls uploadChunks with fileId prop", async () => {
            uploadChunks.mockResolvedValue();

            mountComponent({ fileId: 42 });
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ fileId: 42 }),
            );
        });

        test("calls uploadChunks with chunkSize prop", async () => {
            uploadChunks.mockResolvedValue();

            mountComponent({ chunkSize: 1048576 });
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ chunkSize: 1048576 }),
            );
        });

        test("calls uploadChunks with file prop", async () => {
            uploadChunks.mockResolvedValue();

            const file = makeFile("video.mp4");
            mountComponent({ file });
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ file }),
            );
        });

        test("calls uploadChunks with chunksMissing as chunksToUpload", async () => {
            uploadChunks.mockResolvedValue();

            mountComponent({ chunksMissing: [3, 7, 11] });
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ chunksToUpload: [3, 7, 11] }),
            );
        });
    });

    describe("progress", () => {
        test("updates progress via onProgress callback", async () => {
            uploadChunks.mockImplementation(({ onProgress }) => {
                onProgress(0.5);
                return Promise.resolve();
            });

            const wrapper = mountComponent();
            await flushPromises();

            expect(wrapper.vm.progress).toBe(0.5);
        });
    });

    describe("success", () => {
        test("status becomes uploaded when uploadChunks resolves", async () => {
            uploadChunks.mockResolvedValue();

            const wrapper = mountComponent();
            await flushPromises();

            expect(wrapper.vm.status).toBe("uploaded");
        });

        test("redirects to file detail page after success", async () => {
            vi.useFakeTimers();
            uploadChunks.mockResolvedValue();

            mountComponent({ fileId: 99 });
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/uploaded-files/99/");
        });
    });

    describe("error handling", () => {
        test("status becomes incomplete when uploadChunks rejects", async () => {
            uploadChunks.mockRejectedValue(new Error("Network error"));

            const wrapper = mountComponent();
            await flushPromises();

            expect(wrapper.vm.status).toBe("incomplete");
        });

        test("redirects after a failed upload", async () => {
            vi.useFakeTimers();
            uploadChunks.mockRejectedValue(new Error("Network error"));

            mountComponent({ fileId: 5 });
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/uploaded-files/5/");
        });
    });

    describe("cancellation", () => {
        test("status becomes cancelled when upload is aborted", async () => {
            uploadChunks.mockImplementation(makeCancellableMock());

            const wrapper = mountComponent();
            await flushPromises();

            wrapper.vm.onCancel();
            await flushPromises();

            expect(wrapper.vm.status).toBe("cancelled");
        });

        test("redirects after cancellation", async () => {
            vi.useFakeTimers();
            uploadChunks.mockImplementation(makeCancellableMock());

            const wrapper = mountComponent({ fileId: 7 });
            await flushPromises();

            wrapper.vm.onCancel();
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/uploaded-files/7/");
        });
    });
});
