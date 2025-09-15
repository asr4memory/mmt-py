export default function getCookie(cookieStr, name) {
    console.assert(typeof cookieStr === 'string');

    const re = new RegExp(`(?:^|;\\s?)${name}=(\\w+)(?:;|$)`);
    const match = cookieStr.match(re);

    if (!match) {
        return null;
    }
    const result = decodeURIComponent(match[1]);

    return result;
}
