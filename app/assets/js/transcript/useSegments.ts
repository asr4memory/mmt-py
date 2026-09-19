import { computed, type Ref } from "vue";

import { newId } from "./new_id";
import type { Speaker, TranscriptSegment } from "./types";

// The segment list itself: which segments are unsaved, inserting and deleting
// segments.
export function useSegments(
  segments: Ref<TranscriptSegment[]>,
  speakers: Ref<Speaker[]>,
  pruneOrphans: () => void,
) {
  const dirtySegmentCount = computed(() => {
    const dirtySegments = segments.value.filter(
      (segment) =>
        segment.dirty === true ||
        segment.words.some((word) => word.dirty === true),
    );
    return dirtySegments.length;
  });

  const transcriptIsDirty = computed(() => dirtySegmentCount.value > 0);

  // Removes the dirty flags in place, so only the segments that were
  // changed re-render after a save.
  function markSaved() {
    for (const segment of segments.value) {
      delete segment.dirty;
      for (const word of segment.words) {
        delete word.dirty;
      }
    }
  }

  function deleteSegment(segmentId: string) {
    const index = segments.value.findIndex(
      (segment) => segment.id === segmentId,
    );
    const firstPart = segments.value.slice(0, index);
    const lastPart = segments.value.slice(index + 1);
    segments.value = firstPart.concat(lastPart);
    pruneOrphans();
  }

  function buildSegment(
    text: string,
    start: number,
    end: number,
  ): TranscriptSegment {
    const speakerId = speakers.value[0]?.id ?? null;
    return {
      id: newId("seg"),
      start: start,
      end: end,
      speakerId: speakerId,
      words: [
        {
          id: newId("wrd"),
          start: start,
          end: start + 3.0,
          word: text,
          score: 1.0,
          speakerId: speakerId,
        },
      ],
    };
  }

  function insertSegmentBefore(text: string, segmentId: string | null = null) {
    // Omit segmentId to insert the segment at the end.
    const index =
      typeof segmentId === "string"
        ? segments.value.findIndex((segment) => segment.id === segmentId)
        : segments.value.length;

    // start
    const start = index === 0 ? 0.0 : segments.value[index - 1].end;
    // end
    const end =
      index === segments.value.length - 1
        ? start + 15.0
        : segments.value[index].start;

    const newSegment = buildSegment(text, start, end);
    const firstPart = segments.value.slice(0, index);
    const lastPart = segments.value.slice(index);
    segments.value = firstPart.concat(newSegment, lastPart);
  }

  function insertSegmentAfter(text: string, segmentId: string) {
    const index = segments.value.findIndex(
      (segment) => segment.id === segmentId,
    );
    if (index === -1) return;

    // The new segment fills the gap from this segment's end up to the
    // start of its successor, or runs 15s when there is none.
    const start = segments.value[index].end;
    const end =
      index === segments.value.length - 1
        ? start + 15.0
        : segments.value[index + 1].start;

    const newSegment = buildSegment(text, start, end);
    const firstPart = segments.value.slice(0, index + 1);
    const lastPart = segments.value.slice(index + 1);
    segments.value = firstPart.concat(newSegment, lastPart);
  }

  return {
    dirtySegmentCount,
    transcriptIsDirty,
    markSaved,
    deleteSegment,
    insertSegmentBefore,
    insertSegmentAfter,
  };
}
