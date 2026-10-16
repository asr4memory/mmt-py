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
        ent_z: { name: "Zürich", type: "LOC" },
        ent_a: {
            name: "Anna Seghers",
            type: "PER",
            wikidataId: "Q61597",
        },
        ent_u: { name: "UNESCO", type: "ORG" },
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
    return wrapper
        .findAll(".entity-register-row__name")
        .map((name) => name.text());
}

function row(wrapper: ReturnType<typeof mountRegister>, name: string) {
    const found = wrapper
        .findAll(".entity-register-row")
        .find((candidate) => candidate.text().includes(name));
    if (found === undefined) throw new Error(`no row for ${name}`);
    return found;
}

function rowCount(wrapper: ReturnType<typeof mountRegister>, name: string) {
    const count = row(wrapper, name).find(".entity-register-row__count");
    return {
        text: count.text(),
        label: count.attributes("aria-label"),
    };
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

        expect(rowCount(wrapper, "Anna Seghers")).toEqual({
            text: 'entity_mention_count_short {"count":2}',
            label: "entity_mention_count 2",
        });
        expect(rowCount(wrapper, "Zürich").text).toBe(
            'entity_mention_count_short {"count":1}',
        );
    });

    test("shows a count of zero for an entity without mentions", () => {
        seedRegister();
        const wrapper = mountRegister();

        expect(rowCount(wrapper, "UNESCO").text).toBe(
            'entity_mention_count_short {"count":0}',
        );
    });

    test("links the Wikidata ID only when the entity has one", () => {
        seedRegister();
        const wrapper = mountRegister();

        const link = row(wrapper, "Anna Seghers").find("a");
        expect(link.attributes("href")).toBe(
            "https://www.wikidata.org/wiki/Q61597",
        );
        expect(link.text()).toBe("Q61597");
        expect(row(wrapper, "UNESCO").find("a").exists()).toBe(false);
    });
});
