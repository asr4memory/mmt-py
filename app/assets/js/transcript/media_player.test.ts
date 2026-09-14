import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";

import MediaPlayer from "./media_player.vue";

function mountPlayer(mediaType: string) {
    return mount(MediaPlayer, {
        props: { src: "/media.mp4", mediaType },
        global: { mocks: { $t: (key: string) => key } },
    });
}

// jsdom does not implement currentTime on media elements, so it is defined on
// the element before the event is dispatched.
function setMediaTime(element: HTMLMediaElement, current: number) {
    Object.defineProperty(element, "currentTime", {
        value: current,
        configurable: true,
    });
}

describe("MediaPlayer time overlay", () => {
    test("shows the current time over a video", async () => {
        const wrapper = mountPlayer("video/mp4");
        const video = wrapper.find("video");
        setMediaTime(video.element as HTMLMediaElement, 83);

        await video.trigger("timeupdate");

        expect(wrapper.find(".media-player__time").text()).toBe("1:23");
    });

    test("starts at zero before playback", async () => {
        const wrapper = mountPlayer("video/mp4");

        expect(wrapper.find(".media-player__time").text()).toBe("0:00");
    });

    test("shows the current time for audio as well", async () => {
        const wrapper = mountPlayer("audio/mpeg");
        const audio = wrapper.find("audio");
        setMediaTime(audio.element as HTMLMediaElement, 83);

        await audio.trigger("timeupdate");

        expect(wrapper.find(".media-player__time").text()).toBe("1:23");
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

    test("renders no separate box for video", () => {
        const wrapper = mountPlayer("video/mp4");

        expect(wrapper.find(".media-player__poster").exists()).toBe(false);
    });
});
