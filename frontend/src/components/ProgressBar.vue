<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
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
  <progress
    class="progress-bar"
    :style="`--bar-color: ${color}`"
    :value="percentage"
    max="100"
    :aria-label="`${label}: ${percentageStr} %`"
    :title="`${label}: ${percentageStr} %`"
  >
    {{ percentageStr }} %
  </progress>
</template>
