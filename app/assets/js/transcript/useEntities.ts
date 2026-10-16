import { type Ref, ref } from "vue";

import {
    entityProblems,
    hasProblems,
    normalizedSurface,
} from "./entity_matching";
import { newId } from "./new_id";
import type { Entity, EntityType, Mention } from "./types";

// The entity register: resolving an entity, creating one, and linking mentions
// to it. The type of a linked mention is kept equal to the type of its entity.
export function useEntities(
    mentions: Ref<Record<string, Mention>>,
    entities: Ref<Record<string, Entity>>,
) {
    // True after an entity or a link changed since the last load or save.
    const entitiesAreDirty = ref(false);

    function loadEntities(map: Record<string, Entity>) {
        entities.value = map;
        entitiesAreDirty.value = false;
    }

    function markEntitiesSaved() {
        entitiesAreDirty.value = false;
    }

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

    // Add an entity without aliases and Wikidata ID and return its id. Throws
    // when the name is empty after normalisation or already a name or alias
    // in the register.
    function createEntity(name: string, type: EntityType): string {
        const values = { name: name.trim(), aliases: [], wikidataId: null };
        if (hasProblems(entityProblems(values, entities.value, null))) {
            throw new Error(`Entity name is empty or taken: ${values.name}`);
        }
        const id = newId("ent");
        entities.value[id] = { ...values, type };
        entitiesAreDirty.value = true;
        return id;
    }

    // Write the given values to the entity. Name and aliases are trimmed, an
    // alias that is empty or repeats the name or an earlier alias after
    // normalisation is dropped, and an empty Wikidata ID is stored as null.
    // A new type is set on every linked mention. Throws when the entity does
    // not exist or the values violate the register's invariants.
    function updateEntity(entityId: string, values: Partial<Entity>) {
        const current = entities.value[entityId];
        if (!current) {
            throw new Error(`Entity does not exist: ${entityId}`);
        }
        const name = (values.name ?? current.name).trim();
        const seen = new Set([normalizedSurface(name)]);
        const aliases: string[] = [];
        for (const alias of values.aliases ?? current.aliases) {
            const normalized = normalizedSurface(alias);
            if (normalized === "" || seen.has(normalized)) continue;
            seen.add(normalized);
            aliases.push(alias.trim());
        }
        const wikidataId =
            ("wikidataId" in values
                ? values.wikidataId
                : current.wikidataId
            )?.trim() || null;
        const updated: Entity = {
            name,
            type: values.type ?? current.type,
            aliases,
            wikidataId,
        };
        if (hasProblems(entityProblems(updated, entities.value, entityId))) {
            throw new Error(`Entity values violate the register: ${entityId}`);
        }
        if (updated.type !== current.type) {
            for (const mention of Object.values(mentions.value)) {
                if (mention.entityId === entityId) mention.type = updated.type;
            }
        }
        entities.value[entityId] = updated;
        entitiesAreDirty.value = true;
    }

    // Remove the entity and unlink its mentions, which keep their type.
    function deleteEntity(entityId: string) {
        if (!(entityId in entities.value)) return;
        for (const mention of Object.values(mentions.value)) {
            if (mention.entityId === entityId) mention.entityId = null;
        }
        delete entities.value[entityId];
        entitiesAreDirty.value = true;
    }

    // Point the mention at the entity and give it the entity's type.
    function linkMention(mentionId: string, entityId: string) {
        const mention = mentions.value[mentionId];
        if (!mention) {
            throw new Error(`Mention does not exist: ${mentionId}`);
        }
        const target = entities.value[entityId];
        if (!target) {
            throw new Error(`Entity does not exist: ${entityId}`);
        }
        mention.entityId = entityId;
        mention.type = target.type;
        entitiesAreDirty.value = true;
    }

    // Clear the mention's link. The mention keeps its type, and the entity
    // stays in the register.
    function unlinkMention(mentionId: string) {
        const mention = mentions.value[mentionId];
        if (!mention || mention.entityId === null) return;
        mention.entityId = null;
        entitiesAreDirty.value = true;
    }

    return {
        entitiesAreDirty,
        loadEntities,
        markEntitiesSaved,
        entity,
        mentionCount,
        createEntity,
        linkMention,
        unlinkMention,
        updateEntity,
        deleteEntity,
    };
}
