<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import FullscreenIcon from "../icons/fullscreen_icon.vue";
import PauseIcon from "../icons/pause_icon.vue";
import PlayIcon from "../icons/play_icon.vue";
import SeekBackIcon from "../icons/seek_back_icon.vue";
import SeekForwardIcon from "../icons/seek_forward_icon.vue";
import VolumeLowIcon from "../icons/volume_low_icon.vue";
import VolumeMutedIcon from "../icons/volume_muted_icon.vue";
import VolumeOnIcon from "../icons/volume_on_icon.vue";
import formatClockTime from "../shared/format_clock_time";
import { useMediaStore } from "./media_store";
import PlaybackRateSelect from "./playback_rate_select.vue";

const props = defineProps<{
    src: string;
    mediaType: string;
}>();

const emit = defineEmits<{ timeupdate: [time: number] }>();

// The commands and the state they change live in the store, so that the
// transcript components can reach them without going through this component.
// What stays here is the state the player alone displays: the clock and the
// progress bar.
const media = useMediaStore();

const mediaRef = ref<HTMLMediaElement | null>(null);
const isVideo = computed(() => props.mediaType.startsWith("video"));
const currentTime = ref(0);
const duration = ref(0);

const clock = computed(() => formatClockTime(currentTime.value));
const totalClock = computed(() => formatClockTime(duration.value));
const progressPercent = computed(() =>
    duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0,
);
const volumePercent = computed(() => media.volume * 100);

onMounted(() => media.setElement(mediaRef.value));
onBeforeUnmount(() => media.setElement(null));

function onTimeUpdate() {
    if (!mediaRef.value) return;
    currentTime.value = mediaRef.value.currentTime;
    emit("timeupdate", mediaRef.value.currentTime);
}

function onDurationChange() {
    if (!mediaRef.value) return;
    const value = mediaRef.value.duration;
    duration.value = Number.isFinite(value) ? value : 0;
}

function onProgressInput(event: Event) {
    const value = +(event.target as HTMLInputElement).value;
    currentTime.value = value;
    media.seekTo(value);
}

function onVolumeInput(event: Event) {
    media.setVolume(+(event.target as HTMLInputElement).value);
}
</script>

<template>
    <div
        class="media-player"
        :class="isVideo ? 'media-player--video' : 'media-player--audio'"
    >
        <div class="media-player__stage">
            <video
                v-if="isVideo"
                class="media-player__element transcript__media"
                ref="mediaRef"
                width="240"
                @timeupdate="onTimeUpdate"
                @durationchange="onDurationChange"
                @play="media.syncPlayState"
                @pause="media.syncPlayState"
                @volumechange="media.syncVolumeState"
                @click="media.togglePlay"
            >
                <source :src="src" />
            </video>
            <audio
                v-else
                class="media-player__element"
                ref="mediaRef"
                width="240"
                @timeupdate="onTimeUpdate"
                @durationchange="onDurationChange"
                @play="media.syncPlayState"
                @pause="media.syncPlayState"
                @volumechange="media.syncVolumeState"
            >
                <source :src="src" />
            </audio>
            <!-- Browsers hide an audio element without controls, so the box that
                 keeps the bar at its height is a separate element. -->
            <div
                v-if="!isVideo"
                class="media-player__element media-player__poster transcript__media"
                @click="media.togglePlay"
            ></div>
            <p class="media-player__time">{{ clock }} / {{ totalClock }}</p>
            <input
                type="range"
                class="media-player__progress"
                min="0"
                :max="duration"
                step="any"
                :value="currentTime"
                :style="{ '--progress': `${progressPercent}%` }"
                :title="$t('media_player.seek_to_position')"
                :aria-label="$t('media_player.seek_to_position')"
                @input="onProgressInput"
            />
        </div>
        <div class="media-player__toolbar">
            <button
                type="button"
                class="media-player__button"
                @click="media.togglePlay"
                :title="media.isPlaying ? $t('media_player.pause') : $t('media_player.play')"
                :aria-label="
                    media.isPlaying ? $t('media_player.pause') : $t('media_player.play')
                "
            >
                <PauseIcon v-if="media.isPlaying" />
                <PlayIcon v-else />
            </button>

            <button
                type="button"
                class="media-player__button"
                @click="media.seekBackward"
                :title="$t('media_player.seek_back')"
                :aria-label="$t('media_player.seek_back')"
            >
                <SeekBackIcon />
            </button>

            <button
                type="button"
                class="media-player__button"
                @click="media.seekForward"
                :title="$t('media_player.seek_forward')"
                :aria-label="$t('media_player.seek_forward')"
            >
                <SeekForwardIcon />
            </button>

            <!-- The button mutes on click; the slider is revealed above it on
                 hover and while anything inside has focus, so that it does not
                 take up room in the toolbar. -->
            <div class="media-player__volume">
                <button
                    type="button"
                    class="media-player__button"
                    :class="{ 'media-player__button--muted': media.isMuted }"
                    @click="media.toggleMute"
                    :title="media.isMuted ? $t('media_player.unmute') : $t('media_player.mute')"
                    :aria-label="
                        media.isMuted ? $t('media_player.unmute') : $t('media_player.mute')
                    "
                >
                    <VolumeMutedIcon v-if="media.isMuted" />
                    <VolumeLowIcon v-else-if="media.volume < 0.5" />
                    <VolumeOnIcon v-else />
                </button>
                <input
                    type="range"
                    class="media-player__volume-slider"
                    min="0"
                    max="1"
                    step="0.01"
                    :value="media.volume"
                    :style="{ '--progress': `${volumePercent}%` }"
                    :title="$t('media_player.volume')"
                    :aria-label="$t('media_player.volume')"
                    @input="onVolumeInput"
                />
            </div>

            <PlaybackRateSelect />

            <button
                v-if="isVideo"
                type="button"
                class="media-player__button u-ml-auto"
                @click="media.toggleFullscreen"
                :title="$t('media_player.fullscreen')"
                :aria-label="$t('media_player.fullscreen')"
            >
                <FullscreenIcon />
            </button>
        </div>
    </div>
</template>
