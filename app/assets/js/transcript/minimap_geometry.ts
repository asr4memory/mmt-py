// Geometry for the transcript minimap. The vertical axis of the minimap is the
// height of the rendered document, not media time, so every position is a
// percentage of the document's scroll height.

export interface SegmentBox {
    top: number;
    height: number;
}

export interface Band {
    top: number;
    height: number;
}

// Convert the viewport rectangles of the segment elements into document space
// by adding the current scroll offset.
export function measureSegments(
    elements: HTMLElement[],
    scrollY: number,
): SegmentBox[] {
    return elements.map((element) => {
        const rect = element.getBoundingClientRect();
        return { top: rect.top + scrollY, height: rect.height };
    });
}

// Express each segment box as a percentage of the document height.
export function minimapBands(
    boxes: SegmentBox[],
    documentHeight: number,
): Band[] {
    if (documentHeight <= 0) return [];
    return boxes.map((box) => ({
        top: (box.top / documentHeight) * 100,
        height: (box.height / documentHeight) * 100,
    }));
}

// The part of the document that is currently visible, as a percentage band.
export function viewportBand(
    scrollY: number,
    viewportHeight: number,
    documentHeight: number,
): Band {
    if (documentHeight <= 0) return { top: 0, height: 100 };
    const height = Math.min((viewportHeight / documentHeight) * 100, 100);
    const top = Math.min((scrollY / documentHeight) * 100, 100 - height);
    return { top: Math.max(top, 0), height };
}

// The scroll offset for a click at the given fraction of the minimap's height.
// The clicked position is centred in the viewport and clamped to the document.
export function scrollTargetForFraction(
    fraction: number,
    documentHeight: number,
    viewportHeight: number,
): number {
    const target = fraction * documentHeight - viewportHeight / 2;
    const maximum = Math.max(documentHeight - viewportHeight, 0);
    return Math.min(Math.max(target, 0), maximum);
}
