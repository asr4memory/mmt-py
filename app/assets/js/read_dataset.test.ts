import { describe, expect, test } from "vitest";
import { readBool, readFiles, readInt, readIntList, readString } from "./read_dataset";

function makeElement(dataset: Record<string, string>): HTMLElement {
    const el = document.createElement("div");
    for (const [key, value] of Object.entries(dataset)) {
        el.dataset[key] = value;
    }
    return el;
}

describe("readString", () => {
    test("returns the value when the attribute is present", () => {
        const el = makeElement({ foo: "bar" });
        expect(readString(el, "foo")).toBe("bar");
    });

    test("throws when the attribute is missing", () => {
        const el = makeElement({});
        expect(() => readString(el, "foo")).toThrow("data-foo");
    });
});

describe("readInt", () => {
    test("parses a dataset value as an integer", () => {
        const el = makeElement({ count: "42" });
        expect(readInt(el, "count")).toBe(42);
    });

    test("throws when the attribute is missing", () => {
        const el = makeElement({});
        expect(() => readInt(el, "count")).toThrow("data-count");
    });
});

describe("readBool", () => {
    test("returns true for 'true'", () => {
        const el = makeElement({ active: "true" });
        expect(readBool(el, "active")).toBe(true);
    });

    test("returns false for 'false'", () => {
        const el = makeElement({ active: "false" });
        expect(readBool(el, "active")).toBe(false);
    });

    test("throws when the attribute is missing", () => {
        const el = makeElement({});
        expect(() => readBool(el, "active")).toThrow("data-active");
    });
});

describe("readIntList", () => {
    test("parses a comma-separated list of integers", () => {
        const el = makeElement({ chunks: "1,3,5" });
        expect(readIntList(el, "chunks")).toEqual([1, 3, 5]);
    });

    test("returns an empty array for an empty value", () => {
        const el = makeElement({ chunks: "" });
        expect(readIntList(el, "chunks")).toEqual([]);
    });

    test("handles a single value", () => {
        const el = makeElement({ chunks: "7" });
        expect(readIntList(el, "chunks")).toEqual([7]);
    });

    test("handles chunk index 0", () => {
        const el = makeElement({ chunks: "0,1,2" });
        expect(readIntList(el, "chunks")).toEqual([0, 1, 2]);
    });

    test("throws when the attribute is missing", () => {
        const el = makeElement({});
        expect(() => readIntList(el, "chunks")).toThrow("data-chunks");
    });
});

describe("readFiles", () => {
    function makeFormWithFiles(files: File[]): HTMLElement {
        const form = document.createElement("form");
        const input = document.createElement("input");
        input.type = "file";
        const fileList = {
            length: files.length,
            item: (i: number) => files[i] ?? null,
            [Symbol.iterator]: () => files[Symbol.iterator](),
        } as unknown as FileList;
        Object.defineProperty(input, "files", { value: fileList });
        form.append(input);
        return form;
    }

    test("returns the selected files from the file input", () => {
        const a = new File(["a"], "a.mp4");
        const b = new File(["b"], "b.mp4");
        expect(readFiles(makeFormWithFiles([a, b]))).toEqual([a, b]);
    });

    test("returns an empty array when no file is selected", () => {
        expect(readFiles(makeFormWithFiles([]))).toEqual([]);
    });

    test("returns an empty array when there is no file input", () => {
        expect(readFiles(document.createElement("form"))).toEqual([]);
    });
});
