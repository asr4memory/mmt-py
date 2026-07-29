/**
 * htmx replaces the tab panel only, so the tab bar keeps the aria-current
 * attribute the server rendered for the tab that was active when the page was
 * loaded. These functions move that attribute to the tab of the current path
 * after a swap.
 */

export function markActiveTab(root: ParentNode, pathname: string): void {
    const links = root.querySelectorAll<HTMLAnchorElement>("a.tabs__link");
    for (const link of links) {
        if (link.pathname === pathname) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    }
}

export function initTabs(): void {
    // htmx pushes the new URL before it swaps, so the location is already the
    // one of the fetched tab when this runs.
    document.body.addEventListener("htmx:afterSwap", () => {
        markActiveTab(document, window.location.pathname);
    });
}
