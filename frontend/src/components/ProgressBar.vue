<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  id: string
  percentage: number
  color: string
  label: string
}>()

const { locale } = useI18n()

const percentageStr = computed(() => {
  return props.percentage.toLocaleString(locale.value, { maximumFractionDigits: 1 })
})
</script>

<template>
  <div class="progress-bar">
    <label :for="id" class="progress-bar__label">
      {{label}}: {{percentageStr}}&thinsp;%
    </label>
    <progress
      :id="id"
      class="progress-bar__bar"
      :style="`--bar-color: ${color}`"
      :value="percentage"
      max="100"
    >
    </progress>
  </div>
</template>
