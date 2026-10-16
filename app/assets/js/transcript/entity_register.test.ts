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
        ent_a: {
            name: "Anna Seghers",
            type: "PER",
            aliases: ["Netty Reiling", "Seghers"],
            wikidataId: "Q61597",
        },
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

function seedEntities(count: number) {
    const store = useTranscriptStore();
    const names = [
        "Anna Seghers",
        "Berlin",
        "Bonn",
        "Christa Wolf",
        "DEFA",
        "Leipzig",
        "Potsdam",
        "Stasi",
        "UNESCO",
    ];
    store.entities = Object.fromEntries(
        names.slice(0, count).map((name, index) => [
            `ent_${index}`,
            {
                name,
                type: "PER" as const,
                aliases: name === "Anna Seghers" ? ["Netty Reiling"] : [],
            },
        ]),
    );
    return store;
}

describe("EntityRegister search", () => {
    test("is absent for eight entities", () => {
        seedEntities(8);
        const wrapper = mountRegister();

        expect(wrapper.find(".entity-register__search").exists()).toBe(false);
    });

    test("appears above eight entities and filters on name and aliases", async () => {
        seedEntities(9);
        const wrapper = mountRegister();

        const search = wrapper.find(".entity-register__search");
        await search.setValue("BO");
        expect(rowNames(wrapper)).toEqual(["Bonn"]);

        await search.setValue("reiling");
        expect(rowNames(wrapper)).toEqual(["Anna Seghers"]);
    });
});

async function openAddForm(wrapper: ReturnType<typeof mountRegister>) {
    await wrapper.find(".entity-register__add-toggle").trigger("click");
    return wrapper.find(".entity-register__add-form");
}

describe("EntityRegister add form", () => {
    test("creates an entity of the chosen type without mentions", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openAddForm(wrapper);
        await form.find(".entity-register__add-name").setValue(" Leipzig ");
        await form.find(".entity-register__add-type").setValue("LOC");
        await form.find(".entity-register__add-confirm").trigger("click");

        const created = Object.entries(store.entities).find(
            ([, entity]) => entity.name === "Leipzig",
        );
        expect(created?.[1].type).toBe("LOC");
        expect(store.mentionCount(created?.[0] ?? "")).toBe(0);
        expect(rowCount(wrapper, "Leipzig").text).toBe(
            'entity_mention_count_short {"count":0}',
        );
        expect(wrapper.find(".entity-register__add-form").exists()).toBe(false);
    });

    test("defaults to the type PER", async () => {
        seedRegister();
        const wrapper = mountRegister();

        const form = await openAddForm(wrapper);

        expect(
            (
                form.find(".entity-register__add-type")
                    .element as HTMLSelectElement
            ).value,
        ).toBe("PER");
    });

    test("cannot be confirmed with an empty name", async () => {
        seedRegister();
        const wrapper = mountRegister();

        const form = await openAddForm(wrapper);
        await form.find(".entity-register__add-name").setValue(" ... ");

        expect(
            form.find(".entity-register__add-confirm").attributes("disabled"),
        ).toBeDefined();
    });

    test("cannot be confirmed with a name another entity has as alias", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openAddForm(wrapper);
        await form.find(".entity-register__add-name").setValue("seghers,");
        await form.find(".entity-register__add-confirm").trigger("click");

        expect(form.text()).toContain("entity_name_taken");
        expect(Object.keys(store.entities)).toHaveLength(3);
    });
});

async function openEditForm(
    wrapper: ReturnType<typeof mountRegister>,
    name: string,
) {
    await row(wrapper, name)
        .find(".entity-register-row__edit")
        .trigger("click");
    return wrapper.find(".entity-edit-form");
}

