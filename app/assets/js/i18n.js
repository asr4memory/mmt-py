import { createI18n } from "vue-i18n";

import de from "./locales/de";
import en from "./locales/en";

const locale = document.documentElement.lang;

export default createI18n({
    legacy: false,
    locale: locale,
    fallbackLocale: "en",
    messages: {
        de,
        en,
    },
});
