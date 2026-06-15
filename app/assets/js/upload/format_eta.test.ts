import { describe, expect, test } from "vitest";

import formatEta from "./format_eta";

describe("formatEta", () => {
    test("returns null when not estimable", () => {
        expect(formatEta(null)).toBeNull();
        expect(formatEta(Infinity)).toBeNull();
    });

    test("shows seconds below 60 s", () => {
        expect(formatEta(0)).toBe("0s");
        expect(formatEta(17)).toBe("17s");
        expect(formatEta(59.4)).toBe("59s");
    });

    test("shows minutes and seconds between 60 s and 1 h", () => {
        expect(formatEta(60)).toBe("1m");
        expect(formatEta(125)).toBe("2m 5s");
        expect(formatEta(3599)).toBe("59m 59s");
    });

    test("shows hours and minutes at 1 h and above", () => {
        expect(formatEta(3600)).toBe("1h");
        expect(formatEta(5100)).toBe("1h 25m");
    });
});