describe("EntityRegister edit form", () => {
    test("writes the name, type, aliases and Wikidata ID", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "UNESCO");
        await form.find(".entity-edit-form__name").setValue("Unesco");
        await form.find(".entity-edit-form__type").setValue("PER");
        await form.find(".entity-edit-form__add-alias").trigger("click");
        await wrapper
            .find(".entity-edit-form__alias")
            .setValue(
                "United Nations Educational, Scientific and Cultural Organization",
            );
        await form.find(".entity-edit-form__wikidata").setValue("Q7809");
        await form.find(".entity-edit-form__confirm").trigger("click");

        expect(store.entities.ent_u).toEqual({
            name: "Unesco",
            type: "PER",
            aliases: [
                "United Nations Educational, Scientific and Cultural Organization",
            ],
            wikidataId: "Q7809",
        });
        expect(wrapper.find(".entity-edit-form").exists()).toBe(false);
    });

    test("removes an alias", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "Anna Seghers");
        await form
            .findAll(".entity-edit-form__remove-alias")[0]
            .trigger("click");
        await form.find(".entity-edit-form__confirm").trigger("click");

        expect(store.entities.ent_a.aliases).toEqual(["Seghers"]);
    });

    test("drops an alias that repeats its own name", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "Zürich");
        await form.find(".entity-edit-form__add-alias").trigger("click");
        await wrapper.find(".entity-edit-form__alias").setValue("ZÜRICH!");
        await form.find(".entity-edit-form__confirm").trigger("click");

        expect(store.entities.ent_z.aliases).toEqual([]);
    });

    test("cannot be confirmed with an empty name", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "UNESCO");
        await form.find(".entity-edit-form__name").setValue("");
        await form.find(".entity-edit-form__confirm").trigger("click");

        expect(
            form.find(".entity-edit-form__confirm").attributes("disabled"),
        ).toBeDefined();
        expect(store.entities.ent_u.name).toBe("UNESCO");
    });

    test("cannot be confirmed with a name another entity has", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "UNESCO");
        await form.find(".entity-edit-form__name").setValue("zürich");
        await form.find(".entity-edit-form__confirm").trigger("click");

        expect(form.text()).toContain("entity_name_taken");
        expect(store.entities.ent_u.name).toBe("UNESCO");
    });

    test("cannot be confirmed with an alias another entity has", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "UNESCO");
        await form.find(".entity-edit-form__add-alias").trigger("click");
        await wrapper.find(".entity-edit-form__alias").setValue("Seghers");
        await form.find(".entity-edit-form__confirm").trigger("click");

        expect(form.text()).toContain("entity_name_taken");
        expect(store.entities.ent_u.aliases).toEqual([]);
    });

    test("marks a malformed Wikidata ID as invalid", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "UNESCO");
        const wikidata = form.find(".entity-edit-form__wikidata");
        await wikidata.setValue("Q0");
        await form.find(".entity-edit-form__confirm").trigger("click");

        expect(wikidata.attributes("aria-invalid")).toBe("true");
        expect(store.entities.ent_u.wikidataId).toBeUndefined();
    });

    test("cannot be confirmed with a Wikidata ID another entity has", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "UNESCO");
        await form.find(".entity-edit-form__wikidata").setValue("Q61597");
        await form.find(".entity-edit-form__confirm").trigger("click");

        expect(form.text()).toContain("entity_wikidata_taken");
        expect(store.entities.ent_u.wikidataId).toBeUndefined();
    });

    test("cancel keeps the entity unchanged", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        const form = await openEditForm(wrapper, "UNESCO");
        await form.find(".entity-edit-form__name").setValue("Unesco");
        await form.find(".entity-edit-form__cancel").trigger("click");

        expect(store.entities.ent_u.name).toBe("UNESCO");
        expect(wrapper.find(".entity-edit-form").exists()).toBe(false);
    });
});

describe("EntityRegister delete", () => {
    test("asks for confirmation in place and then deletes the entity", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        await row(wrapper, "Anna Seghers")
            .find(".entity-register-row__delete")
            .trigger("click");
        expect(store.entities.ent_a).toBeDefined();
        expect(row(wrapper, "Anna Seghers").text()).toContain(
            "entity_delete_confirm",
        );

        await row(wrapper, "Anna Seghers")
            .find(".entity-register-row__delete-confirm")
            .trigger("click");

        expect(store.entities.ent_a).toBeUndefined();
        expect(store.mentions.men_1.entityId).toBeNull();
        expect(rowNames(wrapper)).toEqual(["UNESCO", "Zürich"]);
    });

    test("cancelling the confirmation keeps the entity", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        await row(wrapper, "UNESCO")
            .find(".entity-register-row__delete")
            .trigger("click");
        await row(wrapper, "UNESCO")
            .find(".entity-register-row__delete-cancel")
            .trigger("click");

        expect(store.entities.ent_u).toBeDefined();
        expect(row(wrapper, "UNESCO").text()).not.toContain(
            "entity_delete_confirm",
        );
    });
});
