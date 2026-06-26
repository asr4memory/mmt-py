<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import deformatTimecode from "../shared/deformat_timecode";
import formatTimecode from "../shared/format_timecode";

const props = defineProps<{ seconds: number }>();
const emit = defineEmits<{ submit: [seconds: number] }>();

const editMode = ref(false);

const formattedTimecode = computed(() => formatTimecode(props.seconds));

function handleFocus(event: FocusEvent) {
    editMode.value = true;
    const span = event.target as HTMLSpanElement;
    nextTick(() => {
        const input = span.firstElementChild as HTMLInputElement | null;
        input?.focus();
    });
}

function handleChange(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.checkValidity()) {
        const newSeconds = deformatTimecode(input.value);
        if (newSeconds !== props.seconds) {
            emit("submit", newSeconds);
        }
    }
    nextTick(() => {
        editMode.value = false;
    });
}
</script>

<template>
    <span
        class="timecode-input"
        :tabindex="editMode ? -1 : 0"
        @focus="handleFocus"
    >
        {{ formattedTimecode }}
        <input
            v-if="editMode"
            class="timecode-input__input"
            tabindex="0"
            required
            pattern="[0-9]{1,2}:[0-5][0-9]:[0-5][0-9]\.[0-9]{3}"
            placeholder="#:##:##.###"
            :value="formattedTimecode"
            @blur="handleChange"
            @keyup.enter="handleChange"
        />
    </span>
</template>
