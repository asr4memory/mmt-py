import type { Ref } from "vue";

import { newId } from "./new_id";
import type { Speaker, TranscriptSegment } from "./types";

const SPEAKER_COLORS = ["#5b9bd5", "#70ad47", "#ed7d31", "#9b59b6", "#17a589"];

// The speaker legend: adding, renaming, recoloring and deleting speakers, and
// keeping the segments that reference them consistent.
export function useSpeakers(
    segments: Ref<TranscriptSegment[]>,
    speakers: Ref<Speaker[]>,
) {
    // Marks every segment that references the speaker, either directly or
    // through one of its words, as dirty.
    function markSegmentsReferencingSpeakerDirty(speakerId: string) {
        segments.value.forEach((segment) => {
            const references =
                segment.speakerId === speakerId ||
                segment.words.some((word) => word.speakerId === speakerId);
            if (references) {
                segment.dirty = true;
            }
        });
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

        // Segments reference the speaker by id, so the rename leaves their
        // speakerId untouched; mark the ones that point at this speaker dirty
        // so the changed name gets persisted on the next save.
        markSegmentsReferencingSpeakerDirty(speakerId);
    }

    function setSpeakerColor(speakerId: string, color: string) {
        const speaker = speakers.value.find((s) => s.id === speakerId);
        if (!speaker) {
            throw new Error(`Speaker does not exist: ${speakerId}`);
        }
        if (color === speaker.color) return;

        speaker.color = color;

        // The color lives on the speaker, not on the segments, so mark the
        // segments that reference this speaker dirty to make the change
        // saveable.
        markSegmentsReferencingSpeakerDirty(speakerId);
    }

    function deleteSpeaker(speakerId: string) {
        const speaker = speakers.value.find((s) => s.id === speakerId);
        if (!speaker) {
            throw new Error(`Speaker does not exist: ${speakerId}`);
        }

        speakers.value = speakers.value.filter((s) => s.id !== speakerId);

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
        addSpeaker,
        renameSpeaker,
        setSpeakerColor,
        deleteSpeaker,
    };
}
