import { describe, test, expect } from "vitest";
import { mount } from "@vue/test-utils";
import SpeakerSelect from "./speaker_select.vue";

const SPEAKERS = [
    { name: "Alice", color: "#5b9bd5" },
    { name: "Bob", color: "#70ad47" },
];

function mountComponent(
    modelValue: string | undefined,
    speakers: { name: string; color: string }[] = [],
    segmentId: string = "1",
) {
    return mount(SpeakerSelect, { props: { modelValue, speakers, segmentId } });
}

describe("SpeakerSelect", () => {
    test("renders an option for each speaker", () => {
        const wrapper = mountComponent("Alice", SPEAKERS);

        const options = wrapper.findAll("option");
        expect(options).toHaveLength(2);
        expect(options[0].text()).toBe("Alice");
        expect(options[1].text()).toBe("Bob");
    });

    test("selects the option matching modelValue", () => {
        const wrapper = mountComponent("Bob", SPEAKERS);

        expect(wrapper.find("select").element.value).toBe("Bob");
    });

    test("emits update:modelValue with new speaker when selection changes", async () => {
        const wrapper = mountComponent("Alice", SPEAKERS);
        await wrapper.find("select").setValue("Bob");

        expect(wrapper.emitted("update:modelValue")).toEqual([["Bob"]]);
    });
});
