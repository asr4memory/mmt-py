<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <footer class="site-footer">
    <p>Media Management Tool v2.0.0</p>

    <nav class="site-footer__nav u-mt">
      <RouterLink to="legal-notice" class="site-footer__link">
        {{ $t('components.SiteFooter.legalNotice') }}
      </RouterLink>
      <RouterLink to="privacy" class="site-footer__link">
        {{ $t('components.SiteFooter.privacy') }}
      </RouterLink>
      <RouterLink :to="{ name: 'accessibility' }" class="site-footer__link">
        {{ $t('components.SiteFooter.accessibility') }}
      </RouterLink>
      <RouterLink to="contact" class="site-footer__link">
        {{ $t('components.SiteFooter.contact') }}
      </RouterLink>
    </nav>
  </footer>
</template>
