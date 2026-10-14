// @vitest-environment node

import { expect, test } from "vitest";

import cases from "../../../mmt/transcripts/tests/data/normalization_cases.json";
import {
    matchingEntity,
    normalizedSurface,
    rankEntities,
} from "./entity_matching";
import type { Entity } from "./types";

test.each(cases)("normalizedSurface($input)", ({ input, expected }) => {
    expect(normalizedSurface(input)).toBe(expected);
});

const entities: Record<string, Entity> = {
    ent_1: {
        name: "Angela Merkel",
        type: "PER",
        aliases: ["Merkel"],
        wikidataId: "Q567",
    },
    ent_2: { name: "Berlin", type: "LOC", aliases: [], wikidataId: null },
};

test("matchingEntity matches the name", () => {
    expect(matchingEntity("Angela Merkel", "PER", entities)).toBe("ent_1");
});

test("matchingEntity matches an alias", () => {
    expect(matchingEntity("Merkel", "PER", entities)).toBe("ent_1");
});

test("matchingEntity ignores case and edge punctuation", () => {
    expect(matchingEntity("„MERKEL“,", "PER", entities)).toBe("ent_1");
});

test("matchingEntity requires the same type", () => {
    expect(matchingEntity("Berlin", "ORG", entities)).toBeNull();
});

test("matchingEntity returns null without a match", () => {
    expect(matchingEntity("Helmut Kohl", "PER", entities)).toBeNull();
});

const register: Record<string, Entity> = {
    ent_kohl: { name: "Helmut Kohl", type: "PER", aliases: [] },
    ent_berlin: { name: "Berlin", type: "LOC", aliases: [] },
    ent_merkel: { name: "Angela Merkel", type: "PER", aliases: ["Merkel"] },
    ent_merz: { name: "Merz", type: "PER", aliases: [] },
    ent_bmk: {
        name: "Bundeskanzleramt",
        type: "ORG",
        aliases: ["Kanzleramt Merkel"],
    },
    ent_aaa: { name: "Aachen", type: "LOC", aliases: [] },
};

test("rankEntities orders the match, prefix, containment and other groups", () => {
    const ranked = rankEntities("Merkel", "PER", register);
    expect(ranked.map((entry) => entry.id)).toEqual([
        // The alias "Merkel" of a PER entity matches exactly.
        "ent_merkel",
        // An alias contains the query.
        "ent_bmk",
        // Every other entity, by name.
        "ent_aaa",
        "ent_berlin",
        "ent_kohl",
        "ent_merz",
    ]);
});

test("rankEntities puts prefix matches before containment matches", () => {
    const ranked = rankEntities("mer", "PER", register);
    expect(ranked.map((entry) => entry.id)).toEqual([
        "ent_merkel",
        "ent_merz",
        "ent_bmk",
        "ent_aaa",
        "ent_berlin",
        "ent_kohl",
    ]);
});

test("rankEntities marks only the matchingEntity result as exact", () => {
    const ranked = rankEntities("Merkel", "PER", register);
    expect(
        ranked.filter((entry) => entry.exactMatch).map((entry) => entry.id),
    ).toEqual(["ent_merkel"]);
});

test("rankEntities marks no exact match when the type differs", () => {
    const ranked = rankEntities("Merkel", "ORG", register);
    expect(ranked.some((entry) => entry.exactMatch)).toBe(false);
    expect(ranked[0].id).toBe("ent_merkel");
});
