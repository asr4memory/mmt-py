import { config } from "@vue/test-utils";

// The customizable select API (Chrome 130+) permits <button> inside <select>,
// <span> inside <option>, and the <selectedcontent> element. Vue's HTML
// conformance checker doesn't know about this spec addition yet.
config.global.config.warnHandler = (msg) => {
    if (
        msg.startsWith("<button> cannot be child of <select>") ||
        msg.startsWith("<span> cannot be child of <option>") ||
        msg.startsWith("Failed to resolve component: selectedcontent")
    ) {
        return;
    }
    console.warn("[Vue warn]:", msg);
};

// jsdom has no matchMedia. The stub reports that no media query matches; a
// test that depends on the viewport width replaces it with vi.stubGlobal.
// Test files that run in the node environment have no window.
if (typeof window !== "undefined") {
    window.matchMedia = (query: string) =>
        ({
            matches: false,
            media: query,
            onchange: null,
            addEventListener: () => {},
            removeEventListener: () => {},
            addListener: () => {},
            removeListener: () => {},
            dispatchEvent: () => false,
        }) as MediaQueryList;
}
