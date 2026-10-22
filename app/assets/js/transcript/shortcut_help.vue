<script setup lang="ts">
import { useTemplateRef } from "vue";
import KeyboardIcon from "../icons/keyboard_icon.vue";
import ModalDialog from "../shared/modal_dialog.vue";

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

const modal = useTemplateRef<InstanceType<typeof ModalDialog>>("modal");

function open() {
    modal.value?.open();
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
    <ModalDialog ref="modal" :title="$t('shortcuts')">
            <div class="auto-grid auto-grid--large">
                <section
                    v-for="group in groups"
                    :key="group.heading"
                    class="stack stack--small"
                >
                    <h3 class="h-small">
                        {{ $t(group.heading) }}
                    </h3>
                    <dl class="stack stack--tiny">
                        <div
                            v-for="shortcut in group.shortcuts"
                            :key="shortcut.label"
                            class="repel"
                        >
                            <dt>{{ $t(shortcut.label) }}</dt>
                            <dd class="cluster cluster--tiny">
                                <template
                                    v-for="(key, index) in shortcut.keys"
                                    :key="key"
                                >
                                    <span
                                        v-if="index > 0 && shortcut.alternatives"
                                        class="u-color-muted u-font-tiny"
                                        >{{ $t("shortcut_or") }}</span
                                    >
                                    <kbd>{{ key }}</kbd>
                                </template>
                            </dd>
                        </div>
                    </dl>
                </section>
            </div>
    </ModalDialog>
</template>
