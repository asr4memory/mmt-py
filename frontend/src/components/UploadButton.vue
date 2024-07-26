<script setup lang="ts">
import UploadIcon from '@/icons/UploadIcon.vue'

defineProps<{
  onChange: (payload: Event) => void
}>()

const ACCEPTED_FILES = 'video/*,audio/*,image/*,model/vnd.mts,application/mxf'
const FILESIZE_LIMIT = 1 * 1024 * 1024 * 1024 * 1024 // 1 TB
</script>

<template>
  <form class="upload-button">
    <label for="file-input" class="upload-button__label">
      {{ $t('components.UploadButton.label') }}
    </label>
    <input
      class="upload-button__input u-mt-1/2"
      type="file"
      name="files"
      id="file-input"
      :accept="ACCEPTED_FILES"
      multiple
      @change="onChange"
    />
  </form>
</template>
