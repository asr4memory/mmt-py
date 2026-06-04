import { describe, test, expect } from "vitest";
import { mount } from "@vue/test-utils";
import SpeakerSelect from "./speaker_select.ts";

function mountComponent(modelValue, speakers = []) {
    return mount(SpeakerSelect, { props: { modelValue, speakers } });
}

describe("SpeakerSelect", () => {
    test("renders an option for each speaker", () => {
        const wrapper = mountComponent("Alice", ["Alice", "Bob"]);

        const options = wrapper.findAll("option");
        expect(options).toHaveLength(2);
        expect(options[0].text()).toBe("Alice");
        expect(options[1].text()).toBe("Bob");
    });

    test("selects the option matching modelValue", () => {
        const wrapper = mountComponent("Bob", ["Alice", "Bob"]);

        expect(wrapper.find("select").element.value).toBe("Bob");
    });

    test("emits update:modelValue with new speaker when selection changes", async () => {
        const wrapper = mountComponent("Alice", ["Alice", "Bob"]);
        await wrapper.find("select").setValue("Bob");

        expect(wrapper.emitted("update:modelValue")).toEqual([["Bob"]]);
    });
});
