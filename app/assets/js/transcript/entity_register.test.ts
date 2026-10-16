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

function isDisabled(element: { attributes: (name: string) => unknown }) {
    return element.attributes("disabled") !== undefined;
}

describe("EntityRegister add form", () => {
    async function openAddForm() {
        const store = seedRegister();
        const wrapper = mountRegister();
        await wrapper.find(".entity-register__add-toggle").trigger("click");
        return { store, wrapper };
    }

    test("creates an entity without mentions from the name and the type", async () => {
        const { store, wrapper } = await openAddForm();

        await wrapper
            .find(".entity-register__add-name")
            .setValue(" Bertolt Brecht ");
        await wrapper.find(".entity-register__add-type").setValue("PER");
        await wrapper.find(".entity-register__add-confirm").trigger("click");

        const created = Object.values(store.entities).find(
            (entity) => entity.name === "Bertolt Brecht",
        );
        expect(created).toMatchObject({ type: "PER", wikidataId: null });
        expect(rowCount(wrapper, "Bertolt Brecht").text).toBe(
            'entity_mention_count_short {"count":0}',
        );
        expect(wrapper.find(".entity-register__add-form").exists()).toBe(false);
    });

    test("defaults the type to PER", async () => {
        const { wrapper } = await openAddForm();

        const select = wrapper.find(".entity-register__add-type")
            .element as HTMLSelectElement;
        expect(select.value).toBe("PER");
    });

    test("cannot confirm an empty name", async () => {
        const { wrapper } = await openAddForm();

        await wrapper.find(".entity-register__add-name").setValue("   ");

        expect(isDisabled(wrapper.find(".entity-register__add-confirm"))).toBe(
            true,
        );
    });

    test("cannot confirm a name another entity has, whatever its type", async () => {
        const { store, wrapper } = await openAddForm();

        await wrapper.find(".entity-register__add-name").setValue("UNESCO");
        await wrapper.find(".entity-register__add-type").setValue("LOC");

        expect(isDisabled(wrapper.find(".entity-register__add-confirm"))).toBe(
            true,
        );
        expect(wrapper.find(".entity-register__add-form").text()).toContain(
            "entity_name_taken",
        );
        await wrapper.find(".entity-register__add-name").trigger("keyup.enter");
        expect(Object.keys(store.entities)).toHaveLength(3);
    });

    test("cancelling creates nothing", async () => {
        const { store, wrapper } = await openAddForm();

        await wrapper.find(".entity-register__add-name").setValue("Brecht");
        await wrapper.find(".entity-register__add-cancel").trigger("click");

        expect(Object.keys(store.entities)).toHaveLength(3);
        expect(wrapper.find(".entity-register__add-form").exists()).toBe(false);
    });
});

describe("EntityRegister edit form", () => {
    async function openEditForm(name: string) {
        const store = seedRegister();
        const wrapper = mountRegister();
        await row(wrapper, name)
            .find(".entity-register-row__edit")
            .trigger("click");
        return {
            store,
            wrapper,
            form: () => wrapper.find(".entity-register__edit-form"),
        };
    }

    test("is prefilled and writes the name and the Wikidata ID", async () => {
        const { store, wrapper, form } = await openEditForm("Anna Seghers");
        const nameInput = form().find(".entity-register__edit-name");
        const wikidataInput = form().find(".entity-register__edit-wikidata");
        expect((nameInput.element as HTMLInputElement).value).toBe(
            "Anna Seghers",
        );
        expect((wikidataInput.element as HTMLInputElement).value).toBe(
            "Q61597",
        );

        await nameInput.setValue(" Netty Reiling ");
        await wikidataInput.setValue("Q1");
        await form().find(".entity-register__edit-confirm").trigger("click");

        expect(store.entities.ent_a).toEqual({
            name: "Netty Reiling",
            type: "PER",
            wikidataId: "Q1",
        });
        expect(form().exists()).toBe(false);
        expect(rowNames(wrapper)).toContain("Netty Reiling");
    });

    test("shows the type without a way to change it", async () => {
        const { form } = await openEditForm("Anna Seghers");

        expect(form().text()).toContain("entity_per");
        expect(form().find("select").exists()).toBe(false);
    });

    test("an empty Wikidata field removes the identifier", async () => {
        const { store, form } = await openEditForm("Anna Seghers");

        await form().find(".entity-register__edit-wikidata").setValue("  ");
        await form().find(".entity-register__edit-confirm").trigger("click");

        expect(store.entities.ent_a.wikidataId).toBeNull();
    });

    test("keeping the entity's own name is allowed", async () => {
        const { form } = await openEditForm("UNESCO");

        expect(isDisabled(form().find(".entity-register__edit-confirm"))).toBe(
            false,
        );
    });

    test("cannot confirm an empty name", async () => {
        const { form } = await openEditForm("UNESCO");

        await form().find(".entity-register__edit-name").setValue("");

        expect(isDisabled(form().find(".entity-register__edit-confirm"))).toBe(
            true,
        );
    });

    test("cannot confirm a name another entity has", async () => {
        const { store, form } = await openEditForm("UNESCO");

        await form().find(".entity-register__edit-name").setValue("Zürich");

        expect(isDisabled(form().find(".entity-register__edit-confirm"))).toBe(
            true,
        );
        expect(form().text()).toContain("entity_name_taken");
        await form().find(".entity-register__edit-name").trigger("keyup.enter");
        expect(store.entities.ent_u.name).toBe("UNESCO");
    });

    test("marks a malformed Wikidata ID as invalid", async () => {
        const { form } = await openEditForm("UNESCO");

        for (const value of ["Q0", "567", "Q567x"]) {
            await form()
                .find(".entity-register__edit-wikidata")
                .setValue(value);

            expect(
                form()
                    .find(".entity-register__edit-wikidata")
                    .attributes("aria-invalid"),
            ).toBe("true");
            expect(
                isDisabled(form().find(".entity-register__edit-confirm")),
            ).toBe(true);
        }
    });

    test("cannot confirm a Wikidata ID another entity has", async () => {
        const { form } = await openEditForm("UNESCO");

        await form().find(".entity-register__edit-wikidata").setValue("Q61597");

        expect(isDisabled(form().find(".entity-register__edit-confirm"))).toBe(
            true,
        );
        expect(form().text()).toContain("entity_wikidata_taken");
    });

    test("cancelling keeps the entity unchanged", async () => {
        const { store, form } = await openEditForm("UNESCO");

        await form().find(".entity-register__edit-name").setValue("Unesco");
        await form().find(".entity-register__edit-cancel").trigger("click");

        expect(store.entities.ent_u.name).toBe("UNESCO");
        expect(store.entitiesAreDirty).toBe(false);
        expect(form().exists()).toBe(false);
    });
});

