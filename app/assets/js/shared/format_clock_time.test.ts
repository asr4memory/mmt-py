import { describe, test, expect } from "vitest";
import formatClockTime from "./format_clock_time";

describe("formatClockTime", () => {
    test("formats seconds below a minute as 0:ss", () => {
        expect(formatClockTime(0)).toBe("0:00");
        expect(formatClockTime(7.9)).toBe("0:07");
    });

    test("formats minutes and seconds without padding the minutes", () => {
        expect(formatClockTime(83)).toBe("1:23");
        expect(formatClockTime(599)).toBe("9:59");
    });

    test("adds an hours part only once the hour is reached", () => {
        expect(formatClockTime(3599)).toBe("59:59");
        expect(formatClockTime(3600)).toBe("1:00:00");
        expect(formatClockTime(10053)).toBe("2:47:33");
    });

    test("treats a negative or non-finite value as zero", () => {
        expect(formatClockTime(-5)).toBe("0:00");
        expect(formatClockTime(NaN)).toBe("0:00");
    });
});
