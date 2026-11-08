import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import DocumentBar from "./document_bar.vue";
import { useTranscriptStore } from "./transcript_store";

function mountDocumentBar(props: Record<string, unknown> = {}) {
    return mount(DocumentBar, {
        props: {
            transcriptId: 7,
            projectId: 3,
            projectTitle: "Oral history",
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
    test("renders the project and the file as breadcrumb links", () => {
        const wrapper = mountDocumentBar();

        const links = wrapper.findAll('nav[aria-label="breadcrumb"] ol li a');
        expect(links.map((link) => link.attributes("href"))).toEqual([
            "/projects/3/",
            "/uploaded-files/42/",
        ]);
        expect(links.map((link) => link.text())).toEqual([
            "Oral history",
            "recording.mp3",
        ]);
    });

    test("shortens long file names but keeps the extension", () => {
        const wrapper = mountDocumentBar({
            uploadedFileName: "a-really-long-recording-name.mp3",
        });

        const link = wrapper.find(".document-bar__file-link");
        expect(link.text()).toBe("a-really-long-record...mp3");
    });

    test("shows the saving status and disables the buttons while saving", () => {
        const wrapper = mountDocumentBar({ isSaving: true });

        const status = wrapper.find(".save-status");
        expect(status.text()).toBe("saving");
        expect(status.classes()).toContain("save-status--saving");
        // The rename button is not one of these: it only opens the input, and
        // the label is written by the same save as the content.
        for (const button of wrapper.findAll(".document-bar__actions button")) {
            expect(button.attributes("disabled")).toBeDefined();
        }
    });

    test("reports unsaved changes when not saving", () => {
        const store = useTranscriptStore();
        store.segments = [
            {
                id: "seg_1",
                start: 0,
                end: 1,
                speakerId: null,
                dirty: true,
                words: [],
            },
        ];
        const wrapper = mountDocumentBar({ isSaving: false });

        const status = wrapper.find(".save-status");
        expect(status.text()).toBe("unsaved_changes");
        expect(status.classes()).toContain("save-status--unsaved");
    });
});

describe("DocumentBar renaming", () => {
    test("shows the label from the store as text", () => {
        const store = useTranscriptStore();
        store.loadLabel("Interview");
        const wrapper = mountDocumentBar();

        expect(wrapper.find(".document-bar__title").text()).toBe("Interview");
        expect(wrapper.find(".document-bar__label-input").exists()).toBe(false);
    });

    test("opens an input carrying the current label", async () => {
        const store = useTranscriptStore();
        store.loadLabel("Interview");
        const wrapper = mountDocumentBar();

        await wrapper.find(".document-bar__rename").trigger("click");

        const input = wrapper.find(".document-bar__label-input");
        expect(input.exists()).toBe(true);
        expect((input.element as HTMLInputElement).value).toBe("Interview");
    });

    test("writes the new label to the store on Enter and closes the input", async () => {
        const store = useTranscriptStore();
        store.loadLabel("Interview");
        const wrapper = mountDocumentBar();
        await wrapper.find(".document-bar__rename").trigger("click");

        const input = wrapper.find(".document-bar__label-input");
        await input.setValue("  Second interview  ");
        await input.trigger("keydown.enter");

        expect(store.label).toBe("Second interview");
        expect(store.labelIsDirty).toBe(true);
        expect(wrapper.find(".document-bar__label-input").exists()).toBe(false);
    });

    test("stays open on the keyup of the Enter that pressed the rename button", async () => {
        const wrapper = mountDocumentBar();
        await wrapper.find(".document-bar__rename").trigger("click");

        await wrapper.find(".document-bar__label-input").trigger("keyup.enter");

        expect(wrapper.find(".document-bar__label-input").exists()).toBe(true);
    });

    test("writes the new label when the input loses focus", async () => {
        const store = useTranscriptStore();
        store.loadLabel("Interview");
        const wrapper = mountDocumentBar();
        await wrapper.find(".document-bar__rename").trigger("click");

        const input = wrapper.find(".document-bar__label-input");
        await input.setValue("Second interview");
        await input.trigger("blur");

        expect(store.label).toBe("Second interview");
    });

    test("keeps the label on Escape", async () => {
        const store = useTranscriptStore();
        store.loadLabel("Interview");
        const wrapper = mountDocumentBar();
        await wrapper.find(".document-bar__rename").trigger("click");

        const input = wrapper.find(".document-bar__label-input");
        await input.setValue("Second interview");
        await input.trigger("keyup.escape");

        expect(store.label).toBe("Interview");
        expect(wrapper.find(".document-bar__label-input").exists()).toBe(false);
    });

    test("keeps the label when the input is emptied", async () => {
        const store = useTranscriptStore();
        store.loadLabel("Interview");
        const wrapper = mountDocumentBar();
        await wrapper.find(".document-bar__rename").trigger("click");

        const input = wrapper.find(".document-bar__label-input");
        await input.setValue("   ");
        await input.trigger("keydown.enter");

        expect(store.label).toBe("Interview");
    });

    test("enables the save button for a changed label alone", async () => {
        const store = useTranscriptStore();
        store.loadLabel("Interview");
        const wrapper = mountDocumentBar();
        await wrapper.find(".document-bar__rename").trigger("click");

        const input = wrapper.find(".document-bar__label-input");
        await input.setValue("Second interview");
        await input.trigger("keydown.enter");

        const saveButton = wrapper.findAll(".document-bar__actions button")[1];
        expect(saveButton.attributes("disabled")).toBeUndefined();
    });
});
