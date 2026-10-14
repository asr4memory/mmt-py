import type { Ref } from "vue";

import type { Entity, Mention } from "./types";

// The entity register: resolving an entity and the mentions linked to it.
export function useEntities(
    mentions: Ref<Record<string, Mention>>,
    entities: Ref<Record<string, Entity>>,
) {
    // Resolve an entityId to its Entity, or null when the mention is unlinked
    // or the entity is missing.
    function entity(entityId?: string | null): Entity | null {
        if (!entityId) return null;
        return entities.value[entityId] ?? null;
    }

    // The number of mentions linked to the entity, which may be zero.
    function mentionCount(entityId: string): number {
        return Object.values(mentions.value).filter(
            (mention) => mention.entityId === entityId,
        ).length;
    }

    return {
        entity,
        mentionCount,
    };
}
