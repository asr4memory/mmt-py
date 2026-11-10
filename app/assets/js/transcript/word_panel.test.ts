import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";
import EntityCombobox from "./entity_combobox.vue";
import { useTranscriptStore } from "./transcript_store";
import type { Entity, Mention, TranscriptWord } from "./types";
import WordPanel from "./word_panel.vue";

const WORD: TranscriptWord = {
    id: "wrd_1",
    start: 1.5,
    end: 2.25,
    word: "hello",
    score: 0.92,
    speakerId: "spk_a",
};

function mountPanel(word: TranscriptWord = WORD) {
    return mount(WordPanel, {
        props: {
            segmentIndex: 3,
            index: 7,
            word,
        },
        global: {
            mocks: { $t: (key: string) => key },
        },
    });
}

// A panel on one word of a segment that is in the store, which is what the
// split action needs: it reads the segment of the word to find its id and the
// word that follows.
function mountInSegment(words: TranscriptWord[], index: number) {
    const store = useTranscriptStore();
    store.segments = [
        { id: "seg_1", start: 0, end: 5, speakerId: null, words },
    ];
    const wrapper = mount(WordPanel, {
        props: {
            segmentIndex: 0,
            index,
            word: words[index],
        },
        global: {
            mocks: { $t: (key: string) => key },
        },
    });
    return { wrapper, store };
}

function wordOf(id: string, extra: Partial<TranscriptWord> = {}) {
    return {
        id,
        start: 0,
        end: 1,
        word: id,
        score: 1,
        speakerId: null,
        ...extra,
    } as TranscriptWord;
}

beforeEach(() => {
    setActivePinia(createPinia());
});

