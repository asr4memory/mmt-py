<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import InlineMessage from '@/components/InlineMessage.vue'

const store = useAuthStore()

function handleSubmit(event: Event) {
  event.preventDefault()
  const form = event?.target as HTMLFormElement
  const elements = form.elements

  const usernameInput = elements[0] as HTMLInputElement
  const passwordInput = elements[1] as HTMLInputElement
  const username = usernameInput.value
  const password = passwordInput.value

  store.login(username, password)
}
</script>

<template>
  <InlineMessage v-if="store.error" type="error" class="u-mt">
    {{ $t(`${store.error}`) }}
  </InlineMessage>

  <form @submit="handleSubmit" class="form u-mt">
    <div>
      <label class="form__label" htmlFor="username">
        {{ $t('components.LoginForm.username') }}
      </label>
      <div class="form__control">
        <input
          class="form__input"
          id="username"
          name="username"
          :placeholder="$t('components.LoginForm.usernamePlaceholder')"
          autocomplete="username"
          minLength="4"
          maxLength="12"
          required
        />
      </div>
    </div>
    <div class="u-mt-1/2">
      <label class="form__label" htmlFor="password">
        {{ $t('components.LoginForm.password') }}
      </label>
      <div class="form__control">
        <input
          class="form__input"
          type="password"
          id="password"
          name="password"
          :placeholder="$t('components.LoginForm.passwordPlaceholder')"
          autocomplete="current-password"
          minLength="8"
          maxLength="40"
          required
        />
      </div>
    </div>
    <div class="u-mt">
      <button type="submit" class="form__button">
        {{ $t('components.LoginForm.submit') }}
      </button>
    </div>
  </form>
</template>
