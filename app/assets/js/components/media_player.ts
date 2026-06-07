import { defineComponent, ref, computed } from "vue";

const SEEK_TIME = 5;

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

        function setPlaybackRate(rate: number) {
            playbackRate.value = rate;
            if (mediaRef.value) mediaRef.value.playbackRate = rate;
        }

        function seekLeft() {
            if (!mediaRef.value) return;
            mediaRef.value.currentTime -= SEEK_TIME;
            mediaRef.value.play();
        }

        function seekRight() {
            if (!mediaRef.value) return;
            mediaRef.value.currentTime += SEEK_TIME;
            mediaRef.value.play();
        }

        expose({
            get mediaElement() {
                return mediaRef.value;
            },
        });

        return {
            mediaRef,
            isVideo,
            isPlaying,
            playbackRate,
            PLAYBACK_RATES,
            onTimeUpdate,
            onPlayPause,
            togglePlay,
            setPlaybackRate,
            seekLeft,
            seekRight,
        };
    },
    template: `
    <div class="media-player" :class="isVideo ? 'media-player--video' : 'media-player--audio'">
        <video v-if="isVideo" id="media-player" class="media-player__element transcript__media" ref="mediaRef"
            width="240" @timeupdate="onTimeUpdate" @play="onPlayPause" @pause="onPlayPause" @click="togglePlay">
            <source :src="src" :type="mediaType" />
        </video>
        <audio v-else id="media-player" class="media-player__element transcript__media" ref="mediaRef" controls
            width="240" @timeupdate="onTimeUpdate" @play="onPlayPause" @pause="onPlayPause">
            <source :src="src" :type="mediaType" />
        </audio>
        <div class="media-player__toolbar repel">
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

            <select class="media-player__speed" :value="playbackRate" @change="setPlaybackRate(+$event.target.value)"
                :title="$t('media_player.playback_speed')" :aria-label="$t('media_player.playback_speed')">
                <option v-for="rate in PLAYBACK_RATES" :key="rate" :value="rate">{{ rate }}x</option>
            </select>
        </div>
    </div>
    `,
});
