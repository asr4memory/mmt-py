// @vitest-environment node

import { expect, test } from "vitest";

import { trimmedSurface } from "./entity_matching";

test("trimmedSurface strips the edges and keeps case and interior punctuation", () => {
    expect(trimmedSurface("St. Pauli,")).toBe("St. Pauli");
    expect(trimmedSurface("„Merkel“")).toBe("Merkel");
    expect(trimmedSurface("  Angela   Merkel?! ")).toBe("Angela Merkel");
    expect(trimmedSurface("...")).toBe("");
});
