import { onUnmounted, toValue, watch, type MaybeRefOrGetter } from "vue";

// While the tab is backgrounded the document title is the only reliable upload
// indicator, so reflect progress there and restore the original title once
// nothing is uploading. `current` is the 1-based number of the active upload
// (null when none is active), `total` the number of files in the queue.
export function useUploadTabTitle(
    progress: MaybeRefOrGetter<number>,
    current: MaybeRefOrGetter<number | null>,
    total: MaybeRefOrGetter<number>,
) {
    const originalTitle = document.title;

    watch(
        () => ({
            progress: toValue(progress),
            current: toValue(current),
            total: toValue(total),
        }),
        ({ progress, current, total }) => {
            document.title =
                current === null
                    ? originalTitle
                    : `↑ ${progress}% · ${current}/${total}`;
        },
        { immediate: true },
    );

    onUnmounted(() => {
        document.title = originalTitle;
    });
}
