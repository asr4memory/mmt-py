<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import PersonIcon from '@/icons/PersonIcon.vue'

const store = useAuthStore()
</script>

<template>
  <header class="site-header">
    <div class="site-header__inner">
      <RouterLink to="/" class="site-header__logo">
        <h1 class="logo">
          <span class="logo__mmt">MMT</span><i class="logo__py">Py</i>
        </h1>
      </RouterLink>

      <nav class="site-header__nav primary-nav">
        <RouterLink v-if="store.user?.can_upload" to="/uploads" class="primary-nav__link">
          {{ $t('components.SiteHeader.uploads') }}
        </RouterLink>
        <RouterLink to="/downloads" class="primary-nav__link">
          {{ $t('components.SiteHeader.downloads') }}
        </RouterLink>
        <RouterLink v-if="store.user?.admin" to="/admin" class="primary-nav__link">
          {{ $t('components.SiteHeader.admin') }}
        </RouterLink>
      </nav>

      <nav v-if="store.user" class="site-header__nav site-header__nav--last primary-nav">
        <RouterLink to="/profile" class="primary-nav__link primary-nav__profile">
          <PersonIcon class="icon" />
          <span>{{ store.user.username }}</span>
        </RouterLink>
        <span class="logout-button">
          <button class="logout-button__button" type="button" @click="store.logout">
            {{ $t('components.SiteHeader.logOut') }}
          </button>
        </span>
      </nav>
      <nav v-else class="site-header__nav site-header__nav--last primary-nav">
        <RouterLink to="/register" class="primary-nav__link">
          {{ $t('components.SiteHeader.register') }}
        </RouterLink>
        <RouterLink to="/log-in" class="primary-nav__link">
          {{ $t('components.SiteHeader.logIn') }}
        </RouterLink>
      </nav>
    </div>
  </header>
</template>
