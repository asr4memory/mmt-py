<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <main class="container u-mt u-mb-2">
    <h1>404</h1>
    <p class="u-ll">
      {{ $t('views.NotFoundView.message') }}
    </p>
    <p class="u-mt">
      <RouterLink to="/">
        {{ $t('views.NotFoundView.back') }}
      </RouterLink>
    </p>
  </main>
</template>
