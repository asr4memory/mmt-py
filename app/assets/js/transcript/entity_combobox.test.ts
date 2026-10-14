import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import EntityCombobox from "./entity_combobox.vue";
import type { Entity } from "./types";

const ENTITIES: Record<string, Entity> = {
    ent_merkel: { name: "Angela Merkel", type: "PER", aliases: ["Merkel"] },
    ent_berlin: { name: "Berlin", type: "LOC", aliases: [] },
    ent_kohl: { name: "Helmut Kohl", type: "PER", aliases: [] },
};

// $t returns the key followed by its argument, so that a test can read the
// name passed to the create button.
function translate(key: string, params?: unknown) {
    return params === undefined ? key : `${key} ${JSON.stringify(params)}`;
}

function mountCombobox(query: string, type = "PER") {
    return mount(EntityCombobox, {
        props: { query, type, entities: ENTITIES },
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
    test("preselects the entity that rule A matches", () => {
        const wrapper = mountCombobox("Merkel");

        expect(selectedValue(wrapper)).toBe("ent_merkel");
    });

    test("preselects nothing without a match", () => {
        const wrapper = mountCombobox("Helmut");

        expect(selectedValue(wrapper)).toBe("");
    });

    test("selects a given entity until the query changes", async () => {
        const wrapper = mount(EntityCombobox, {
            props: {
                query: "Merkel",
                type: "PER",
                entities: ENTITIES,
                entityId: "ent_kohl",
            },
            global: { mocks: { $t: translate } },
        });
        expect(selectedValue(wrapper)).toBe("ent_kohl");

        await wrapper.find("input").setValue("Angela Merkel");
        expect(selectedValue(wrapper)).toBe("ent_merkel");
    });

    test("typing reorders the options and moves the preselection", async () => {
        const wrapper = mountCombobox("Merkel");

        await wrapper.find("input").setValue("Helmut Kohl");

        expect(optionIds(wrapper)[0]).toBe("ent_kohl");
        expect(selectedValue(wrapper)).toBe("ent_kohl");
    });

    test("the create button emits the trimmed query", async () => {
        const wrapper = mountCombobox(" Gerhard Schröder ");

        const button = wrapper.find(".entity-combobox__create");
        expect(button.text()).toBe('entity_create {"name":"Gerhard Schröder"}');
        await button.trigger("click");

        expect(wrapper.emitted("create")).toEqual([["Gerhard Schröder"]]);
    });

    test("offers no create button for a name or alias of an entity of any type", async () => {
        const wrapper = mountCombobox("berlin");
        expect(wrapper.find(".entity-combobox__create").exists()).toBe(false);

        await wrapper.find("input").setValue("MERKEL,");
        expect(wrapper.find(".entity-combobox__create").exists()).toBe(false);
    });

    test("offers no create button for an empty query", () => {
        const wrapper = mountCombobox(" ... ");

        expect(wrapper.find(".entity-combobox__create").exists()).toBe(false);
    });

    test("the link button emits the selected entity", async () => {
        const wrapper = mountCombobox("Helmut");

        await wrapper.find("select").setValue("ent_berlin");
        await wrapper.find(".entity-combobox__link").trigger("click");

        expect(wrapper.emitted("select")).toEqual([["ent_berlin"]]);
    });

    test("the link button is disabled while nothing is selected", () => {
        const wrapper = mountCombobox("Helmut");

        expect(
            wrapper.find(".entity-combobox__link").attributes("disabled"),
        ).toBeDefined();
    });

    test("Enter in the input links the preselected entity", async () => {
        const wrapper = mountCombobox("Merkel");

        await wrapper.find("input").trigger("keydown", { key: "Enter" });

        expect(wrapper.emitted("select")).toEqual([["ent_merkel"]]);
    });

    test("Enter in the input does nothing while nothing is selected", async () => {
        const wrapper = mountCombobox("Gerhard Schröder");

        await wrapper.find("input").trigger("keydown", { key: "Enter" });

        expect(wrapper.emitted("select")).toBeUndefined();
        expect(wrapper.emitted("create")).toBeUndefined();
    });

    test("Escape cancels", async () => {
        const wrapper = mountCombobox("Merkel");

        await wrapper.find("input").trigger("keydown", { key: "Escape" });

        expect(wrapper.emitted("cancel")).toHaveLength(1);
        expect(wrapper.emitted("select")).toBeUndefined();
    });
});