describe("EntityRegister delete", () => {
    test("asks for confirmation and then deletes the entity, keeping its mentions", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        await row(wrapper, "Anna Seghers")
            .find(".entity-register-row__delete")
            .trigger("click");
        expect(Object.keys(store.entities)).toHaveLength(3);
        expect(wrapper.text()).toContain("entity_delete_confirm");

        await wrapper.find(".entity-register__delete-confirm").trigger("click");

        expect(store.entities.ent_a).toBeUndefined();
        expect(store.mentions.men_1).toEqual({
            type: "PER",
            score: 1,
            entityId: null,
        });
        expect(rowNames(wrapper)).toEqual(["UNESCO", "Zürich"]);
    });

    test("cancelling the confirmation keeps the entity", async () => {
        const store = seedRegister();
        const wrapper = mountRegister();

        await row(wrapper, "UNESCO")
            .find(".entity-register-row__delete")
            .trigger("click");
        await wrapper.find(".entity-register__delete-cancel").trigger("click");

        expect(store.entities.ent_u).toBeDefined();
        expect(rowNames(wrapper)).toEqual(["Anna Seghers", "UNESCO", "Zürich"]);
    });
});

describe("EntityRegister mentions of an entity", () => {
    function seedWithWords() {
        const store = seedRegister();
        store.segments = [
            {
                id: "seg_1",
                words: [
                    { id: "w1", start: 1, word: "Anna", mentionId: "men_1" },
                    { id: "w2", start: 2, word: "Seghers", mentionId: "men_1" },
                    { id: "w3", start: 3, word: "Zürich", mentionId: "men_3" },
                ],
            },
            {
                id: "seg_2",
                words: [
                    {
                        id: "w4",
                        start: 75,
                        word: "Seghers",
                        mentionId: "men_2",
                    },
                    { id: "w5", start: 76, word: "sagt", mentionId: "men_4" },
                ],
            },
        ] as any;
        return store;
    }

    test("offers no expand action for an entity without mentions", () => {
        seedWithWords();
        const wrapper = mountRegister();

        expect(
            row(wrapper, "UNESCO")
                .find(".entity-register-row__expand")
                .exists(),
        ).toBe(false);
        expect(
            row(wrapper, "Anna Seghers")
                .find(".entity-register-row__expand")
                .exists(),
        ).toBe(true);
    });

    test("expanding lists the mentions in document order with start time and surface text", async () => {
        seedWithWords();
        const wrapper = mountRegister();

        await row(wrapper, "Anna Seghers")
            .find(".entity-register-row__expand")
            .trigger("click");

        const entries = row(wrapper, "Anna Seghers").findAll(
            ".entity-register-row__mention",
        );
        expect(entries.map((entry) => entry.text())).toEqual([
            "0:01 Anna Seghers",
            "1:15 Seghers",
        ]);
    });

    test("activating a mention emits jump with its segment index", async () => {
        seedWithWords();
        const wrapper = mountRegister();
        await row(wrapper, "Anna Seghers")
            .find(".entity-register-row__expand")
            .trigger("click");

        await row(wrapper, "Anna Seghers")
            .findAll(".entity-register-row__mention")[1]
            .trigger("click");

        expect(wrapper.emitted("jump")).toEqual([[1]]);
    });
});
