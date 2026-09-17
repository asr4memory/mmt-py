import { setActivePinia, createPinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { useMediaStore } from "./media_store";

// jsdom implements neither playback nor fullscreen on media elements, so the
// store is driven against a stand-in that records the calls. readyState is 1
// so that the seek helpers act at once instead of waiting for metadata, and
// addEventListener runs its callback immediately so that seekAndPlay reaches
// the play() call.
function fakeMedia(tagName = "VIDEO"): HTMLMediaElement {
    return {
        tagName,
        currentTime: 0,
        volume: 1,
        muted: false,
        paused: true,
        playbackRate: 1,
        readyState: 1,
        play: vi.fn(),
        pause: vi.fn(),
        requestFullscreen: vi.fn(),
        addEventListener: (_type: string, callback: () => void) => callback(),
    } as unknown as HTMLMediaElement;
}

beforeEach(() => {
    setActivePinia(createPinia());
});

describe("media store registration", () => {
    test("hands out the element the player registered", () => {
        const store = useMediaStore();
        const media = fakeMedia();

        store.setElement(media);

        expect(store.element).toBe(media);
    });

    test("holds no element before a player registers one", () => {
        const store = useMediaStore();

        expect(store.element).toBe(null);
    });

    test("forgets the element when the player unmounts", () => {
        const store = useMediaStore();
        store.setElement(fakeMedia());

        store.setElement(null);

        expect(store.element).toBe(null);
    });

    test("carries the current playback rate over to a newly registered element", () => {
        const store = useMediaStore();
        store.setPlaybackRate(1.5);
        const media = fakeMedia();

        store.setElement(media);

        expect(media.playbackRate).toBe(1.5);
    });
});

describe("media store seeking", () => {
    test("seeks to a position without starting playback", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        store.setElement(media);

        store.seekTo(42);

        expect(media.currentTime).toBe(42);
        expect(media.play).not.toHaveBeenCalled();
    });

    test("seeks and starts playback", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        store.setElement(media);

        store.playFrom(12);

        expect(media.currentTime).toBe(12);
        expect(media.play).toHaveBeenCalled();
    });

    test("seeks backward and forward by five seconds", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        media.currentTime = 20;
        store.setElement(media);

        store.seekForward();
        expect(media.currentTime).toBe(25);

        store.seekBackward();
        expect(media.currentTime).toBe(20);
    });
});

describe("media store playback", () => {
    test("starts a paused element", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        store.setElement(media);

        store.togglePlay();

        expect(media.play).toHaveBeenCalled();
    });

    test("pauses a playing element", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        (media as { paused: boolean }).paused = false;
        store.setElement(media);

        store.togglePlay();

        expect(media.pause).toHaveBeenCalled();
    });

    test("reads the play state back from the element", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        (media as { paused: boolean }).paused = false;
        store.setElement(media);

        store.syncPlayState();

        expect(store.isPlaying).toBe(true);
    });
});

describe("media store volume", () => {
    test("mutes and unmutes", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        store.setElement(media);

        store.toggleMute();
        expect(media.muted).toBe(true);

        store.toggleMute();
        expect(media.muted).toBe(false);
    });

    test("reads the muted state and the level back from the element", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        media.muted = true;
        media.volume = 0.4;
        store.setElement(media);

        store.syncVolumeState();

        expect(store.isMuted).toBe(true);
        expect(store.volume).toBeCloseTo(0.4);
    });

    test("sets the volume to a given level", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        store.setElement(media);

        store.setVolume(0.25);

        expect(media.volume).toBeCloseTo(0.25);
    });

    test("raises and lowers the volume in steps", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        media.volume = 0.5;
        store.setElement(media);

        store.increaseVolume();
        expect(media.volume).toBeCloseTo(0.6);

        store.decreaseVolume();
        expect(media.volume).toBeCloseTo(0.5);
    });

    test("does not raise the volume above one", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        media.volume = 0.95;
        store.setElement(media);

        store.increaseVolume();

        expect(media.volume).toBe(1);
    });

    test("does not lower the volume below zero", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        media.volume = 0.05;
        store.setElement(media);

        store.decreaseVolume();

        expect(media.volume).toBe(0);
    });
});

describe("media store playback rate", () => {
    test("steps up and down through the offered rates", () => {
        const store = useMediaStore();
        const media = fakeMedia();
        store.setElement(media);

        store.increasePlaybackRate();
        expect(store.playbackRate).toBe(1.5);
        expect(media.playbackRate).toBe(1.5);

        store.decreasePlaybackRate();
        expect(store.playbackRate).toBe(1);
    });

    test("stays at the fastest rate", () => {
        const store = useMediaStore();
        store.setElement(fakeMedia());
        store.setPlaybackRate(2);

        store.increasePlaybackRate();

        expect(store.playbackRate).toBe(2);
    });

    test("stays at the slowest rate", () => {
        const store = useMediaStore();
        store.setElement(fakeMedia());
        store.setPlaybackRate(0.7);

        store.decreasePlaybackRate();

        expect(store.playbackRate).toBe(0.7);
    });
});

describe("media store fullscreen", () => {
    test("requests fullscreen for a video element", () => {
        const store = useMediaStore();
        const media = fakeMedia("VIDEO");
        store.setElement(media);

        store.toggleFullscreen();

        expect(media.requestFullscreen).toHaveBeenCalled();
    });

    test("does nothing for an audio element", () => {
        const store = useMediaStore();
        const media = fakeMedia("AUDIO");
        store.setElement(media);

        store.toggleFullscreen();

        expect(media.requestFullscreen).not.toHaveBeenCalled();
    });
});

describe("media store without an element", () => {
    test("accepts every command before a player has registered", () => {
        const store = useMediaStore();

        expect(() => {
            store.seekTo(10);
            store.playFrom(10);
            store.togglePlay();
            store.seekBackward();
            store.seekForward();
            store.toggleMute();
            store.toggleFullscreen();
            store.increaseVolume();
            store.decreaseVolume();
            store.setVolume(0.5);
            store.increasePlaybackRate();
            store.decreasePlaybackRate();
        }).not.toThrow();
    });
});