describe("WordPanel", () => {
    test("renders the four word action buttons", () => {
        const wrapper = mountPanel();

        const buttons = wrapper.findAll(".popup__section")[0].findAll("button");
        expect(buttons).toHaveLength(4);
        expect(buttons.map((b) => b.attributes("title"))).toEqual([
            "add_word_left",
            "add_word_right",
            "split_segment_after",
            "remove_word",
        ]);
    });

    test("split button splits the segment after the word", async () => {
        const { wrapper, store } = mountInSegment(
            [wordOf("w1"), wordOf("w2")],
            0,
        );
        const spy = vi
            .spyOn(store, "splitSegmentAfterWord")
            .mockImplementation(() => {});

        await wrapper.find("[title='split_segment_after']").trigger("click");

        expect(spy).toHaveBeenCalledWith("seg_1", 0);
    });

    test("disables the split action on the last word of the segment", () => {
        const { wrapper } = mountInSegment([wordOf("w1"), wordOf("w2")], 1);

        expect(
            wrapper
                .find("[title='split_segment_after']")
                .attributes("disabled"),
        ).toBeDefined();
    });

    test("disables the split action inside a mention or a redaction", () => {
        const inMention = mountInSegment(
            [
                wordOf("w1", { mentionId: "men_1" }),
                wordOf("w2", { mentionId: "men_1" }),
            ],
            0,
        ).wrapper;
        const inRedaction = mountInSegment(
            [
                wordOf("w1", { redactionId: "red_1" }),
                wordOf("w2", { redactionId: "red_1" }),
            ],
            0,
        ).wrapper;

        expect(
            inMention
                .find("[title='split_segment_after']")
                .attributes("disabled"),
        ).toBeDefined();
        expect(
            inRedaction
                .find("[title='split_segment_after']")
                .attributes("disabled"),
        ).toBeDefined();
    });

    test("renders the score", () => {
        const wrapper = mountPanel();

        expect(wrapper.text()).toContain("confidence");
    });

    test("add-left button inserts a word", async () => {
        const store = useTranscriptStore();
        const spy = vi.spyOn(store, "insertLeft").mockImplementation(() => {});

        const wrapper = mountPanel();
        await wrapper.find("[title='add_word_left']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7);
    });

    test("add-right button inserts a word", async () => {
        const store = useTranscriptStore();
        const spy = vi.spyOn(store, "insertRight").mockImplementation(() => {});

        const wrapper = mountPanel();
        await wrapper.find("[title='add_word_right']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7);
    });

    test("remove button deletes the word", async () => {
        const store = useTranscriptStore();
        const spy = vi.spyOn(store, "deleteWord").mockImplementation(() => {});

        const wrapper = mountPanel();
        await wrapper.find("[title='remove_word']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7);
    });

    test("shows an empty mention section with a create action when unlinked", () => {
        const wrapper = mountPanel();

        // The word, mention and redaction sections are present, but the
        // mention section has no entity details yet.
        expect(wrapper.findAll(".popup__section")).toHaveLength(3);
        expect(wrapper.find(".popup__select").exists()).toBe(false);
        expect(wrapper.text()).not.toContain("entity_type");
        expect(wrapper.find("[title='set_as_mention']").exists()).toBe(true);
    });

    test("set-as-mention creates a mention for the word", async () => {
        const store = useTranscriptStore();
        const spy = vi
            .spyOn(store, "createMention")
            .mockImplementation(() => {});

        const wrapper = mountPanel();
        await wrapper.find("[title='set_as_mention']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7, "PER");
    });

    function mountMentionPanel() {
        const store = useTranscriptStore();
        store.mentions = {
            men_1: { type: "LOC", score: 0.76, entityId: null },
        };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_a", word: "New", mentionId: "men_1" },
                    { id: "w_b", word: "York", mentionId: "men_1" },
                ],
            },
        ] as any;

        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "York",
            score: 0.9,
            mentionId: "men_1",
        };
        return { store, wrapper: mountPanel(word) };
    }

    test("shows the entity type and full mention text for a mention word", () => {
        const { wrapper } = mountMentionPanel();

        // Two sections: the word, then the mention.
        const titles = wrapper.findAll(".popup__title");
        expect(titles).toHaveLength(2);
        // The full mention surface form as a heading, not just the clicked word.
        expect(titles[1].text()).toBe("New York");
        expect(wrapper.text()).toContain("entity_type");

        // The type is an editable select preset to the mention's type.
        const select = wrapper.find(".popup__select");
        expect((select.element as HTMLSelectElement).value).toBe("LOC");
        expect(
            select.findAll("option").map((o) => o.attributes("value")),
        ).toEqual(["PER", "LOC", "ORG", "DATE"]);
    });

    test("changing the type select changes the mention's type", async () => {
        const { store, wrapper } = mountMentionPanel();
        const spy = vi
            .spyOn(store, "setMentionType")
            .mockImplementation(() => {});

        await wrapper.find(".popup__select").setValue("PER");

        expect(spy).toHaveBeenCalledWith(3, "men_1", "PER");
    });

    test("remove-mention button removes the whole mention", async () => {
        const { store, wrapper } = mountMentionPanel();
        const spy = vi
            .spyOn(store, "removeMention")
            .mockImplementation(() => {});

        await wrapper.find("[title='remove_mention']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, "men_1");
    });

    test("disables extend when the span already fills the segment", () => {
        // The mention of mountMentionPanel covers every word in the segment.
        const { wrapper } = mountMentionPanel();

        expect(
            wrapper
                .find("[title='extend_mention_left']")
                .attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper
                .find("[title='extend_mention_right']")
                .attributes("disabled"),
        ).toBeDefined();
    });

    // Mention "New York" flanked by a free word on each side.
    function mountMentionWithNeighbours() {
        const store = useTranscriptStore();
        store.mentions = {
            men_1: { type: "LOC", score: 0.76, entityId: null },
        };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "in", mentionId: null },
                    { id: "w_a", word: "New", mentionId: "men_1" },
                    { id: "w_b", word: "York", mentionId: "men_1" },
                    { id: "w_y", word: "today", mentionId: null },
                ],
            },
        ] as any;

        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "York",
            score: 0.9,
            mentionId: "men_1",
        };
        return { store, wrapper: mountPanel(word) };
    }

    test("extend buttons grow the mention", async () => {
        const { store, wrapper } = mountMentionWithNeighbours();
        const spy = vi
            .spyOn(store, "extendMention")
            .mockImplementation(() => {});

        const left = wrapper.find("[title='extend_mention_left']");
        const right = wrapper.find("[title='extend_mention_right']");
        expect(left.attributes("disabled")).toBeUndefined();
        expect(right.attributes("disabled")).toBeUndefined();

        await left.trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "men_1", "left");

        await right.trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "men_1", "right");
    });

    test("reduce buttons trim the span", async () => {
        const { store, wrapper } = mountMentionWithNeighbours();
        const spy = vi
            .spyOn(store, "reduceMention")
            .mockImplementation(() => {});

        await wrapper.find("[title='reduce_mention_left']").trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "men_1", "left");

        await wrapper.find("[title='reduce_mention_right']").trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "men_1", "right");
    });

    test("disables reduce for a single-word mention", () => {
        const store = useTranscriptStore();
        store.mentions = {
            men_1: { type: "LOC", score: 0.76, entityId: null },
        };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "in", mentionId: null },
                    { id: "w_b", word: "York", mentionId: "men_1" },
                    { id: "w_y", word: "today", mentionId: null },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "York",
            score: 0.9,
            mentionId: "men_1",
        };
        const wrapper = mountPanel(word);

        expect(
            wrapper
                .find("[title='reduce_mention_left']")
                .attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper
                .find("[title='reduce_mention_right']")
                .attributes("disabled"),
        ).toBeDefined();
        // But a single-word mention flanked by free words can still grow.
        expect(
            wrapper
                .find("[title='extend_mention_left']")
                .attributes("disabled"),
        ).toBeUndefined();
    });
});

