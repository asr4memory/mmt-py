import { type Ref, ref } from "vue";

import { newId } from "./new_id";
import type { Speaker, TranscriptSegment } from "./types";

const SPEAKER_COLORS = ["#5b9bd5", "#70ad47", "#ed7d31", "#9b59b6", "#17a589"];

// The speaker legend: adding, renaming, recoloring and deleting speakers, and
// keeping the segments that reference them consistent.
export function useSpeakers(
    segments: Ref<TranscriptSegment[]>,
    speakers: Ref<Speaker[]>,
) {
    // True after a speaker was added, renamed, recolored or deleted since the
    // last load or save.
    const speakersAreDirty = ref(false);

    function loadSpeakers(list: Speaker[]) {
        speakers.value = list;
        speakersAreDirty.value = false;
    }

    function markSpeakersSaved() {
        speakersAreDirty.value = false;
    }

    function addSpeaker(name: string) {
        const trimmed = name.trim();
        if (!trimmed) return;
        if (speakers.value.some((s) => s.name === trimmed)) {
            throw new Error(`Speaker already exists: ${trimmed}`);
        }
        speakers.value.push({
            id: newId("spk"),
            name: trimmed,
            color: SPEAKER_COLORS[
                speakers.value.length % SPEAKER_COLORS.length
            ],
        });
        speakersAreDirty.value = true;
    }

    function renameSpeaker(speakerId: string, newName: string) {
        const trimmed = newName.trim();
        if (!trimmed) return;
        const speaker = speakers.value.find((s) => s.id === speakerId);
        if (!speaker) {
            throw new Error(`Speaker does not exist: ${speakerId}`);
        }
        if (trimmed === speaker.name) return;
        if (
            speakers.value.some((s) => s.id !== speakerId && s.name === trimmed)
        ) {
            throw new Error(`Speaker already exists: ${trimmed}`);
        }

        speaker.name = trimmed;
        speakersAreDirty.value = true;
    }

    function setSpeakerColor(speakerId: string, color: string) {
        const speaker = speakers.value.find((s) => s.id === speakerId);
        if (!speaker) {
            throw new Error(`Speaker does not exist: ${speakerId}`);
        }
        if (color === speaker.color) return;

        speaker.color = color;
        speakersAreDirty.value = true;
    }

    function deleteSpeaker(speakerId: string) {
        const speaker = speakers.value.find((s) => s.id === speakerId);
        if (!speaker) {
            throw new Error(`Speaker does not exist: ${speakerId}`);
        }

        speakers.value = speakers.value.filter((s) => s.id !== speakerId);
        speakersAreDirty.value = true;

        // Segments and words reference the speaker by id; clear those
        // references and mark the affected segments dirty so the change gets
        // persisted on the next save.
        segments.value.forEach((segment) => {
            let references = false;
            if (segment.speakerId === speakerId) {
                segment.speakerId = null;
                references = true;
            }
            segment.words.forEach((word) => {
                if (word.speakerId === speakerId) {
                    word.speakerId = null;
                    references = true;
                }
            });
            if (references) {
                segment.dirty = true;
            }
        });
    }

    return {
        speakersAreDirty,
        loadSpeakers,
        markSpeakersSaved,
        addSpeaker,
        renameSpeaker,
        setSpeakerColor,
        deleteSpeaker,
    };
}
