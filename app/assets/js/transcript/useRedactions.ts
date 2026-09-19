import type { Ref } from "vue";

import { newId } from "./new_id";
import type { Redaction, TranscriptSegment } from "./types";

// The redaction occurrence tier, independent of the mentions: runs of words
// within one segment that must not be published.
export function useRedactions(
  segments: Ref<TranscriptSegment[]>,
  redactions: Ref<Record<string, Redaction>>,
) {
  // Resolve a redactionId to its Redaction, or null when the word is
  // unlinked or the redaction is missing.
  function redaction(redactionId?: string | null): Redaction | null {
    if (!redactionId) return null;
    return redactions.value[redactionId] ?? null;
  }

  // The full surface text of a redaction: the words within the segment that
  // share the redactionId, joined in order. Redactions do not cross
  // segments.
  function redactionText(
    segmentIndex: number,
    redactionId?: string | null,
  ): string {
    if (!redactionId) return "";
    const segment = segments.value[segmentIndex];
    if (!segment) return "";
    return segment.words
      .filter((word) => word.redactionId === redactionId)
      .map((word) => word.word)
      .join(" ");
  }

  // Mark a word as not to be published: create a fresh redaction with no
  // reason and no explicit time range, and point the word at it. Returns the
  // new redaction id, or an empty string when there is no such word.
  function createRedaction(segmentIndex: number, wordIndex: number): string {
    const segment = segments.value[segmentIndex];
    const word = segment?.words[wordIndex];
    if (!word) return "";
    const id = newId("red");
    redactions.value[id] = { reason: null, start: null, end: null };
    word.redactionId = id;
    segment.dirty = true;
    return id;
  }

  // Grow a redaction onto the word just past its run, left or right. Does
  // nothing at a segment edge, which is what keeps a redaction inside one
  // segment, and nothing when the neighbour already belongs to another
  // redaction. A mention on the neighbour is not consulted: the two
  // occurrence tiers are independent.
  function extendRedaction(
    segmentIndex: number,
    redactionId: string,
    side: "left" | "right",
  ) {
    const segment = segments.value[segmentIndex];
    if (!segment) return;
    const indices = segment.words
      .map((word, i) => (word.redactionId === redactionId ? i : -1))
      .filter((i) => i >= 0);
    if (indices.length === 0) return;
    const target =
      side === "left" ? indices[0] - 1 : indices[indices.length - 1] + 1;
    const neighbour = segment.words[target];
    if (!neighbour || neighbour.redactionId) return;
    neighbour.redactionId = redactionId;
    segment.dirty = true;
  }

  // Shorten a redaction by unlinking the word at one end of its run. Does
  // nothing for a single-word redaction, because a redaction that no word
  // references is invalid; removeRedaction covers that case.
  function reduceRedaction(
    segmentIndex: number,
    redactionId: string,
    side: "left" | "right",
  ) {
    const segment = segments.value[segmentIndex];
    if (!segment) return;
    const indices = segment.words
      .map((word, i) => (word.redactionId === redactionId ? i : -1))
      .filter((i) => i >= 0);
    if (indices.length <= 1) return;
    const target = side === "left" ? indices[0] : indices[indices.length - 1];
    segment.words[target].redactionId = null;
    segment.dirty = true;
  }

  // Remove a whole redaction: unlink every word in the segment that carries
  // the redactionId and drop the redaction itself, discarding its reason.
  // The words and their mentions stay.
  function removeRedaction(segmentIndex: number, redactionId: string) {
    const segment = segments.value[segmentIndex];
    if (!segment) return;
    for (const word of segment.words) {
      if (word.redactionId === redactionId) {
        word.redactionId = null;
      }
    }
    delete redactions.value[redactionId];
    segment.dirty = true;
  }

  // Record why a passage is redacted. The reason belongs to the
  // transcript-level entry rather than to one segment, so the segments
  // holding the redaction's words are looked up here and marked dirty, which
  // is what makes a change of reason alone saveable.
  function setRedactionReason(redactionId: string, reason: string) {
    const target = redactions.value[redactionId];
    if (!target) return;
    target.reason = reason;
    segments.value.forEach((segment) => {
      const references = segment.words.some(
        (word) => word.redactionId === redactionId,
      );
      if (references) {
        segment.dirty = true;
      }
    });
  }

  return {
    redaction,
    redactionText,
    createRedaction,
    extendRedaction,
    reduceRedaction,
    removeRedaction,
    setRedactionReason,
  };
}
