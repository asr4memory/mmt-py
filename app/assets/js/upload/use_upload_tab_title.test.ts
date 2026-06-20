import { describe, expect, test, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { defineComponent, ref } from "vue";

import { useUploadTabTitle } from "./use_upload_tab_title";

function setup(progress: number, current: number | null, total: number) {
    const p = ref(progress);
    const c = ref<number | null>(current);
    const t = ref(total);
    const wrapper = mount(
        defineComponent({
            setup() {
                useUploadTabTitle(p, c, t);
                return () => null;
            },
        }),
    );
    return { wrapper, p, c, t };
}

describe("useUploadTabTitle", () => {
    afterEach(() => {
        document.title = "";
    });

    test("shows progress and counts while uploading", () => {
        document.title = "MMT";

        setup(0, 1, 2);

        expect(document.title).toBe("↑ 0% · 1/2");
    });

    test("updates the title when progress changes", async () => {
        document.title = "MMT";

        const { p } = setup(0, 1, 2);
        p.value = 42;
        await flushPromises();

        expect(document.title).toBe("↑ 42% · 1/2");
    });

    test("restores the original title when nothing is uploading", async () => {
        document.title = "MMT";

        const { c } = setup(50, 1, 1);
        c.value = null;
        await flushPromises();

        expect(document.title).toBe("MMT");
    });

    test("restores the original title on unmount", () => {
        document.title = "MMT";

        const { wrapper } = setup(50, 1, 1);
        expect(document.title).not.toBe("MMT");

        wrapper.unmount();

        expect(document.title).toBe("MMT");
    });
});
