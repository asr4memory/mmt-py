import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";
import DocumentBar from "./document_bar.vue";
import TranscriptTable from "./transcript_table.vue";
import type { TranscriptContent } from "./types";
import updateTranscript from "./update_transcript";

vi.mock("./update_transcript", () => ({
    default: vi.fn(() => Promise.resolve()),
}));

function loadedContent(): TranscriptContent {
    return {
        format: "mmt-transcript",
        version: 1,
        language: "en",
        speakers: [{ id: "spk_1", name: "Alice", color: "#5b9bd5" }],
        entities: {},
        mentions: {},
        redactions: {},
        segments: [
            {
                id: "seg_1",
                start: 0,
                end: 1,
                speakerId: "spk_1",
                words: [
                    {
                        id: "wrd_1",
                        start: 0,
                        end: 1,
                        word: "Hi",
                        score: 1,
                        speakerId: "spk_1",
                        mentionId: null,
                        redactionId: null,
                    },
                ],
            },
        ],
    };
}

async function mountTranscriptTable(content: TranscriptContent) {
    vi.stubGlobal(
        "fetch",
        vi.fn(() => Promise.resolve({ json: () => Promise.resolve(content) })),
    );
    const wrapper = mount(TranscriptTable, {
        props: {
            id: 7,
            label: "recording.mp3",
            mediaType: "audio/mpeg",
            duration: "00:01:00",
            uploadedFile: "recording.mp3",
            uploadedFileId: 42,
            projectId: 3,
        },
        shallow: true,
        global: { mocks: { $t: (key: string) => key } },
    });
    await flushPromises();
    return wrapper;
}

beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(updateTranscript).mockClear();
});

describe("TranscriptTable language round-trip", () => {
    test("saves the language it loaded from the content", async () => {
        const wrapper = await mountTranscriptTable(loadedContent());

        wrapper.findComponent(DocumentBar).vm.$emit("save");
        await flushPromises();

        expect(vi.mocked(updateTranscript).mock.calls[0][1]).toMatchObject({
            language: "en",
        });
    });

    test("saves a null language when the content has none", async () => {
        const content = loadedContent();
        content.language = null;
        const wrapper = await mountTranscriptTable(content);

        wrapper.findComponent(DocumentBar).vm.$emit("save");
        await flushPromises();

        expect(vi.mocked(updateTranscript).mock.calls[0][1].language).toBeNull();
    });
});

describe("TranscriptTable entity round-trip", () => {
    test("saves the entities it loaded from the content", async () => {
        const content = loadedContent();
        content.entities = {
            ent_1: {
                name: "Angela Merkel",
                type: "PER",
                aliases: ["Merkel"],
                wikidataId: "Q567",
            },
        };
        content.mentions = {
            men_1: { label: "PER", score: 1, entityId: "ent_1" },
        };
        content.segments[0].words[0].mentionId = "men_1";
        const wrapper = await mountTranscriptTable(content);

        wrapper.findComponent(DocumentBar).vm.$emit("save");
        await flushPromises();

        expect(vi.mocked(updateTranscript).mock.calls[0][1]).toMatchObject({
            entities: content.entities,
            mentions: content.mentions,
        });
    });
});

describe("TranscriptTable redaction round-trip", () => {
    test("saves the redactions and word links it loaded from the content", async () => {
        const content = loadedContent();
        content.redactions = {
            red_1: { reason: "Names the employer", start: null, end: null },
        };
        content.segments[0].words[0].redactionId = "red_1";
        const wrapper = await mountTranscriptTable(content);

        wrapper.findComponent(DocumentBar).vm.$emit("save");
        await flushPromises();

        const payload = vi.mocked(updateTranscript).mock.calls[0][1];
        expect(payload).toMatchObject({ redactions: content.redactions });
        expect(payload.segments[0].words[0].redactionId).toBe("red_1");
    });

    test("carries an explicit redaction time range through unchanged", async () => {
        const content = loadedContent();
        content.redactions = { red_1: { reason: null, start: 1, end: 2.5 } };
        content.segments[0].words[0].redactionId = "red_1";
        const wrapper = await mountTranscriptTable(content);

        wrapper.findComponent(DocumentBar).vm.$emit("save");
        await flushPromises();

        const payload = vi.mocked(updateTranscript).mock.calls[0][1];
        expect(payload.redactions).toEqual({
            red_1: { reason: null, start: 1, end: 2.5 },
        });
    });
});

describe("TranscriptTable saving state", () => {
    test("marks the document bar as saving until the request resolves", async () => {
        let resolveSave: () => void = () => {};
        vi.mocked(updateTranscript).mockImplementationOnce(
            () => new Promise<void>((resolve) => (resolveSave = resolve)),
        );
        const wrapper = await mountTranscriptTable(loadedContent());
        const documentBar = wrapper.findComponent(DocumentBar);

        expect(documentBar.props("isSaving")).toBe(false);

        documentBar.vm.$emit("save");
        await flushPromises();
        expect(documentBar.props("isSaving")).toBe(true);

        resolveSave();
        await flushPromises();
        expect(documentBar.props("isSaving")).toBe(false);
    });

    test("clears the saving state when the request fails", async () => {
        vi.mocked(updateTranscript).mockImplementationOnce(() =>
            Promise.reject(new Error("failed")),
        );
        vi.spyOn(console, "error").mockImplementation(() => {});
        const wrapper = await mountTranscriptTable(loadedContent());
        const documentBar = wrapper.findComponent(DocumentBar);

        documentBar.vm.$emit("save");
        await flushPromises();

        expect(documentBar.props("isSaving")).toBe(false);
    });
});
