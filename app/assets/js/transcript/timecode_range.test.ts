import { describe, test, expect } from "vitest";
import { mount } from "@vue/test-utils";
import TimecodeRange from "./timecode_range.vue";
import TimecodeValue from "./timecode_value.vue";

describe("TimecodeRange", () => {
    test("renders a value for both the start and end timecode", () => {
        const wrapper = mount(TimecodeRange, { props: { start: 65, end: 130 } });

        const values = wrapper.findAllComponents(TimecodeValue);
        expect(values).toHaveLength(2);
        expect(values[0].text()).toBe("0:01:05.000");
        expect(values[1].text()).toBe("0:02:10.000");
    });

    test("renders the start timecode in the start slot and the end in the end slot", () => {
        const wrapper = mount(TimecodeRange, { props: { start: 65, end: 130 } });

        expect(wrapper.find(".timecode-range__start").text()).toBe("0:01:05.000");
        expect(wrapper.find(".timecode-range__end").text()).toBe("0:02:10.000");
    });

    test("renders a separator between the two timecodes", () => {
        const wrapper = mount(TimecodeRange, { props: { start: 65, end: 130 } });

        expect(wrapper.find(".timecode-range__separator").text()).toBe("–");
    });
});
