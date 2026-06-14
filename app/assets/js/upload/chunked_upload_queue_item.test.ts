import { describe, expect, test } from "vitest";
import { mount } from "@vue/test-utils";
import { createI18n } from "vue-i18n";

import ChunkedUploadQueueItem from "./chunked_upload_queue_item";
import en from "../locales/en.js";
import type { Upload } from "./types";

const i18n = createI18n({ legacy: false, locale: "en", messages: { en } });

function makeUpload(overrides: Partial<Upload> = {}): Upload {
    return {
        id: 1,
        file: new File([new ArrayBuffer(1000)], "clip.mp4"),
        status: "uploading",
        transferred: 0,
        speed: 0,
        eta: null,
        ...overrides,
    };
}

function mountItem(overrides: Partial<Upload> = {}) {
    return mount(ChunkedUploadQueueItem, {
        props: { upload: makeUpload(overrides) },
        global: { plugins: [i18n] },
    });
}

describe("ChunkedUploadQueueItem", () => {
    test("renders the file name", () => {
        const wrapper = mountItem();
        expect(wrapper.find(".chunked-queue-item__name").text()).toBe(
            "clip.mp4",
        );
    });

    test("reflects status in the modifier class and details", () => {
        const wrapper = mountItem({ status: "uploaded" });
        expect(wrapper.classes()).toContain("chunked-queue-item--uploaded");
        expect(wrapper.find(".chunked-queue-item__details").text()).toContain(
            "uploaded",
        );
    });

    describe("stats", () => {
        test("shows the floored percentage while uploading", () => {
            const wrapper = mountItem({ transferred: 255 });
            expect(wrapper.find(".chunked-queue-item__percent").text()).toBe(
                "25 %",
            );
        });

        test("formats speed once it is known", () => {
            const wrapper = mountItem({ speed: 1572864 });
            expect(wrapper.find(".chunked-queue-item__speed").text()).toBe(
                "1.5 MB/s",
            );
        });

        test("hides speed before it is estimable", () => {
            const wrapper = mountItem({ speed: 0 });
            expect(wrapper.find(".chunked-queue-item__speed").exists()).toBe(
                false,
            );
        });

        test("renders a coarse ETA label", () => {
            const wrapper = mountItem({ eta: 120 });
            expect(wrapper.find(".chunked-queue-item__eta").text()).toBe(
                "about 2 min left",
            );
        });

        test("hides the ETA when not estimable", () => {
            const wrapper = mountItem({ eta: null });
            expect(wrapper.find(".chunked-queue-item__eta").exists()).toBe(
                false,
            );
        });

        test("hides the whole stats row unless uploading", () => {
            const wrapper = mountItem({ status: "pending", speed: 1572864 });
            expect(wrapper.find(".chunked-queue-item__stats").exists()).toBe(
                false,
            );
        });
    });

    describe("cancel button", () => {
        test("is shown for pending and uploading uploads", () => {
            for (const status of ["pending", "uploading"] as const) {
                const wrapper = mountItem({ status });
                expect(
                    wrapper.find(".chunked-queue-item__button").exists(),
                ).toBe(true);
            }
        });

        test("is hidden for finished uploads", () => {
            for (const status of ["uploaded", "cancelled", "incomplete"] as const) {
                const wrapper = mountItem({ status });
                expect(
                    wrapper.find(".chunked-queue-item__button").exists(),
                ).toBe(false);
            }
        });

        test("emits onCancel with the upload when clicked", async () => {
            const wrapper = mountItem();
            await wrapper.find(".chunked-queue-item__button").trigger("click");
            expect(wrapper.emitted("onCancel")?.[0][0]).toMatchObject({
                file: { name: "clip.mp4" },
            });
        });
    });
});
