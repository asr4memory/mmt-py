import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createI18n } from "vue-i18n";

import ResumeUpload from "./resume_upload";
import uploadChunks from "./upload_chunks";
import type { UploadChunksOptions } from "./upload_chunks";
import en from "../locales/en.js";
import de from "../locales/de.js";

const i18n = createI18n({ legacy: false, locale: "en", messages: { en, de } });

vi.mock("./upload_chunks", () => ({ default: vi.fn() }));
vi.mock("./compute_checksum", () => ({ default: vi.fn().mockResolvedValue("abc123") }));
vi.mock("./submit_checksum.js", () => ({ default: vi.fn().mockResolvedValue(null) }));

function makeFile(name = "test.mp4") {
    return new File(["content"], name);
}

function mountComponent(overrides: Partial<InstanceType<typeof ResumeUpload>["$props"]> = {}) {
    return mount(ResumeUpload, {
        props: {
            fileId: 1,
            chunkSize: 5242880,
            chunksMissing: [0, 1, 2],
            checksumSubmitted: false,
            file: makeFile(),
            ...overrides,
        },
        global: { plugins: [i18n] },
    });
}

function makeCancellableMock() {
    return ({ signal }: UploadChunksOptions): Promise<void> =>
        new Promise((_, reject) => {
            signal!.addEventListener("abort", () => {
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
            vi.mocked(uploadChunks).mockResolvedValue();

            const wrapper = mountComponent();

            expect(wrapper.vm.status).toBe("uploading");
        });
    });

    describe("uploadChunks call", () => {
        test("calls uploadChunks with fileId prop", async () => {
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent({ fileId: 42 });
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ fileId: 42 }),
            );
        });

        test("calls uploadChunks with chunkSize prop", async () => {
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent({ chunkSize: 1048576 });
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ chunkSize: 1048576 }),
            );
        });

        test("calls uploadChunks with file prop", async () => {
            vi.mocked(uploadChunks).mockResolvedValue();

            const file = makeFile("video.mp4");
            mountComponent({ file });
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ file }),
            );
        });

        test("calls uploadChunks with chunksMissing as chunksToUpload", async () => {
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent({ chunksMissing: [3, 7, 11] });
            await flushPromises();

            expect(uploadChunks).toHaveBeenCalledWith(
                expect.objectContaining({ chunksToUpload: [3, 7, 11] }),
            );
        });
    });

    describe("progress", () => {
        test("updates transferred via onProgress callback", async () => {
            vi.mocked(uploadChunks).mockImplementation(({ onProgress }: UploadChunksOptions) => {
                onProgress?.(3);
                return Promise.resolve();
            });

            const wrapper = mountComponent();
            await flushPromises();

            expect(wrapper.vm.transferred).toBe(3);
        });
    });

    describe("success", () => {
        test("status becomes uploaded when uploadChunks resolves", async () => {
            vi.mocked(uploadChunks).mockResolvedValue();

            const wrapper = mountComponent();
            await flushPromises();

            expect(wrapper.vm.status).toBe("uploaded");
        });

        test("redirects to file detail page after success", async () => {
            vi.useFakeTimers();
            vi.mocked(uploadChunks).mockResolvedValue();

            mountComponent({ fileId: 99 });
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/uploaded-files/99/");
        });
    });

    describe("error handling", () => {
        test("status becomes incomplete when uploadChunks rejects", async () => {
            vi.mocked(uploadChunks).mockRejectedValue(new Error("Network error"));

            const wrapper = mountComponent();
            await flushPromises();

            expect(wrapper.vm.status).toBe("incomplete");
        });

        test("redirects after a failed upload", async () => {
            vi.useFakeTimers();
            vi.mocked(uploadChunks).mockRejectedValue(new Error("Network error"));

            mountComponent({ fileId: 5 });
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/uploaded-files/5/");
        });
    });

    describe("cancellation", () => {
        test("status becomes cancelled when upload is aborted", async () => {
            vi.mocked(uploadChunks).mockImplementation(makeCancellableMock());

            const wrapper = mountComponent();
            await flushPromises();

            wrapper.vm.onCancel();
            await flushPromises();

            expect(wrapper.vm.status).toBe("cancelled");
        });

        test("redirects after cancellation", async () => {
            vi.useFakeTimers();
            vi.mocked(uploadChunks).mockImplementation(makeCancellableMock());

            const wrapper = mountComponent({ fileId: 7 });
            await flushPromises();

            wrapper.vm.onCancel();
            await flushPromises();
            vi.runAllTimers();

            expect(window.location.href).toBe("/uploaded-files/7/");
        });
    });
});
