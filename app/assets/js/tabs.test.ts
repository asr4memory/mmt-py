import { afterEach, describe, expect, test } from "vitest";
import { initTabs, markActiveTab } from "./tabs";

function makeTabBar(): HTMLElement {
    const nav = document.createElement("nav");
    nav.className = "tabs";
    nav.innerHTML = `
        <ul class="tabs__list">
            <li class="tabs__item">
                <a class="tabs__link" data-testid="uploaded-files-tab"
                   href="/projects/1/" aria-current="page">Uploaded files</a>
            </li>
            <li class="tabs__item">
                <a class="tabs__link" data-testid="downloads-tab"
                   href="/projects/1/downloads/">Downloadable files</a>
            </li>
        </ul>
    `;
    document.body.append(nav);
    return nav;
}

function current(nav: HTMLElement): string[] {
    const links = nav.querySelectorAll<HTMLAnchorElement>(
        'a.tabs__link[aria-current="page"]',
    );
    return Array.from(links, (link) => link.dataset.testid ?? "");
}

afterEach(() => {
    document.body.innerHTML = "";
});

describe("markActiveTab", () => {
    test("moves aria-current to the link with the given path", () => {
        const nav = makeTabBar();

        markActiveTab(document, "/projects/1/downloads/");

        expect(current(nav)).toEqual(["downloads-tab"]);
    });

    test("marks no tab when no link matches the path", () => {
        const nav = makeTabBar();

        markActiveTab(document, "/projects/1/settings/");

        expect(current(nav)).toEqual([]);
    });
});

describe("initTabs", () => {
    test("marks the tab of the current path after an htmx swap", () => {
        const nav = makeTabBar();
        initTabs();

        window.history.pushState({}, "", "/projects/1/downloads/");
        document.body.dispatchEvent(
            new Event("htmx:afterSwap", { bubbles: true }),
        );

        expect(current(nav)).toEqual(["downloads-tab"]);
    });
});
