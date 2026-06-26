import { describe, test, expect } from "vitest";
import { mount } from "@vue/test-utils";
import TimeCode from "./time_code.vue";

describe("TimeCode", () => {
    test("renders hours, minutes, seconds and milliseconds as separate spans", () => {
        const wrapper = mount(TimeCode, { props: { seconds: 10053.482 } });

        expect(wrapper.find(".timecode__hours").text()).toBe("2");
        expect(wrapper.find(".timecode__minutes").text()).toBe("47");
        expect(wrapper.find(".timecode__seconds").text()).toBe("33");
        expect(wrapper.find(".timecode__milliseconds").text()).toBe("482");
    });

    test("renders colons and a decimal point as separators", () => {
        const wrapper = mount(TimeCode, { props: { seconds: 10053.482 } });

        const colons = wrapper.findAll(".timecode__colon");
        expect(colons).toHaveLength(2);
        expect(colons[0].text()).toBe(":");
        expect(colons[1].text()).toBe(":");
        expect(wrapper.find(".timecode__point").text()).toBe(".");
    });

    test("renders the whole timecode as 2:47:33.482", () => {
        const wrapper = mount(TimeCode, { props: { seconds: 10053.482 } });

        expect(wrapper.text()).toBe("2:47:33.482");
    });

    test("pads minutes, seconds and milliseconds with zeros", () => {
        const wrapper = mount(TimeCode, { props: { seconds: 3605.04 } });

        expect(wrapper.find(".timecode__hours").text()).toBe("1");
        expect(wrapper.find(".timecode__minutes").text()).toBe("00");
        expect(wrapper.find(".timecode__seconds").text()).toBe("05");
        expect(wrapper.find(".timecode__milliseconds").text()).toBe("040");
    });
});
