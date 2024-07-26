<script setup lang="ts">
import { RouterView } from 'vue-router'
import SiteHeader from './components/SiteHeader.vue'
import SiteFooter from './components/SiteFooter.vue'
import UploadTray from './components/UploadTray.vue'
</script>

<template>
  <div class="layout">
    <SiteHeader />

    <div class="layout__main">
      <RouterView />
    </div>

    <SiteFooter />
    <UploadTray />
  </div>
</template>
