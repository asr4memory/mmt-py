const POLL_INTERVAL_MS = 3000;

/**
 * Performs one status check for an uploaded file.
 *
 * Returns true when the file is still processing and polling should continue,
 * false when polling should stop because the page has been reloaded.
 */
export async function checkUploadStatus(
    statusUrl: string,
    reload: () => void,
): Promise<boolean> {
    const response = await fetch(statusUrl);

    // A non-OK response means the session expired or access was revoked;
    // reload so the user lands on the login page.
    if (!response.ok) {
        reload();
        return false;
    }

    const { status } = await response.json();
    if (status !== "processing") {
        reload();
        return false;
    }

    return true;
}

/**
 * Alpine component that reloads the page once an uploaded file has left the
 * processing state. Alpine calls init() when the element is set up and
 * destroy() when it is removed.
 */
export function createUploadStatusPoller(
    statusUrl: string,
    reload: () => void = () => window.location.reload(),
) {
    let intervalId: ReturnType<typeof setInterval> | undefined;

    return {
        init(): void {
            intervalId = setInterval(async () => {
                if (!(await checkUploadStatus(statusUrl, reload))) {
                    clearInterval(intervalId);
                }
            }, POLL_INTERVAL_MS);
        },

        destroy(): void {
            clearInterval(intervalId);
        },
    };
}
