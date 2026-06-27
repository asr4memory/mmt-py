import { describe, test, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import SpeakerLegend from "./speaker_legend.vue";
import { useTranscriptStore } from "./transcript_store";

beforeEach(() => {
    setActivePinia(createPinia());
});

function mountComponent() {
    return mount(SpeakerLegend, {
        global: { mocks: { $t: (key: string) => key } },
    });
}

function seedSpeakers() {
    const store = useTranscriptStore();
    store.speakers = [
        { id: "spk_a", name: "Alice", color: "#5b9bd5" },
        { id: "spk_b", name: "Bob", color: "#70ad47" },
    ];
    return store;
}

describe("SpeakerLegend delete", () => {
    test("clicking delete reveals an inline confirm prompt without removing the speaker", async () => {
        const store = seedSpeakers();
        const wrapper = mountComponent();

        await wrapper.findAll(".speaker-legend__delete-toggle")[0].trigger(
            "click",
        );

        // The speaker is still there until confirmed.
        expect(store.speakers).toHaveLength(2);
        expect(wrapper.find(".speaker-legend__delete-confirm").exists()).toBe(
            true,
        );
    });

    test("confirming the prompt deletes the speaker", async () => {
        const store = seedSpeakers();
        const wrapper = mountComponent();

        await wrapper.findAll(".speaker-legend__delete-toggle")[0].trigger(
            "click",
        );
        await wrapper
            .find(".speaker-legend__delete-confirm")
            .trigger("mousedown");

        expect(store.speakers).toHaveLength(1);
        expect(store.speakers[0].name).toBe("Bob");
    });

    test("cancelling the prompt keeps the speaker", async () => {
        const store = seedSpeakers();
        const wrapper = mountComponent();

        await wrapper.findAll(".speaker-legend__delete-toggle")[0].trigger(
            "click",
        );
        await wrapper
            .find(".speaker-legend__delete-cancel")
            .trigger("mousedown");

        expect(store.speakers).toHaveLength(2);
        expect(wrapper.find(".speaker-legend__delete-confirm").exists()).toBe(
            false,
        );
    });
});
