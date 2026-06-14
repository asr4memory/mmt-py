export function readString(element: HTMLElement, key: string): string {
    const value = element.dataset[key];
    if (value === undefined) throw new Error(`Missing data attribute: data-${key}`);
    return value;
}

export function readInt(element: HTMLElement, key: string): number {
    return Number.parseInt(readString(element, key), 10);
}

export function readBool(element: HTMLElement, key: string): boolean {
    return readString(element, key) === "true";
}

export function readIntList(element: HTMLElement, key: string): number[] {
    return readString(element, key)
        .split(",")
        .filter((s) => s !== "")
        .map((s) => Number.parseInt(s, 10));
}
