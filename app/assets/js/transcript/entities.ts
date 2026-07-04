// Single source of truth mapping an NER label to its display metadata: the
// i18n key for its human-readable name and the CSS custom property carrying its
// colour. Keep the labels in sync with the backend NER tagset.
export interface EntityMeta {
    nameKey: string;
    colorVar: string;
}

const ENTITY_META: Record<string, EntityMeta> = {
    PER: { nameKey: "entity_per", colorVar: "--entity-person-bg" },
    LOC: { nameKey: "entity_loc", colorVar: "--entity-location-bg" },
    ORG: { nameKey: "entity_org", colorVar: "--entity-org-bg" },
    DATE: { nameKey: "entity_date", colorVar: "--entity-date-bg" },
};

// Metadata for a label, or null for an unknown label so callers can degrade
// gracefully rather than crash.
export function entityMeta(label?: string | null): EntityMeta | null {
    if (!label) return null;
    return ENTITY_META[label] ?? null;
}
