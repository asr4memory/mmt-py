import { afterEach, describe, expect, test, vi } from "vitest";
import { checkUploadStatus } from "./upload_status_poller";

function respondWith(response: Partial<Response>): void {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response as Response));
}

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("checkUploadStatus", () => {
    test("keeps polling while the file is still processing", async () => {
        respondWith({ ok: true, json: async () => ({ status: "processing" }) });
        const reload = vi.fn();

        expect(await checkUploadStatus("/status/", reload)).toBe(true);
        expect(reload).not.toHaveBeenCalled();
    });

    test("reloads and stops once the file reaches another status", async () => {
        respondWith({ ok: true, json: async () => ({ status: "complete" }) });
        const reload = vi.fn();

        expect(await checkUploadStatus("/status/", reload)).toBe(false);
        expect(reload).toHaveBeenCalledOnce();
    });

    test("reloads and stops when the response is not OK", async () => {
        respondWith({
            ok: false,
            json: async () => ({ status: "processing" }),
        });
        const reload = vi.fn();

        expect(await checkUploadStatus("/status/", reload)).toBe(false);
        expect(reload).toHaveBeenCalledOnce();
    });

    test("requests the URL it was given", async () => {
        respondWith({ ok: true, json: async () => ({ status: "processing" }) });

        await checkUploadStatus("/uploaded-files/7/status/", vi.fn());

        expect(fetch).toHaveBeenCalledWith("/uploaded-files/7/status/");
    });
});
