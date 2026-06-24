<script setup lang="ts">
import type { Speaker } from "./types";

defineProps<{
    modelValue?: string;
    segmentId: string;
    speakers: Speaker[];
}>();

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

function handleChange(event: Event) {
    emit("update:modelValue", (event.target as HTMLSelectElement).value);
}
</script>

<template>
    <select
        :id="`speaker-select-${segmentId}`"
        :value="modelValue"
        @change="handleChange"
        class="speaker-select"
    >
        <button>
            <selectedcontent></selectedcontent>
        </button>
        <option
            v-for="speaker in speakers"
            :key="speaker.id"
            :value="speaker.id"
        >
            <span
                class="speaker-select__swatch"
                :style="{ backgroundColor: speaker.color }"
            ></span>
            {{ speaker.name }}
        </option>
    </select>
</template>
