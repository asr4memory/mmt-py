// A segment counts as visible when any part of it lies between the lower edge
// of the sticky header and the lower edge of the viewport.
export default function segmentIsInView(
    rect: DOMRect,
    headerBottom: number,
    viewportHeight: number,
): boolean {
    return rect.bottom > headerBottom && rect.top < viewportHeight;
}
