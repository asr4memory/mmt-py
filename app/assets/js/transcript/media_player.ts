import { defineComponent, ref, computed } from "vue";

import { useMediaShortcuts } from "./useMediaShortcuts";

const SEEK_TIME = 5;
const VOLUME_STEP = 0.1;

export default defineComponent({
    name: "MediaPlayer",
    props: {
        src: { type: String, required: true },
        mediaType: { type: String, required: true },
    },
    emits: ["timeupdate"],
    setup(props, { emit, expose }) {
        const mediaRef = ref<HTMLMediaElement | null>(null);
        const isVideo = computed(() => props.mediaType.startsWith("video"));
        const isPlaying = ref(false);
        const isMuted = ref(false);
        const playbackRate = ref(1);
        const PLAYBACK_RATES = [0.7, 1, 1.5, 2];

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
            mediaRef.value.volume = Math.min(
                1,
                mediaRef.value.volume + VOLUME_STEP,
            );
        }

        function decreaseVolume() {
            if (!mediaRef.value) return;
            mediaRef.value.volume = Math.max(
                0,
                mediaRef.value.volume - VOLUME_STEP,
            );
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

        expose({
            get mediaElement() {
                return mediaRef.value;
            },
        });

        return {
            mediaRef,
            isVideo,
            isPlaying,
            isMuted,
            playbackRate,
            PLAYBACK_RATES,
            onTimeUpdate,
            onPlayPause,
            togglePlay,
            toggleMute,
            onVolumeChange,
            setPlaybackRate,
            seekLeft,
            seekRight,
            increaseVolume,
            decreaseVolume,
            toggleFullscreen,
        };
    },
    template: `
    <div class="media-player" :class="isVideo ? 'media-player--video' : 'media-player--audio'">
        <video v-if="isVideo" id="media-player" class="media-player__element transcript__media" ref="mediaRef"
            width="240" @timeupdate="onTimeUpdate" @play="onPlayPause" @pause="onPlayPause" @volumechange="onVolumeChange" @click="togglePlay">
            <source :src="src" :type="mediaType" />
        </video>
        <audio v-else id="media-player" class="media-player__element transcript__media" ref="mediaRef" controls
            width="240" @timeupdate="onTimeUpdate" @play="onPlayPause" @pause="onPlayPause" @volumechange="onVolumeChange">
            <source :src="src" :type="mediaType" />
        </audio>
        <div class="media-player__toolbar">
            <button type="button" class="media-player__button" @click="togglePlay"
                :title="isPlaying ? $t('media_player.pause') : $t('media_player.play')"
                :aria-label="isPlaying ? $t('media_player.pause') : $t('media_player.play')">
                <svg v-if="isPlaying" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <rect x="6.4"  y="5" width="3.7" height="14" rx="1.3" />
                    <rect x="13.9" y="5" width="3.7" height="14" rx="1.3" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4.8 L18.6 12 L7 19.2 Z" /></svg>
            </button>

            <button type="button" class="media-player__button" @click="seekLeft"
                :title="$t('media_player.seek_back')" :aria-label="$t('media_player.seek_back')">
                <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M11 5 L4 12 L11 19 Z M19 5 L12 12 L19 19 Z" /></svg>
            </button>

            <button type="button" class="media-player__button" @click="seekRight"
                :title="$t('media_player.seek_forward')" :aria-label="$t('media_player.seek_forward')">
                <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M5 5 L12 12 L5 19 Z M13 5 L20 12 L13 19 Z" /></svg>
            </button>

            <button type="button" class="media-player__button" :class="{ 'media-player__button--muted': isMuted }" @click="toggleMute"
                :title="isMuted ? $t('media_player.unmute') : $t('media_player.mute')"
                :aria-label="isMuted ? $t('media_player.unmute') : $t('media_player.mute')">
                <svg v-if="isMuted" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M4 9 H7 L11.5 5 V19 L7 15 H4 Z" fill="currentColor" />
                    <path d="M15.5 9.5 L20.5 14.5 M20.5 9.5 L15.5 14.5"
                            fill="none" stroke="currentColor" stroke-width="1.9"
                            stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M4 9 H7 L11.5 5 V19 L7 15 H4 Z" fill="currentColor" />
                    <path d="M15 9.2 a4 4 0 0 1 0 5.6 M17.4 7 a7.2 7.2 0 0 1 0 10"
                            fill="none" stroke="currentColor" stroke-width="1.8"
                            stroke-linecap="round" stroke-linejoin="round" />
                </svg>
            </button>

            <button type="button" class="media-player__button" @click="increaseVolume"
                :title="$t('media_player.increase_volume')" :aria-label="$t('media_player.increase_volume')">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 9 H7 L11.5 5 V19 L7 15 H4 Z" fill="currentColor" />
                    <path d="M18 8.5 V14.5 M15 11.5 H21" fill="none" stroke="currentColor"
                          stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
            </button>

            <button type="button" class="media-player__button" @click="decreaseVolume"
                :title="$t('media_player.decrease_volume')" :aria-label="$t('media_player.decrease_volume')">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 9 H7 L11.5 5 V19 L7 15 H4 Z" fill="currentColor" />
                    <path d="M15 11.5 H21" fill="none" stroke="currentColor"
                          stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
            </button>

            <select class="media-player__speed" :value="playbackRate" @change="setPlaybackRate(+$event.target.value)"
                :title="$t('media_player.playback_speed')" :aria-label="$t('media_player.playback_speed')">
                <option v-for="rate in PLAYBACK_RATES" :key="rate" :value="rate">{{ rate }}x</option>
            </select>

            <button v-if="isVideo" type="button" class="media-player__button" @click="toggleFullscreen"
                :title="$t('media_player.fullscreen')" :aria-label="$t('media_player.fullscreen')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M4 9 V5 H8 M16 5 H20 V9 M20 15 V19 H16 M8 19 H4 V15" />
                </svg>
            </button>
        </div>
    </div>
    `,
});
