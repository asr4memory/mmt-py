<script setup lang="ts">
import InlineMessage from '@/components/InlineMessage.vue'

defineProps<{
  loading: boolean
  error: string | null
  onSubmit: (payload: Event) => void
}>()
</script>

<template>
  <h2>{{ $t('components.RegistrationForm.title') }}</h2>

  <InlineMessage v-if="error" type="error" class="u-mt">
    {{ $t(`${error}`) }}
  </InlineMessage>

  <form @submit="onSubmit" class="u-mt">
    <div>
      <label class="form__label" htmlFor="username">
        {{ $t('components.RegistrationForm.username') }}
      </label>
      <div class="control">
        <input
          name="username"
          type="text"
          class="form__input"
          id="username"
          required
          pattern="[A-Za-z0-9_-]{4,12}"
          :placeholder="$t('components.RegistrationForm.usernamePlaceholder')"
          autocomplete="username"
        />
      </div>
      <p class="form__help u-ll">
        {{ $t('components.RegistrationForm.usernameHelp') }}
      </p>
    </div>

    <div class="u-mt">
      <label class="form__label" htmlFor="emailInput">
        {{ $t('components.RegistrationForm.email') }}
      </label>
      <div class="control">
        <input
          name="email"
          type="email"
          class="form__input"
          id="emailInput"
          required
          :placeholder="$t('components.RegistrationForm.emailPlaceholder')"
          autocomplete="email"
        />
      </div>
    </div>

    <div class="u-mt">
      <label class="form__label" htmlFor="passwordInput">
        {{ $t('components.RegistrationForm.password') }}
      </label>
      <div class="control">
        <input
          name="password"
          type="password"
          class="form__input"
          id="passwordInput"
          required
          :placeholder="$t('components.RegistrationForm.passwordPlaceholder')"
          autocomplete="new-password"
        />
      </div>
    </div>

    <div class="field">
      <label class="form__label" htmlFor="repeatPasswordInput">
        {{ $t('components.RegistrationForm.repeatPassword') }}
      </label>
      <div class="control">
        <input
          name="repeatPassword"
          type="password"
          class="form__input"
          id="repeatPasswordInput"
          required
          :placeholder="$t('components.RegistrationForm.repeatPasswordPlaceholder')"
          autocomplete="new-password"
        />
      </div>
    </div>

    <div class="field u-mt">
      <button type="submit" class="form__button" :disabled="loading">
        {{ $t('components.RegistrationForm.submit') }}
      </button>
    </div>
  </form>
</template>
