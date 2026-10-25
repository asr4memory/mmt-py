<script setup lang="ts">
import AlertIcon from "../icons/alert_icon.vue";
import CheckIcon from "../icons/check_icon.vue";
import ClockIcon from "../icons/clock_icon.vue";
import CloseIcon from "../icons/close_icon.vue";
import UploadIcon from "../icons/upload_icon.vue";
import type { UploadStatus } from "./types";

defineOptions({ name: "UploadStatusIcon" });

defineProps<{
    status: UploadStatus;
}>();
</script>

<template>
    <ClockIcon v-if="status === 'pending'" />
    <UploadIcon v-else-if="status === 'uploading'" />
    <CheckIcon v-else-if="status === 'uploaded'" />
    <AlertIcon v-else-if="status === 'incomplete'" />
    <CloseIcon v-else />
</template>
