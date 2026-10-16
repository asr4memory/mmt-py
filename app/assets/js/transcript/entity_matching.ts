// Punctuation (P*) and symbols (S*) at the start or the end of the text.
const EDGE_PUNCTUATION_AND_SYMBOLS = /^[\p{P}\p{S}]+|[\p{P}\p{S}]+$/gu;

// The surface text without surrounding whitespace, punctuation and symbols,
// as a proposed entity name. Case and Unicode form are kept.
export function trimmedSurface(text: string): string {
    const collapsed = text.replace(/\s+/gu, " ").trim();
    // Stripping "„ Merkel “" leaves spaces at both ends.
    return collapsed.replace(EDGE_PUNCTUATION_AND_SYMBOLS, "").trim();
}
