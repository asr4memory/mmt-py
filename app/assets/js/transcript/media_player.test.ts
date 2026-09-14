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

    test("renders no overlay for audio", () => {
        const wrapper = mountPlayer("audio/mpeg");

        expect(wrapper.find(".media-player__time").exists()).toBe(false);
    });
});
