<script setup lang="ts">
import { useTemplateRef } from "vue";
import CloseIcon from "../icons/close_icon.vue";
import KeyboardIcon from "../icons/keyboard_icon.vue";

interface Shortcut {
    label: string;
    keys: string[];
    // The keys are alternatives for the same action, not one key per action.
    alternatives?: boolean;
}

// The keys handled in useMediaShortcuts.ts.
const groups: { heading: string; shortcuts: Shortcut[] }[] = [
    {
        heading: "shortcut_group_playback",
        shortcuts: [
            {
                label: "shortcut_play_pause",
                keys: ["Space", "P"],
                alternatives: true,
            },
            { label: "shortcut_seek", keys: ["←", "→"] },
            { label: "shortcut_speed", keys: ["<", ">"] },
            { label: "shortcut_follow", keys: ["."] },
        ],
    },
    {
        heading: "shortcut_group_sound",
        shortcuts: [
            { label: "shortcut_volume", keys: ["⇧ ↑", "⇧ ↓"] },
            { label: "shortcut_mute", keys: ["M"] },
        ],
    },
    {
        heading: "view",
        shortcuts: [
            { label: "shortcut_fullscreen", keys: ["F"] },
            { label: "shortcut_help", keys: ["?"] },
        ],
    },
];

const dialog = useTemplateRef<HTMLDialogElement>("dialog");

function open() {
    dialog.value?.showModal();
}

function close() {
    dialog.value?.close();
}

// The backdrop belongs to the dialog element, so a click on it has the
// dialog itself as its target. The content is wrapped in an element that
// fills the dialog, so a click inside never has that target.
function closeOnBackdropClick(event: MouseEvent) {
    if (event.target === dialog.value) {
        close();
    }
}

defineExpose({ open });
</script>

<template>
    <button
        type="button"
        class="button button--small button--outline shortcut-help__open"
        @click="open"
    >
        <KeyboardIcon class="icon" />
        <span class="button__label">{{ $t("shortcuts") }}</span>
    </button>
    <dialog
        ref="dialog"
        class="shortcut-help"
        aria-labelledby="shortcut-help-title"
        @click="closeOnBackdropClick"
    >
        <div class="shortcut-help__body">
            <div class="shortcut-help__header">
                <h2 id="shortcut-help-title" class="shortcut-help__title">
                    {{ $t("shortcuts") }}
                </h2>
                <button
                    type="button"
                    class="icon-button shortcut-help__close"
                    :title="$t('close')"
                    :aria-label="$t('close')"
                    @click="close"
                >
                    <CloseIcon class="icon-button__icon" />
                </button>
            </div>
            <div class="shortcut-help__groups">
                <section
                    v-for="group in groups"
                    :key="group.heading"
                    class="shortcut-help__group"
                >
                    <h3 class="shortcut-help__heading">
                        {{ $t(group.heading) }}
                    </h3>
                    <dl class="shortcut-help__list">
                        <div
                            v-for="shortcut in group.shortcuts"
                            :key="shortcut.label"
                            class="shortcut-help__row"
                        >
                            <dt>{{ $t(shortcut.label) }}</dt>
                            <dd class="shortcut-help__keys">
                                <template
                                    v-for="(key, index) in shortcut.keys"
                                    :key="key"
                                >
                                    <span
                                        v-if="index > 0 && shortcut.alternatives"
                                        class="shortcut-help__or"
                                        >{{ $t("shortcut_or") }}</span
                                    >
                                    <kbd class="kbd">{{ key }}</kbd>
                                </template>
                            </dd>
                        </div>
                    </dl>
                </section>
            </div>
        </div>
    </dialog>
</template>