describe("WordPanel redaction section", () => {
    // Redaction "at Acme" with a free word on each side, in segment 3.
    function mountRedactionPanel(reason: string | null = null) {
        const store = useTranscriptStore();
        store.redactions = { red_1: { reason, start: null, end: null } };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "I", redactionId: null },
                    { id: "w_a", word: "at", redactionId: "red_1" },
                    { id: "w_b", word: "Acme", redactionId: "red_1" },
                    { id: "w_y", word: "today", redactionId: null },
                ],
            },
        ] as any;

        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Acme",
            score: 0.9,
            redactionId: "red_1",
        };
        return { store, wrapper: mountPanel(word) };
    }

    test("shows the empty state with a redact action for an unredacted word", () => {
        const wrapper = mountPanel();

        expect(wrapper.text()).toContain("no_redaction");
        expect(wrapper.find("[title='set_as_redaction']").exists()).toBe(true);
        expect(wrapper.find(".popup__input").exists()).toBe(false);
        expect(wrapper.find("[title='remove_redaction']").exists()).toBe(false);
    });

    test("redact button creates a redaction for the word", async () => {
        const store = useTranscriptStore();
        const spy = vi
            .spyOn(store, "createRedaction")
            .mockImplementation(() => "red_new");

        const wrapper = mountPanel();
        await wrapper.find("[title='set_as_redaction']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7);
    });

    test("shows the surface text of the whole run for a redacted word", () => {
        const { wrapper } = mountRedactionPanel();

        // Three sections: the word, the (empty) mention, then the redaction.
        expect(wrapper.findAll(".popup__section")).toHaveLength(3);
        const titles = wrapper.findAll(".popup__title");
        // The word's own title, then the redaction's full surface form.
        expect(titles).toHaveLength(2);
        expect(titles[1].text()).toBe("at Acme");
        expect(wrapper.text()).not.toContain("no_redaction");
    });

    test("shows the stored reason in the reason input", () => {
        const { wrapper } = mountRedactionPanel("employer");

        const input = wrapper.find(".popup__input");
        expect((input.element as HTMLInputElement).value).toBe("employer");
    });

    test("shows an empty reason input when the redaction carries none", () => {
        const { wrapper } = mountRedactionPanel(null);

        expect(
            (wrapper.find(".popup__input").element as HTMLInputElement).value,
        ).toBe("");
    });

    test("typing a reason records it", async () => {
        const { store, wrapper } = mountRedactionPanel();
        const spy = vi
            .spyOn(store, "setRedactionReason")
            .mockImplementation(() => {});

        await wrapper.find(".popup__input").setValue("employer");

        expect(spy).toHaveBeenCalledWith("red_1", "employer");
    });

    test("extend buttons grow the redaction", async () => {
        const { store, wrapper } = mountRedactionPanel();
        const spy = vi
            .spyOn(store, "extendRedaction")
            .mockImplementation(() => {});

        const left = wrapper.find("[title='extend_redaction_left']");
        const right = wrapper.find("[title='extend_redaction_right']");
        expect(left.attributes("disabled")).toBeUndefined();
        expect(right.attributes("disabled")).toBeUndefined();

        await left.trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "red_1", "left");

        await right.trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "red_1", "right");
    });

    test("reduce buttons shorten the run", async () => {
        const { store, wrapper } = mountRedactionPanel();
        const spy = vi
            .spyOn(store, "reduceRedaction")
            .mockImplementation(() => {});

        await wrapper.find("[title='reduce_redaction_left']").trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "red_1", "left");

        await wrapper.find("[title='reduce_redaction_right']").trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "red_1", "right");
    });

    test("remove button removes the whole redaction", async () => {
        const { store, wrapper } = mountRedactionPanel("employer");
        const spy = vi
            .spyOn(store, "removeRedaction")
            .mockImplementation(() => {});

        await wrapper.find("[title='remove_redaction']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, "red_1");
    });

    test("disables extend when the run already fills the segment", () => {
        const store = useTranscriptStore();
        store.redactions = { red_1: { reason: null, start: null, end: null } };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_a", word: "at", redactionId: "red_1" },
                    { id: "w_b", word: "Acme", redactionId: "red_1" },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Acme",
            score: 0.9,
            redactionId: "red_1",
        };
        const wrapper = mountPanel(word);

        expect(
            wrapper
                .find("[title='extend_redaction_left']")
                .attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper
                .find("[title='extend_redaction_right']")
                .attributes("disabled"),
        ).toBeDefined();
    });

    test("disables extend onto a word held by another redaction", () => {
        const store = useTranscriptStore();
        store.redactions = {
            red_1: { reason: null, start: null, end: null },
            red_2: { reason: null, start: null, end: null },
        };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "Berlin", redactionId: "red_2" },
                    { id: "w_b", word: "Acme", redactionId: "red_1" },
                    { id: "w_y", word: "today", redactionId: null },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Acme",
            score: 0.9,
            redactionId: "red_1",
        };
        const wrapper = mountPanel(word);

        expect(
            wrapper
                .find("[title='extend_redaction_left']")
                .attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper
                .find("[title='extend_redaction_right']")
                .attributes("disabled"),
        ).toBeUndefined();
    });

    test("disables reduce for a single-word redaction", () => {
        const store = useTranscriptStore();
        store.redactions = { red_1: { reason: null, start: null, end: null } };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "at", redactionId: null },
                    { id: "w_b", word: "Acme", redactionId: "red_1" },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Acme",
            score: 0.9,
            redactionId: "red_1",
        };
        const wrapper = mountPanel(word);

        expect(
            wrapper
                .find("[title='reduce_redaction_left']")
                .attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper
                .find("[title='reduce_redaction_right']")
                .attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper
                .find("[title='extend_redaction_left']")
                .attributes("disabled"),
        ).toBeUndefined();
    });
});

