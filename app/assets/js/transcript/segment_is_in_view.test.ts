import { describe, expect, test } from "vitest";

import segmentIsInView from "./segment_is_in_view";

const VIEWPORT = 800;
const HEADER = 200;

function rect(top: number, bottom: number): DOMRect {
    return { top, bottom } as DOMRect;
}

describe("segmentIsInView", () => {
    test("counts a segment between the header and the lower edge as visible", () => {
        expect(segmentIsInView(rect(300, 400), HEADER, VIEWPORT)).toBe(true);
    });

    test("counts a segment that is partly visible as visible", () => {
        expect(segmentIsInView(rect(150, 250), HEADER, VIEWPORT)).toBe(true);
        expect(segmentIsInView(rect(750, 900), HEADER, VIEWPORT)).toBe(true);
    });

    test("counts a segment hidden behind the header as not visible", () => {
        expect(segmentIsInView(rect(50, 199), HEADER, VIEWPORT)).toBe(false);
    });

    test("counts a segment below the viewport as not visible", () => {
        expect(segmentIsInView(rect(801, 900), HEADER, VIEWPORT)).toBe(false);
    });
});
