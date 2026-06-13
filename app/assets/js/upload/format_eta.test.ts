import { describe, expect, test } from "vitest";

import formatEta from "./format_eta";

describe("formatEta", () => {
    test("returns null when not estimable", () => {
        expect(formatEta(null)).toBeNull();
        expect(formatEta(Infinity)).toBeNull();
    });

    test("reports a few seconds below 45 s", () => {
        expect(formatEta(10)).toEqual({ key: "queue.eta_seconds" });
        expect(formatEta(44)).toEqual({ key: "queue.eta_seconds" });
    });

    test("reports about a minute between 45 and 90 s", () => {
        expect(formatEta(45)).toEqual({ key: "queue.eta_one_minute" });
        expect(formatEta(89)).toEqual({ key: "queue.eta_one_minute" });
    });

    test("rounds to the nearest minute", () => {
        expect(formatEta(90)).toEqual({
            key: "queue.eta_minutes",
            params: { minutes: 2 },
        });
        expect(formatEta(150)).toEqual({
            key: "queue.eta_minutes",
            params: { minutes: 3 },
        });
    });

    test("switches to hours for long uploads", () => {
        expect(formatEta(3600)).toEqual({
            key: "queue.eta_hours",
            params: { hours: 1 },
        });
    });
});
