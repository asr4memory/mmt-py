import { describe, test, expect } from "vitest";
import { mount } from "@vue/test-utils";
import SpeakerSelect from "./speaker_select.vue";
import type { Speaker } from "./types";

const SPEAKERS: Speaker[] = [
    { id: "spk_a", name: "Alice", color: "#5b9bd5" },
    { id: "spk_b", name: "Bob", color: "#70ad47" },
];

function mountComponent(
    modelValue: string | undefined,
    speakers: Speaker[] = [],
    segmentId: string = "1",
) {
    return mount(SpeakerSelect, { props: { modelValue, speakers, segmentId } });
}

describe("SpeakerSelect", () => {
    test("renders an option for each speaker", () => {
        const wrapper = mountComponent("spk_a", SPEAKERS);

        const options = wrapper.findAll("option");
        expect(options).toHaveLength(2);
        expect(options[0].text()).toBe("Alice");
        expect(options[1].text()).toBe("Bob");
    });

    test("selects the option matching modelValue", () => {
        const wrapper = mountComponent("spk_b", SPEAKERS);

        expect(wrapper.find("select").element.value).toBe("spk_b");
    });

    test("emits update:modelValue with the speaker id when selection changes", async () => {
        const wrapper = mountComponent("spk_a", SPEAKERS);
        await wrapper.find("select").setValue("spk_b");

        expect(wrapper.emitted("update:modelValue")).toEqual([["spk_b"]]);
    });
});
