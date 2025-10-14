import getCookie from "./get_cookie";

test("getCookie gets cookie value", () => {
    const cookieStr = "name=Oeschger; SameSite=None; Secure";
    const actual = getCookie(cookieStr, "SameSite");
    const expected = "None";
    expect(actual).toEqual(expected);
});

test("getCookie returns null if cookie not available", () => {
    const cookieStr = "name=Oeschger; Secure";
    const actual = getCookie(cookieStr, "SameSite");
    const expected = null;
    expect(actual).toEqual(expected);
});

test("getCookie can handle empty strings", () => {
    const cookieStr = "";
    const actual = getCookie(cookieStr, "SameSite");
    const expected = null;
    expect(actual).toEqual(expected);
});
