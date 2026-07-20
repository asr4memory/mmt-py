<script setup lang="ts">
import { computed, ref } from "vue";

import FullscreenIcon from "../icons/fullscreen_icon.vue";
import PauseIcon from "../icons/pause_icon.vue";
import PlayIcon from "../icons/play_icon.vue";
import SeekBackIcon from "../icons/seek_back_icon.vue";
import SeekForwardIcon from "../icons/seek_forward_icon.vue";
import VolumeDownIcon from "../icons/volume_down_icon.vue";
import VolumeMutedIcon from "../icons/volume_muted_icon.vue";
import VolumeOnIcon from "../icons/volume_on_icon.vue";
import VolumeUpIcon from "../icons/volume_up_icon.vue";
import { useMediaShortcuts } from "./useMediaShortcuts";

const SEEK_TIME = 5;
const VOLUME_STEP = 0.1;
const PLAYBACK_RATES = [0.7, 1, 1.5, 2];

const props = defineProps<{
    src: string;
    mediaType: string;
}>();

const emit = defineEmits<{ timeupdate: [time: number] }>();

const mediaRef = ref<HTMLMediaElement | null>(null);
const isVideo = computed(() => props.mediaType.startsWith("video"));
const isPlaying = ref(false);
const isMuted = ref(false);
const playbackRate = ref(1);

function onTimeUpdate() {
    if (mediaRef.value) emit("timeupdate", mediaRef.value.currentTime);
}

function togglePlay() {
    if (!mediaRef.value) return;
    if (mediaRef.value.paused) {
        mediaRef.value.play();
    } else {
        mediaRef.value.pause();
    }
}

function onPlayPause() {
    isPlaying.value = mediaRef.value ? !mediaRef.value.paused : false;
}

function toggleMute() {
    if (!mediaRef.value) return;
    mediaRef.value.muted = !mediaRef.value.muted;
}

function onVolumeChange() {
    isMuted.value = mediaRef.value ? mediaRef.value.muted : false;
}

function setPlaybackRate(rate: number) {
    playbackRate.value = rate;
    if (mediaRef.value) mediaRef.value.playbackRate = rate;
}

function stepPlaybackRate(direction: number) {
    const index = PLAYBACK_RATES.indexOf(playbackRate.value);
    const rate = PLAYBACK_RATES[index + direction];
    if (rate !== undefined) setPlaybackRate(rate);
}

function seekLeft() {
    if (!mediaRef.value) return;
    mediaRef.value.currentTime -= SEEK_TIME;
}

function seekRight() {
    if (!mediaRef.value) return;
    mediaRef.value.currentTime += SEEK_TIME;
}

function increaseVolume() {
    if (!mediaRef.value) return;
    mediaRef.value.volume = Math.min(1, mediaRef.value.volume + VOLUME_STEP);
}

function decreaseVolume() {
    if (!mediaRef.value) return;
    mediaRef.value.volume = Math.max(0, mediaRef.value.volume - VOLUME_STEP);
}

function toggleFullscreen() {
    if (!isVideo.value || !mediaRef.value) return;
    if (document.fullscreenElement) {
        document.exitFullscreen();
    } else {
        mediaRef.value.requestFullscreen();
    }
}

useMediaShortcuts({
    togglePlay,
    seekBackward: seekLeft,
    seekForward: seekRight,
    toggleMute,
    toggleFullscreen,
    increaseVolume,
    decreaseVolume,
    increasePlaybackRate: () => stepPlaybackRate(1),
    decreasePlaybackRate: () => stepPlaybackRate(-1),
});

defineExpose({
    get mediaElement() {
        return mediaRef.value;
    },
});
</script>

<template>
    <div
        class="media-player"
        :class="isVideo ? 'media-player--video' : 'media-player--audio'"
    >
        <video
            v-if="isVideo"
            id="media-player"
            class="media-player__element transcript__media"
            ref="mediaRef"
            width="240"
            @timeupdate="onTimeUpdate"
            @play="onPlayPause"
            @pause="onPlayPause"
            @volumechange="onVolumeChange"
            @click="togglePlay"
        >
            <source :src="src" />
        </video>
        <audio
            v-else
            id="media-player"
            class="media-player__element transcript__media"
            ref="mediaRef"
            controls
            width="240"
            @timeupdate="onTimeUpdate"
            @play="onPlayPause"
            @pause="onPlayPause"
            @volumechange="onVolumeChange"
        >
            <source :src="src" />
        </audio>
        <div class="media-player__toolbar">
            <button
                type="button"
                class="media-player__button"
                @click="togglePlay"
                :title="isPlaying ? $t('media_player.pause') : $t('media_player.play')"
                :aria-label="
                    isPlaying ? $t('media_player.pause') : $t('media_player.play')
                "
            >
                <PauseIcon v-if="isPlaying" />
                <PlayIcon v-else />
            </button>

            <button
                type="button"
                class="media-player__button"
                @click="seekLeft"
                :title="$t('media_player.seek_back')"
                :aria-label="$t('media_player.seek_back')"
            >
                <SeekBackIcon />
            </button>

            <button
                type="button"
                class="media-player__button"
                @click="seekRight"
                :title="$t('media_player.seek_forward')"
                :aria-label="$t('media_player.seek_forward')"
            >
                <SeekForwardIcon />
            </button>

            <button
                type="button"
                class="media-player__button"
                :class="{ 'media-player__button--muted': isMuted }"
                @click="toggleMute"
                :title="isMuted ? $t('media_player.unmute') : $t('media_player.mute')"
                :aria-label="
                    isMuted ? $t('media_player.unmute') : $t('media_player.mute')
                "
            >
                <VolumeMutedIcon v-if="isMuted" />
                <VolumeOnIcon v-else />
            </button>

            <button
                type="button"
                class="media-player__button"
                @click="increaseVolume"
                :title="$t('media_player.increase_volume')"
                :aria-label="$t('media_player.increase_volume')"
            >
                <VolumeUpIcon />
            </button>

            <button
                type="button"
                class="media-player__button"
                @click="decreaseVolume"
                :title="$t('media_player.decrease_volume')"
                :aria-label="$t('media_player.decrease_volume')"
            >
                <VolumeDownIcon />
            </button>

            <select
                class="media-player__speed"
                :value="playbackRate"
                @change="
                    setPlaybackRate(+($event.target as HTMLSelectElement).value)
                "
                :title="$t('media_player.playback_speed')"
                :aria-label="$t('media_player.playback_speed')"
            >
                <option v-for="rate in PLAYBACK_RATES" :key="rate" :value="rate">
                    {{ rate }}x
                </option>
            </select>

            <button
                v-if="isVideo"
                type="button"
                class="media-player__button"
                @click="toggleFullscreen"
                :title="$t('media_player.fullscreen')"
                :aria-label="$t('media_player.fullscreen')"
            >
                <FullscreenIcon />
            </button>
        </div>
    </div>
</template>
