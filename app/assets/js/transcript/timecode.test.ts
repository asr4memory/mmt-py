import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import Timecode from "./timecode.vue";

describe("Timecode", () => {
    test("renders hours, minutes, seconds and milliseconds as separate spans", () => {
        const wrapper = mount(Timecode, {
            props: { start: 10053.482, end: 0 },
        });
        const start = wrapper.find(".timecode__value--start");

        expect(start.find(".timecode__hours").text()).toBe("2");
        expect(start.find(".timecode__minutes").text()).toBe("47");
        expect(start.find(".timecode__seconds").text()).toBe("33");
        expect(start.find(".timecode__milliseconds").text()).toBe("482");
    });

    test("pads minutes, seconds and milliseconds with zeros", () => {
        const wrapper = mount(Timecode, { props: { start: 3605.04, end: 0 } });
        const start = wrapper.find(".timecode__value--start");

        expect(start.find(".timecode__hours").text()).toBe("1");
        expect(start.find(".timecode__minutes").text()).toBe("00");
        expect(start.find(".timecode__seconds").text()).toBe("05");
        expect(start.find(".timecode__milliseconds").text()).toBe("040");
    });

    test("renders the start in the start value and the end in the end value", () => {
        const wrapper = mount(Timecode, { props: { start: 65, end: 130 } });

        expect(wrapper.find(".timecode__value--start").text()).toBe(
            "0:01:05.000",
        );
        expect(wrapper.find(".timecode__value--end").text()).toBe(
            "0:02:10.000",
        );
    });

    test("renders a separator between the two values", () => {
        const wrapper = mount(Timecode, { props: { start: 65, end: 130 } });

        const separators = wrapper.findAll(".timecode__separator");
        expect(separators).toHaveLength(1);
        expect(separators[0].text()).toBe("–");
    });
});
