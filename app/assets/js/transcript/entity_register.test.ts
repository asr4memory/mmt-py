import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import EntityRegister from "./entity_register.vue";
import { useTranscriptStore } from "./transcript_store";

beforeEach(() => {
    setActivePinia(createPinia());
});

// $t returns the key followed by its argument, so that a test can read the
// count that was passed to a pluralised message.
function translate(key: string, params?: unknown) {
    return params === undefined ? key : `${key} ${JSON.stringify(params)}`;
}

function mountRegister() {
    return mount(EntityRegister, {
        global: { mocks: { $t: translate } },
    });
}

function seedRegister() {
    const store = useTranscriptStore();
    store.entities = {
        ent_z: { name: "Zürich", type: "LOC", aliases: [] },
        ent_a: { name: "Anna Seghers", type: "PER", aliases: [] },
        ent_u: { name: "UNESCO", type: "ORG", aliases: [] },
    };
    store.mentions = {
        men_1: { type: "PER", score: 1, entityId: "ent_a" },
        men_2: { type: "PER", score: 1, entityId: "ent_a" },
        men_3: { type: "LOC", score: 1, entityId: "ent_z" },
        men_4: { type: "PER", score: 1, entityId: null },
    };
    return store;
}

function rowNames(wrapper: ReturnType<typeof mountRegister>) {
    return wrapper.findAll(".entity-register__name").map((name) => name.text());
}

function rowCount(wrapper: ReturnType<typeof mountRegister>, name: string) {
    const row = wrapper
        .findAll(".entity-register__row")
        .find((candidate) => candidate.text().includes(name));
    if (row === undefined) throw new Error(`no row for ${name}`);
    return row.find(".entity-register__count").text();
}

describe("EntityRegister list", () => {
    test("lists the entities sorted by name", () => {
        seedRegister();
        const wrapper = mountRegister();

        expect(rowNames(wrapper)).toEqual(["Anna Seghers", "UNESCO", "Zürich"]);
    });

    test("shows the number of mentions linked to each entity", () => {
        seedRegister();
        const wrapper = mountRegister();

        expect(rowCount(wrapper, "Anna Seghers")).toBe(
            "entity_mention_count 2",
        );
        expect(rowCount(wrapper, "Zürich")).toBe("entity_mention_count 1");
    });

    test("shows a count of zero for an entity without mentions", () => {
        seedRegister();
        const wrapper = mountRegister();

        expect(rowCount(wrapper, "UNESCO")).toBe("entity_mention_count 0");
    });

    test("shows the type of each entity", () => {
        seedRegister();
        const wrapper = mountRegister();

        const types = wrapper
            .findAll(".entity-register__type")
            .map((type) => type.text());
        expect(types).toEqual(["entity_per", "entity_org", "entity_loc"]);
    });

    test("an empty register shows the explanation instead of a list", () => {
        const wrapper = mountRegister();

        expect(wrapper.find(".entity-register__row").exists()).toBe(false);
        expect(wrapper.text()).toContain("entity_register_empty");
    });
});
