// Ids are prefixed by tier ('wrd', 'seg', 'spk', 'men', 'red') and must be
// unique across the whole transcript content.
export function newId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID()}`;
}
