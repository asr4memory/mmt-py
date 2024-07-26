<script setup lang="ts">
import LoginForm from '@/components/LoginForm.vue'
</script>

<template>
  <main class="container u-mt u-mb-2">
    <h2>{{ $t('views.LoginView.title') }}</h2>
    <LoginForm />
  </main>
</template>
