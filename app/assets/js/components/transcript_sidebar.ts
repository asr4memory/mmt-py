import { defineComponent, ref, computed, watch, nextTick } from "vue";
import { storeToRefs } from "pinia";

import { useTranscriptStore } from "../transcript_store";

export default defineComponent({
    name: "TranscriptSidebar",
    props: {
        showConfidence: { type: Boolean, required: true },
        showEntities: { type: Boolean, required: true },
        showEdits: { type: Boolean, required: true },
        autoScroll: { type: Boolean, required: true },
    },
    emits: [
        "update:showConfidence",
        "update:showEntities",
        "update:showEdits",
        "update:autoScroll",
    ],
    setup() {
        const store = useTranscriptStore();
        const { speakers } = storeToRefs(store);

        const showAddForm = ref(false);
        const newSpeakerName = ref("");
        const addInput = ref<HTMLInputElement | null>(null);

        watch(showAddForm, (val) => {
            if (val) nextTick(() => addInput.value?.focus());
        });

        const canAdd = computed(
            () =>
                newSpeakerName.value.trim() !== "" &&
                !speakers.value.some(
                    (s) => s.name === newSpeakerName.value.trim(),
                ),
        );

        function openAddForm() {
            newSpeakerName.value = "";
            showAddForm.value = true;
        }

        function cancelAdd() {
            showAddForm.value = false;
        }

        function confirmAdd() {
            if (!canAdd.value) return;
            store.addSpeaker(newSpeakerName.value);
            showAddForm.value = false;
        }

        return { speakers, showAddForm, newSpeakerName, canAdd, openAddForm, cancelAdd, confirmAdd, addInput };
    },
    template: `
    <section>
        <h3 class="u-mt-none">{{$t("view")}}</h3>
        <label class="view-row">
            <input type="checkbox" class="view-toggle" :checked="showConfidence" @change="$emit('update:showConfidence', $event.target.checked)" />
            <span>{{$t('show_confidence')}}</span>
        </label>
        <label class="view-row">
            <input type="checkbox" class="view-toggle" :checked="showEntities" @change="$emit('update:showEntities', $event.target.checked)" />
            <span>{{$t('show_entities')}}</span>
        </label>
        <label class="view-row">
            <input type="checkbox" class="view-toggle" :checked="showEdits" @change="$emit('update:showEdits', $event.target.checked)" />
            <span>{{$t('show_edits')}}</span>
        </label>
        <label class="view-row">
            <input type="checkbox" class="view-toggle" :checked="autoScroll" @change="$emit('update:autoScroll', $event.target.checked)" />
            <span>{{$t('auto_scroll')}}</span>
        </label>
    </section>

    <section class="u-mt-small">
        <h3>{{$t("speakers")}}</h3>
        <ul class="speaker-legend u-mt-none u-mb-none">
            <li v-for="speaker in speakers" :key="speaker.name" class="speaker-legend__item">
                <span class="speaker-legend__swatch" :style="{ backgroundColor: speaker.color }"></span>
                {{speaker.name}}
            </li>
        </ul>
        <button v-if="!showAddForm" class="speaker-legend__add-toggle" @click="openAddForm">+ {{$t("add_speaker")}}</button>
        <div v-else class="speaker-legend__add-form">
            <input type="text" ref="addInput" v-model="newSpeakerName" :placeholder="$t('speaker_name')" @keyup.enter="confirmAdd" />
            <div class="speaker-legend__add-actions">
                <button :disabled="!canAdd" @click="confirmAdd">{{$t("add")}}</button>
                <button @click="cancelAdd">{{$t("cancel")}}</button>
            </div>
        </div>
    </section>

    <section class="u-mt-small">
        <h3>{{$t("named_entities")}}</h3>
        <ul class="entity-legend-list u-mt-none u-mb-none">
            <li class="entity-legend-list__item">
                <span class="entity-legend-list__swatch entity-legend-list__swatch--per"></span>
                {{$t('entity_per')}}
            </li>
            <li class="entity-legend-list__item">
                <span class="entity-legend-list__swatch entity-legend-list__swatch--loc"></span>
                {{$t('entity_loc')}}
            </li>
            <li class="entity-legend-list__item">
                <span class="entity-legend-list__swatch entity-legend-list__swatch--org"></span>
                {{$t('entity_org')}}
            </li>
            <li class="entity-legend-list__item">
                <span class="entity-legend-list__swatch entity-legend-list__swatch--date"></span>
                {{$t('entity_date')}}
            </li>
        </ul>
    </section>

    <!-- <section class="u-mt-small">
        <h3>{{$t("shortcuts")}}</h3>
        <div class="shortcuts">
            <div class="shortcut"><span class="shortcut__label">{{$t('shortcut_play_pause')}}</span><kbd class="kbd">Space</kbd></div>
            <div class="shortcut"><span class="shortcut__label">{{$t('shortcut_back')}}</span><kbd class="kbd">⌥ ←</kbd></div>
            <div class="shortcut"><span class="shortcut__label">{{$t('shortcut_forward')}}</span><kbd class="kbd">⌥ →</kbd></div>
        </div>
    </section> -->
    `,
});
