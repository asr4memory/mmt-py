import { defineStore } from "pinia";
import { ref, shallowRef } from "vue";

import seekAndPlay from "./seek_and_play";
import seekMedia from "./seek_media";

const SEEK_TIME = 5;
const VOLUME_STEP = 0.1;

export const PLAYBACK_RATES = [0.7, 1, 1.5, 2];

// The single media element of the transcript editor and every command that
// operates on it. The player component registers its element here on mount;
// every other component reaches the element through this store rather than
// looking it up in the document or receiving it through a chain of props.
export const useMediaStore = defineStore("media", () => {
    const element = shallowRef<HTMLMediaElement | null>(null);
    const isPlaying = ref(false);
    const isMuted = ref(false);
    const playbackRate = ref(1);

    function setElement(mediaElement: HTMLMediaElement | null) {
        element.value = mediaElement;
        if (mediaElement) mediaElement.playbackRate = playbackRate.value;
    }

    // Moves playback to a position without starting it, for selecting a
    // segment.
    function seekTo(time: number) {
        if (element.value) seekMedia(element.value, time);
    }

    // Moves playback to a position and starts it, for playing a segment or a
    // single word.
    function playFrom(time: number) {
        if (element.value) seekAndPlay(element.value, time);
    }

    function togglePlay() {
        const media = element.value;
        if (!media) return;
        if (media.paused) {
            media.play();
        } else {
            media.pause();
        }
    }

    function seekBackward() {
        if (element.value) element.value.currentTime -= SEEK_TIME;
    }

    function seekForward() {
        if (element.value) element.value.currentTime += SEEK_TIME;
    }

    function toggleMute() {
        if (element.value) element.value.muted = !element.value.muted;
    }

    function increaseVolume() {
        const media = element.value;
        if (media) media.volume = Math.min(1, media.volume + VOLUME_STEP);
    }

    function decreaseVolume() {
        const media = element.value;
        if (media) media.volume = Math.max(0, media.volume - VOLUME_STEP);
    }

    function setPlaybackRate(rate: number) {
        playbackRate.value = rate;
        if (element.value) element.value.playbackRate = rate;
    }

    function stepPlaybackRate(direction: number) {
        const index = PLAYBACK_RATES.indexOf(playbackRate.value);
        const rate = PLAYBACK_RATES[index + direction];
        if (rate !== undefined) setPlaybackRate(rate);
    }

    function increasePlaybackRate() {
        stepPlaybackRate(1);
    }

    function decreasePlaybackRate() {
        stepPlaybackRate(-1);
    }

    // Only a video element can be shown fullscreen. The tag name is used
    // rather than the media type, so that the store does not depend on the
    // props of the player component.
    function toggleFullscreen() {
        const media = element.value;
        if (!media || media.tagName !== "VIDEO") return;
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            media.requestFullscreen();
        }
    }

    // The element is the authority on whether it plays and whether it is
    // muted, because the user can change both through the native controls.
    // The player calls these from the corresponding media events.
    function syncPlayState() {
        isPlaying.value = element.value ? !element.value.paused : false;
    }

    function syncMuted() {
        isMuted.value = element.value ? element.value.muted : false;
    }

    return {
        element,
        isPlaying,
        isMuted,
        playbackRate,
        setElement,
        seekTo,
        playFrom,
        togglePlay,
        seekBackward,
        seekForward,
        toggleMute,
        increaseVolume,
        decreaseVolume,
        setPlaybackRate,
        increasePlaybackRate,
        decreasePlaybackRate,
        toggleFullscreen,
        syncPlayState,
        syncMuted,
    };
});
