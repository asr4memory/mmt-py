import type { Entity } from "./types";

// The normalisation and matching rules of entity_linking.py. Both
// implementations are tested against
// mmt/transcripts/tests/data/normalization_cases.json.

// Punctuation (P*) and symbols (S*) at the start or the end of the text.
const EDGE_PUNCTUATION_AND_SYMBOLS = /^[\p{P}\p{S}]+|[\p{P}\p{S}]+$/gu;

// The surface text without surrounding whitespace, punctuation and symbols,
// as a proposed entity name. Case and Unicode form are kept.
export function trimmedSurface(text: string): string {
    const collapsed = text.replace(/\s+/gu, " ").trim();
    // Stripping "„ Merkel “" leaves spaces at both ends.
    return collapsed.replace(EDGE_PUNCTUATION_AND_SYMBOLS, "").trim();
}

// The form of a name or surface text that matching compares.
export function normalizedSurface(text: string): string {
    return trimmedSurface(text.normalize("NFKC")).toLowerCase();
}

function normalizedNames(entity: Entity): string[] {
    return [entity.name, ...entity.aliases].map(normalizedSurface);
}

// Rule A, as defined at matching_entity in entity_linking.py.
export function matchingEntity(
    surface: string,
    type: string,
    entities: Record<string, Entity>,
): string | null {
    const normalized = normalizedSurface(surface);
    for (const [id, entity] of Object.entries(entities)) {
        if (entity.type !== type) continue;
        if (normalizedNames(entity).includes(normalized)) return id;
    }
    return null;
}

// The entity, of any type, whose name or one of whose aliases normalises to
// the same form as the text, or null. Invariant 4 forbids a second one.
export function entityNamed(
    text: string,
    entities: Record<string, Entity>,
): string | null {
    const normalized = normalizedSurface(text);
    for (const [id, entity] of Object.entries(entities)) {
        if (normalizedNames(entity).includes(normalized)) return id;
    }
    return null;
}

export interface RankedEntity {
    id: string;
    entity: Entity;
    // True for the entity that matchingEntity returns, which the combobox
    // preselects.
    exactMatch: boolean;
}

// The number of distinct words of the query that occur in any of the names.
function sharedWordCount(queryWords: Set<string>, names: string[]): number {
    const nameWords = new Set(names.flatMap((name) => name.split(" ")));
    let count = 0;
    for (const word of queryWords) {
        if (nameWords.has(word)) count += 1;
    }
    return count;
}

// Every entity, ordered by group (the matchingEntity result, a name or alias
// starting with the query, a name or alias containing it, names sharing words
// with it, the rest) and by name within a group. The shared-word group is
// ordered by the number of shared words first.
export function rankEntities(
    query: string,
    type: string,
    entities: Record<string, Entity>,
    language?: string | null,
): RankedEntity[] {
    const normalizedQuery = normalizedSurface(query);
    const queryWords = new Set(normalizedQuery.split(" ").filter(Boolean));
    const matchId = matchingEntity(query, type, entities);

    function rank(id: string, entity: Entity) {
        if (id === matchId) return { group: 0, shared: 0 };
        const names = normalizedNames(entity);
        if (names.some((name) => name.startsWith(normalizedQuery))) {
            return { group: 1, shared: 0 };
        }
        if (names.some((name) => name.includes(normalizedQuery))) {
            return { group: 2, shared: 0 };
        }
        const shared = sharedWordCount(queryWords, names);
        return { group: shared > 0 ? 3 : 4, shared };
    }

    return Object.entries(entities)
        .map(([id, entity]) => ({ id, entity, ...rank(id, entity) }))
        .sort(
            (a, b) =>
                a.group - b.group ||
                b.shared - a.shared ||
                a.entity.name.localeCompare(
                    b.entity.name,
                    language ?? undefined,
                ),
        )
        .map(({ id, entity }) => ({ id, entity, exactMatch: id === matchId }));
}
