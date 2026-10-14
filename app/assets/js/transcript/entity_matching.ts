import type { Entity } from "./types";

// The normalisation and matching rules of entity_linking.py. Both
// implementations are tested against
// mmt/transcripts/tests/data/normalization_cases.json.

// Punctuation (P*) and symbols (S*) at the start or the end of the text.
const EDGE_PUNCTUATION_AND_SYMBOLS = /^[\p{P}\p{S}]+|[\p{P}\p{S}]+$/gu;

// The form of a name or surface text that matching compares.
export function normalizedSurface(text: string): string {
    let result = text.normalize("NFKC");
    result = result.replace(/\s+/gu, " ").trim();
    result = result.replace(EDGE_PUNCTUATION_AND_SYMBOLS, "");
    // Stripping "„ Merkel “" leaves spaces at both ends.
    result = result.trim();
    return result.toLowerCase();
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

export interface RankedEntity {
    id: string;
    entity: Entity;
    // True for the entity that matchingEntity returns, which the combobox
    // preselects.
    exactMatch: boolean;
}

// Every entity, ordered by group (the matchingEntity result, a name or alias
// starting with the query, a name or alias containing it, the rest) and by
// name within a group.
export function rankEntities(
    query: string,
    type: string,
    entities: Record<string, Entity>,
    language?: string | null,
): RankedEntity[] {
    const normalizedQuery = normalizedSurface(query);
    const matchId = matchingEntity(query, type, entities);

    function group(id: string, entity: Entity): number {
        if (id === matchId) return 0;
        const names = normalizedNames(entity);
        if (names.some((name) => name.startsWith(normalizedQuery))) return 1;
        if (names.some((name) => name.includes(normalizedQuery))) return 2;
        return 3;
    }

    return Object.entries(entities)
        .map(([id, entity]) => ({ id, entity, group: group(id, entity) }))
        .sort(
            (a, b) =>
                a.group - b.group ||
                a.entity.name.localeCompare(
                    b.entity.name,
                    language ?? undefined,
                ),
        )
        .map(({ id, entity }) => ({ id, entity, exactMatch: id === matchId }));
}
