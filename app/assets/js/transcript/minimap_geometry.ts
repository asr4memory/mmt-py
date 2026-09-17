// Geometry for the transcript minimap. The vertical axis of the minimap is the
// height of the rendered document, not media time, so every measurement is
// turned into a share of the document's scroll height.

export interface SegmentBox {
    top: number;
    height: number;
}

export interface MinimapSpans {
    // The share of the document above the first segment and below the last
    // one. Both are rendered as empty boxes so that the bands keep their
    // position within the strip.
    leading: number;
    bands: number[];
    trailing: number;
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

// The share of the document height that each segment takes up. A segment runs
// from its own top to the top of the next segment, so the margin between two
// segments belongs to the preceding one and the shares of the whole strip add
// up to one. The shares are exact fractions: the bands are laid out one after
// another rather than positioned individually, which is what keeps the edge of
// one band and the edge of the next on the same pixel.
export function minimapSpans(
    boxes: SegmentBox[],
    documentHeight: number,
): MinimapSpans {
    if (documentHeight <= 0 || boxes.length === 0) {
        return { leading: 0, bands: [], trailing: 0 };
    }
    const last = boxes[boxes.length - 1];
    const end = last.top + last.height;
    const bands = boxes.map((box, index) => {
        const next = boxes[index + 1];
        const bottom = next ? next.top : end;
        return (bottom - box.top) / documentHeight;
    });
    return {
        leading: boxes[0].top / documentHeight,
        bands,
        trailing: Math.max(documentHeight - end, 0) / documentHeight,
    };
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
