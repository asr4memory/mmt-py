import { type Ref, ref } from "vue";

import { newId } from "./new_id";
import type {
    Entity,
    EntityType,
    Mention,
    MentionRef,
    TranscriptSegment,
} from "./types";

// The entity register: resolving an entity, creating one, and linking mentions
// to it. The type of a linked mention is kept equal to the type of its entity.
export function useEntities(
    segments: Ref<TranscriptSegment[]>,
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

    // The mentions linked to the entity, in the document order of their first
    // words.
    function mentionsOfEntity(entityId: string): MentionRef[] {
        const refs = new Map<string, MentionRef>();
        segments.value.forEach((segment, segmentIndex) => {
            for (const word of segment.words) {
                const mentionId = word.mentionId;
                if (!mentionId) continue;
                if (mentions.value[mentionId]?.entityId !== entityId) continue;
                const existing = refs.get(mentionId);
                if (existing) {
                    existing.surface += ` ${word.word}`;
                } else {
                    refs.set(mentionId, {
                        mentionId,
                        segmentIndex,
                        start: word.start,
                        surface: word.word,
                    });
                }
            }
        });
        return [...refs.values()];
    }

    // Add an entity without Wikidata ID and return its id. Throws when the
    // trimmed name is empty or already the name of an entity in the register.
    function createEntity(name: string, type: EntityType): string {
        const trimmed = name.trim();
        if (trimmed === "") {
            throw new Error("Entity name is empty");
        }
        const taken = Object.values(entities.value).some(
            (entity) => entity.name === trimmed,
        );
        if (taken) {
            throw new Error(`Entity name already exists: ${trimmed}`);
        }
        const id = newId("ent");
        entities.value[id] = {
            name: trimmed,
            type,
            wikidataId: null,
        };
        entitiesAreDirty.value = true;
        return id;
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

    // Write the entity's name and Wikidata ID. The type cannot change, so the
    // linked mentions keep the entity's type.
    function updateEntity(
        entityId: string,
        name: string,
        wikidataId: string | null,
    ) {
        const target = entities.value[entityId];
        if (!target) {
            throw new Error(`Entity does not exist: ${entityId}`);
        }
        target.name = name;
        target.wikidataId = wikidataId;
        entitiesAreDirty.value = true;
    }

    // Unlink every mention of the entity and remove the entity. The mentions
    // stay, with their type.
    function deleteEntity(entityId: string) {
        for (const mention of Object.values(mentions.value)) {
            if (mention.entityId === entityId) mention.entityId = null;
        }
        delete entities.value[entityId];
        entitiesAreDirty.value = true;
    }

    return {
        entitiesAreDirty,
        loadEntities,
        markEntitiesSaved,
        entity,
        mentionCount,
        mentionsOfEntity,
        createEntity,
        linkMention,
        unlinkMention,
        updateEntity,
        deleteEntity,
    };
}
