<script setup lang="ts">
defineProps<{
  type: 'error' | 'warning' | 'info'
}>()
</script>

<template>
  <article :class="`message message--${type}`">
    <div class="message__body u-ll">
      <slot></slot>
    </div>
  </article>
</template>
