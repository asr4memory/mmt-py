import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";

import MediaPlayer from "./media_player.vue";

function mountPlayer(mediaType: string) {
    return mount(MediaPlayer, {
        props: { src: "/media.mp4", mediaType },
        global: { mocks: { $t: (key: string) => key } },
    });
}

beforeEach(() => {
    setActivePinia(createPinia());
});

// jsdom does not implement currentTime on media elements, so it is defined on
// the element before the event is dispatched.
function setMediaTime(element: HTMLMediaElement, current: number) {
    Object.defineProperty(element, "currentTime", {
        value: current,
        configurable: true,
    });
}

// jsdom implements neither duration nor readyState on media elements.
function setMediaDuration(element: HTMLMediaElement, duration: number) {
    Object.defineProperty(element, "duration", {
        value: duration,
        configurable: true,
    });
    Object.defineProperty(element, "readyState", {
        value: 1,
        configurable: true,
    });
}

describe("MediaPlayer time overlay", () => {
    test("shows the current time over a video", async () => {
        const wrapper = mountPlayer("video/mp4");
        const video = wrapper.find("video");
        setMediaTime(video.element as HTMLMediaElement, 83);

        await video.trigger("timeupdate");

        expect(wrapper.find(".media-player__time").text()).toBe("1:23 / 0:00");
    });

    test("shows the total time after the current time", async () => {
        const wrapper = mountPlayer("video/mp4");
        const video = wrapper.find("video");
        setMediaDuration(video.element as HTMLMediaElement, 200);

        await video.trigger("durationchange");

        expect(wrapper.find(".media-player__time").text()).toBe("0:00 / 3:20");
    });

    test("starts at zero before playback", async () => {
        const wrapper = mountPlayer("video/mp4");

        expect(wrapper.find(".media-player__time").text()).toBe("0:00 / 0:00");
    });

    test("shows the current time for audio as well", async () => {
        const wrapper = mountPlayer("audio/mpeg");
        const audio = wrapper.find("audio");
        setMediaTime(audio.element as HTMLMediaElement, 83);

        await audio.trigger("timeupdate");

        expect(wrapper.find(".media-player__time").text()).toBe("1:23 / 0:00");
    });

    test("renders no native controls on the audio element", () => {
        const wrapper = mountPlayer("audio/mpeg");

        expect(wrapper.find("audio").attributes("controls")).toBeUndefined();
    });

    test("renders a box of the video's size for audio, which the element itself cannot provide", () => {
        const wrapper = mountPlayer("audio/mpeg");

        expect(wrapper.find(".media-player__poster").exists()).toBe(true);
        expect(wrapper.find("audio").classes()).not.toContain(
            "transcript__media",
        );
    });

    test("starts playback when the box shown for audio is clicked", async () => {
        const wrapper = mountPlayer("audio/mpeg");
        const audio = wrapper.find("audio").element as HTMLMediaElement;
        const play = vi.spyOn(audio, "play").mockResolvedValue();

        await wrapper.find(".media-player__poster").trigger("click");

        expect(play).toHaveBeenCalled();
    });

    test("renders no separate box for video", () => {
        const wrapper = mountPlayer("video/mp4");

        expect(wrapper.find(".media-player__poster").exists()).toBe(false);
    });
});

describe("MediaPlayer progress bar", () => {
    test("seeks to the position the slider is moved to", async () => {
        const wrapper = mountPlayer("video/mp4");
        const video = wrapper.find("video");
        const element = video.element as HTMLMediaElement;
        setMediaDuration(element, 60);
        await video.trigger("durationchange");

        const slider = wrapper.find<HTMLInputElement>(
            ".media-player__progress",
        );
        slider.element.value = "30";
        await slider.trigger("input");

        expect(element.currentTime).toBe(30);
    });

    test("spans the duration of the media file", async () => {
        const wrapper = mountPlayer("video/mp4");
        const video = wrapper.find("video");
        setMediaDuration(video.element as HTMLMediaElement, 60);

        await video.trigger("durationchange");

        const slider = wrapper.find(".media-player__progress");
        expect(slider.attributes("max")).toBe("60");
        expect(slider.attributes("min")).toBe("0");
    });

    test("follows playback", async () => {
        const wrapper = mountPlayer("video/mp4");
        const video = wrapper.find("video");
        const element = video.element as HTMLMediaElement;
        setMediaDuration(element, 60);
        setMediaTime(element, 15);

        await video.trigger("durationchange");
        await video.trigger("timeupdate");

        const slider = wrapper.find<HTMLInputElement>(
            ".media-player__progress",
        );
        expect(slider.element.value).toBe("15");
    });

    test("is a range input, so it can be dragged and operated by keyboard", () => {
        const wrapper = mountPlayer("video/mp4");

        const slider = wrapper.find(".media-player__progress");
        expect(slider.element.tagName).toBe("INPUT");
        expect(slider.attributes("type")).toBe("range");
    });

    test("renders the bar for audio as well", () => {
        const wrapper = mountPlayer("audio/mpeg");

        expect(wrapper.find(".media-player__progress").exists()).toBe(true);
    });
});
