import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import EntityCombobox from "./entity_combobox.vue";
import type { Entity } from "./types";

const ENTITIES: Record<string, Entity> = {
    ent_merkel: { name: "Angela Merkel", type: "PER" },
    ent_kohl: { name: "Helmut Kohl", type: "PER" },
    ent_berlin: { name: "Berlin", type: "LOC" },
};

// $t returns the key followed by its argument, so that a test can read the
// name passed to the create button.
function translate(key: string, params?: unknown) {
    return params === undefined ? key : `${key} ${JSON.stringify(params)}`;
}

function mountCombobox(
    proposedName: string,
    options: {
        entities?: Record<string, Entity>;
        entityId?: string | null;
    } = {},
) {
    return mount(EntityCombobox, {
        props: {
            proposedName,
            entities: options.entities ?? ENTITIES,
            entityId: options.entityId ?? null,
        },
        global: { mocks: { $t: translate } },
    });
}

function selectedValue(wrapper: ReturnType<typeof mountCombobox>) {
    return (wrapper.find("select").element as HTMLSelectElement).value;
}

// The entity ids in the order of the select's options, without the empty
// option.
function optionIds(wrapper: ReturnType<typeof mountCombobox>) {
    return wrapper
        .findAll("option")
        .map((option) => option.attributes("value"))
        .filter((value) => value !== "");
}

describe("EntityCombobox", () => {
    test("the select lists every entity sorted by name", () => {
        const wrapper = mountCombobox("Merkel");

        expect(optionIds(wrapper)).toEqual([
            "ent_merkel",
            "ent_berlin",
            "ent_kohl",
        ]);
    });

    test("selects nothing, also when an entity has the proposed name", () => {
        const wrapper = mountCombobox("Angela Merkel");

        expect(selectedValue(wrapper)).toBe("");
    });

    test("selects a given entity", () => {
        const wrapper = mountCombobox("Merkel", { entityId: "ent_kohl" });

        expect(selectedValue(wrapper)).toBe("ent_kohl");
    });

    test("typing in the name input leaves the selection unchanged", async () => {
        const wrapper = mountCombobox("Merkel", { entityId: "ent_kohl" });

        await wrapper.find("input").setValue("Berlin");

        expect(selectedValue(wrapper)).toBe("ent_kohl");
        expect(optionIds(wrapper)[0]).toBe("ent_merkel");
    });

    test("the link button emits the selected entity", async () => {
        const wrapper = mountCombobox("Merkel");

        await wrapper.find("select").setValue("ent_berlin");
        await wrapper.find(".entity-combobox__link").trigger("click");

        expect(wrapper.emitted("select")).toEqual([["ent_berlin"]]);
    });

    test("the link button is disabled while nothing is selected", () => {
        const wrapper = mountCombobox("Merkel");

        expect(
            wrapper.find(".entity-combobox__link").attributes("disabled"),
        ).toBeDefined();
    });

    test("no select is shown for an empty register", () => {
        const wrapper = mountCombobox("Merkel", { entities: {} });

        expect(wrapper.find("select").exists()).toBe(false);
        expect(wrapper.find(".entity-combobox__link").exists()).toBe(false);
        expect(wrapper.find(".entity-combobox__create").exists()).toBe(true);
    });

    test("the create button emits the trimmed name", async () => {
        const wrapper = mountCombobox(" Gerhard Schröder ");

        const button = wrapper.find(".entity-combobox__create");
        expect(button.text()).toBe('entity_create {"name":"Gerhard Schröder"}');
        await button.trigger("click");

        expect(wrapper.emitted("create")).toEqual([["Gerhard Schröder"]]);
    });

    test("Enter in the name input creates the entity", async () => {
        const wrapper = mountCombobox("Gerhard Schröder");
        await wrapper.find("select").setValue("ent_berlin");

        await wrapper.find("input").trigger("keydown", { key: "Enter" });

        expect(wrapper.emitted("create")).toEqual([["Gerhard Schröder"]]);
        expect(wrapper.emitted("select")).toBeUndefined();
    });

    test("offers no create for the name of an entity of any type", async () => {
        const wrapper = mountCombobox("Berlin");
        expect(wrapper.find(".entity-combobox__create").exists()).toBe(false);

        await wrapper.find("input").setValue(" Angela Merkel ");
        expect(wrapper.find(".entity-combobox__create").exists()).toBe(false);
        await wrapper.find("input").trigger("keydown", { key: "Enter" });
        expect(wrapper.emitted("create")).toBeUndefined();
    });

    test("names are compared exactly", () => {
        const wrapper = mountCombobox("berlin");

        expect(wrapper.find(".entity-combobox__create").exists()).toBe(true);
    });

    test("offers no create for an empty name", async () => {
        const wrapper = mountCombobox("   ");

        expect(wrapper.find(".entity-combobox__create").exists()).toBe(false);
        await wrapper.find("input").trigger("keydown", { key: "Enter" });
        expect(wrapper.emitted("create")).toBeUndefined();
    });

    test("Escape cancels", async () => {
        const wrapper = mountCombobox("Merkel");

        await wrapper.find("input").trigger("keydown", { key: "Escape" });

        expect(wrapper.emitted("cancel")).toHaveLength(1);
        expect(wrapper.emitted("select")).toBeUndefined();
    });
});
