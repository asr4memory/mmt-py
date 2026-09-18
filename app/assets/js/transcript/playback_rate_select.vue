<script setup lang="ts">
import { PLAYBACK_RATES, useMediaStore } from "./media_store";

// A component of its own, and not part of the player's template, because the
// player re-renders on every timeupdate. Vue rewrites the value attribute of
// the select and of every option on each patch, and a browser rebuilds the
// open dropdown when the attributes of the select change, which makes the
// dropdown flicker while the media is playing. This component takes no props
// and reads the rate from the store, so a re-render of the player leaves it
// alone.
const media = useMediaStore();

function onChange(event: Event) {
    media.setPlaybackRate(+(event.target as HTMLSelectElement).value);
}
</script>

<template>
    <select
        class="media-player__speed"
        :value="media.playbackRate"
        @change="onChange"
        :title="$t('media_player.playback_speed')"
        :aria-label="$t('media_player.playback_speed')"
    >
        <option v-for="rate in PLAYBACK_RATES" :key="rate" :value="rate">
            {{ rate }}x
        </option>
    </select>
</template>