describe("WordPanel entity row", () => {
    // Mention "Angela Merkel" in segment 3, with the given mention and register.
    function mountEntityPanel(
        mention: Mention,
        entities: Record<string, Entity> = {},
    ) {
        const store = useTranscriptStore();
        store.entities = entities;
        store.mentions = { men_1: mention };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_a", word: "Angela", mentionId: "men_1" },
                    { id: "w_b", word: "Merkel,", mentionId: "men_1" },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Merkel,",
            score: 0.9,
            mentionId: "men_1",
        };
        return { store, wrapper: mountPanel(word) };
    }

    const MERKEL: Entity = {
        name: "Angela Merkel",
        type: "PER",
        wikidataId: "Q567",
    };

    test("shows no entity row for a DATE mention", () => {
        const { wrapper } = mountEntityPanel({
            type: "DATE",
            score: 1,
            entityId: null,
        });

        expect(wrapper.findComponent(EntityCombobox).exists()).toBe(false);
        expect(wrapper.text()).not.toContain("entity_section");
    });

    test("an unlinked mention shows the combobox with its trimmed surface text and the type selector", () => {
        const { wrapper } = mountEntityPanel({
            type: "PER",
            score: 1,
            entityId: null,
        });

        const combobox = wrapper.findComponent(EntityCombobox);
        expect(combobox.exists()).toBe(true);
        expect(combobox.props("proposedName")).toBe("Angela Merkel");
        expect(wrapper.find(".popup__select").exists()).toBe(true);
    });

    test("picking an entity links the mention", async () => {
        const { store, wrapper } = mountEntityPanel(
            { type: "PER", score: 1, entityId: null },
            { ent_1: MERKEL },
        );

        wrapper.findComponent(EntityCombobox).vm.$emit("select", "ent_1");
        await wrapper.vm.$nextTick();

        expect(store.mentions.men_1.entityId).toBe("ent_1");
        expect(wrapper.findComponent(EntityCombobox).exists()).toBe(false);
    });

    test("creating an entity adds it with the mention's type and links the mention", async () => {
        const { store, wrapper } = mountEntityPanel({
            type: "ORG",
            score: 1,
            entityId: null,
        });

        wrapper.findComponent(EntityCombobox).vm.$emit("create", "Merkel AG");
        await wrapper.vm.$nextTick();

        const entityId = store.mentions.men_1.entityId as string;
        expect(store.entities[entityId]).toMatchObject({
            name: "Merkel AG",
            type: "ORG",
        });
    });

    test("a linked mention shows the entity's name without the type selector", () => {
        const { wrapper } = mountEntityPanel(
            { type: "PER", score: 1, entityId: "ent_1" },
            { ent_1: MERKEL },
        );

        expect(wrapper.find(".popup__entity").text()).toContain(
            "Angela Merkel",
        );
        expect(wrapper.find(".popup__select").exists()).toBe(false);
        expect(wrapper.findComponent(EntityCombobox).exists()).toBe(false);
    });

    test("unlink returns the row to the combobox and keeps the entity", async () => {
        const { store, wrapper } = mountEntityPanel(
            { type: "PER", score: 1, entityId: "ent_1" },
            { ent_1: MERKEL },
        );

        await wrapper.find("[title='entity_unlink']").trigger("click");

        expect(store.mentions.men_1.entityId).toBeNull();
        expect(Object.keys(store.entities)).toEqual(["ent_1"]);
        expect(wrapper.findComponent(EntityCombobox).exists()).toBe(true);
    });

    test("change reopens the combobox and picking relinks the mention", async () => {
        const { store, wrapper } = mountEntityPanel(
            { type: "PER", score: 1, entityId: "ent_1" },
            {
                ent_1: MERKEL,
                ent_2: { name: "Merkel AG", type: "ORG" },
            },
        );

        await wrapper.find("[title='entity_change']").trigger("click");
        wrapper.findComponent(EntityCombobox).vm.$emit("select", "ent_2");
        await wrapper.vm.$nextTick();

        expect(store.mentions.men_1).toMatchObject({
            entityId: "ent_2",
            type: "ORG",
        });
        expect(wrapper.find(".popup__entity").text()).toContain("Merkel AG");
    });

    test("change passes the current entity to the combobox", async () => {
        const { wrapper } = mountEntityPanel(
            { type: "PER", score: 1, entityId: "ent_1" },
            { ent_1: MERKEL },
        );

        await wrapper.find("[title='entity_change']").trigger("click");

        expect(wrapper.findComponent(EntityCombobox).props("entityId")).toBe(
            "ent_1",
        );
    });

    test("cancelling a change returns to the linked form", async () => {
        const { store, wrapper } = mountEntityPanel(
            { type: "PER", score: 1, entityId: "ent_1" },
            { ent_1: MERKEL },
        );

        await wrapper.find("[title='entity_change']").trigger("click");
        wrapper.findComponent(EntityCombobox).vm.$emit("cancel");
        await wrapper.vm.$nextTick();

        expect(store.mentions.men_1.entityId).toBe("ent_1");
        expect(wrapper.find(".popup__entity").exists()).toBe(true);
    });
});
