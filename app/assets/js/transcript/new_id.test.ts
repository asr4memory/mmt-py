// @vitest-environment node

import { expect, test } from "vitest";

import { newId } from "./new_id";

test("newId spells the uuid without dashes, like the backend does", () => {
    expect(newId("wrd")).toMatch(/^wrd_[0-9a-f]{32}$/);
});

test("newId returns a different id on every call", () => {
    expect(newId("seg")).not.toBe(newId("seg"));
});
