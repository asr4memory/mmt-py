import { defineComponent } from "vue";
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
        return { speakers };
    },
    template: `
    <section class="u-mt">
        <h3>{{$t("view")}}</h3>
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
        <ul class="u-mt-none u-mb-none">
            <li v-for="speaker in speakers">
                {{speaker}}
            </li>
        </ul>
    </section>

    <section class="u-mt-small">
        <h3>{{$t("named_entities")}}</h3>
        <p class="u-mt-small u-mb-none">
            <span class="entity-legend entity-legend--per" :title="$t('entity_per')">PER</span>,
            <span class="entity-legend entity-legend--loc" :title="$t('entity_loc')">LOC</span>,
            <span class="entity-legend entity-legend--org" :title="$t('entity_org')">ORG</span>,
            <span class="entity-legend entity-legend--date" :title="$t('entity_date')">DATE</span>
        </p>
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
