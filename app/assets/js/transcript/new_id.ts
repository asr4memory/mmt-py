// Ids are prefixed by tier ('wrd', 'seg', 'spk', 'men', 'red') and must be
// unique across the whole transcript content. The uuid is spelled without
// dashes, so an id written here looks like one written by the backend.
export function newId(prefix: string): string {
    return `${prefix}_${crypto.randomUUID().replaceAll("-", "")}`;
}
