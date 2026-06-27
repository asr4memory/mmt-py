import { describe, test, expect, vi } from "vitest";
import seekMedia from "./seek_media";

function fakeMediaElement(readyState: number) {
    const listeners: Record<string, () => void> = {};
    return {
        readyState,
        currentTime: 0,
        play: vi.fn(),
        addEventListener(event: string, cb: () => void) {
            listeners[event] = cb;
        },
        fire(event: string) {
            listeners[event]?.();
        },
    } as unknown as HTMLMediaElement & { fire(event: string): void };
}

describe("seekMedia", () => {
    test("seeks immediately when metadata is loaded", () => {
        const media = fakeMediaElement(1);

        seekMedia(media, 42);

        expect(media.currentTime).toBe(42);
        expect(media.play).not.toHaveBeenCalled();
    });

    test("waits for metadata before seeking", () => {
        const media = fakeMediaElement(0);

        seekMedia(media, 42);
        expect(media.currentTime).toBe(0);

        media.fire("loadedmetadata");
        expect(media.currentTime).toBe(42);
    });

    test("never starts playback", () => {
        const media = fakeMediaElement(1);

        seekMedia(media, 42);

        expect(media.play).not.toHaveBeenCalled();
    });
});
