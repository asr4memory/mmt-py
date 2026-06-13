import { describe, expect, test } from "vitest";

import {
    estimateEta,
    estimateSpeed,
    trimToWindow,
    type Sample,
} from "./transfer_stats";

describe("estimateSpeed", () => {
    test("returns 0 with fewer than two samples", () => {
        expect(estimateSpeed([])).toBe(0);
        expect(estimateSpeed([{ time: 0, bytes: 0 }])).toBe(0);
    });

    test("returns 0 when no time has elapsed", () => {
        const samples: Sample[] = [
            { time: 1000, bytes: 0 },
            { time: 1000, bytes: 500 },
        ];
        expect(estimateSpeed(samples)).toBe(0);
    });

    test("measures bytes per second across the window", () => {
        const samples: Sample[] = [
            { time: 0, bytes: 0 },
            { time: 1000, bytes: 1000 },
            { time: 2000, bytes: 3000 },
        ];
        // 3000 bytes over 2 s
        expect(estimateSpeed(samples)).toBe(1500);
    });
});

describe("estimateEta", () => {
    test("returns null when speed is zero or negative", () => {
        expect(estimateEta(1000, 0)).toBeNull();
        expect(estimateEta(1000, -5)).toBeNull();
    });

    test("returns remaining seconds", () => {
        expect(estimateEta(3000, 1500)).toBe(2);
    });
});

describe("trimToWindow", () => {
    test("returns an empty array unchanged", () => {
        expect(trimToWindow([])).toEqual([]);
    });

    test("drops samples older than 5 s before the latest", () => {
        const samples: Sample[] = [
            { time: 0, bytes: 0 },
            { time: 4000, bytes: 100 },
            { time: 7000, bytes: 200 },
        ];
        // latest is 7000, cutoff is 2000
        expect(trimToWindow(samples)).toEqual([
            { time: 4000, bytes: 100 },
            { time: 7000, bytes: 200 },
        ]);
    });
});
