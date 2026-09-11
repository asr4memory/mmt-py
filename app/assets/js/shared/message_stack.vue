<script setup lang="ts">
import { storeToRefs } from "pinia";

import { type Message, useMessagesStore } from "./messages_store";

// Same markup as the Django `_messages.html` template, styled by messages.css.
const store = useMessagesStore();
const { messages } = storeToRefs(store);

const DISMISS_ANIMATIONS = ["message-dismiss", "message-dismiss-motion"];

function isPersistent(message: Message): boolean {
    return message.level === "error" || message.level === "warning";
}

function onAnimationEnd(message: Message, event: AnimationEvent) {
    if (DISMISS_ANIMATIONS.includes(event.animationName)) {
        store.remove(message.id);
    }
}
</script>

<template>
    <div
        v-if="messages.length > 0"
        class="message-stack"
        data-placement="top"
        role="region"
        aria-label="Messages"
    >
        <div
            v-for="message in messages"
            :key="message.id"
            class="message"
            :data-level="message.level"
            :role="message.level === 'error' ? 'alert' : 'status'"
            @animationend="onAnimationEnd(message, $event)"
        >
            <span class="message__icon" aria-hidden="true">
                <svg
                    v-if="message.level === 'success'"
                    viewBox="0 0 24 24"
                    focusable="false"
                >
                    <circle cx="12" cy="12" r="10" />
                    <path d="m9 12 2 2 4-4" />
                </svg>
                <svg
                    v-else-if="message.level === 'warning'"
                    viewBox="0 0 24 24"
                    focusable="false"
                >
                    <path
                        d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"
                    />
                    <path d="M12 9v4" />
                    <path d="M12 17h.01" />
                </svg>
                <svg
                    v-else-if="message.level === 'error'"
                    viewBox="0 0 24 24"
                    focusable="false"
                >
                    <circle cx="12" cy="12" r="10" />
                    <path d="m15 9-6 6" />
                    <path d="m9 9 6 6" />
                </svg>
                <svg v-else viewBox="0 0 24 24" focusable="false">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 16v-4" />
                    <path d="M12 8h.01" />
                </svg>
            </span>
            <p class="message__text">{{ message.text }}</p>
            <button
                v-if="isPersistent(message)"
                type="button"
                class="message__close"
                :aria-label="$t('dismiss')"
                @click="store.remove(message.id)"
            >
                <svg viewBox="0 0 24 24" focusable="false">
                    <path d="M18 6 6 18" />
                    <path d="m6 6 12 12" />
                </svg>
            </button>
        </div>
    </div>
</template>
