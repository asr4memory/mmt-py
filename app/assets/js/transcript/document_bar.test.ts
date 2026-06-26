import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import DocumentBar from "./document_bar.vue";

function mountDocumentBar(props: Record<string, unknown> = {}) {
    return mount(DocumentBar, {
        props: {
            label: "recording.mp3",
            uploadedFileName: "recording.mp3",
            uploadedFileId: 42,
            ...props,
        },
        global: {
            mocks: { $t: (key: string) => key },
        },
    });
}

beforeEach(() => {
    setActivePinia(createPinia());
});

describe("DocumentBar", () => {
    test("renders the filename as a link to the uploaded file", () => {
        const wrapper = mountDocumentBar();

        const link = wrapper.find(".document-bar a");
        expect(link.exists()).toBe(true);
        expect(link.attributes("href")).toBe("/uploaded-files/42/");
        expect(link.text()).toBe("recording.mp3");
    });

    test("shortens long file names but keeps the extension", () => {
        const wrapper = mountDocumentBar({
            uploadedFileName: "a-really-long-recording-name.mp3",
        });

        const link = wrapper.find(".document-bar a");
        expect(link.text()).toBe("a-really-long-record...mp3");
    });
});
