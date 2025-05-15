import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    contains,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test.tags("focus required");
test("input is focused when opening the keypad", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await contains(".o-voip-Keypad-searchBar input:focus");
});

test.tags("focus required");
test("input is persisted when closing then re-opening the keypad", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "513");
    await contains("button:contains(Recent)");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await contains(".o-voip-Keypad-searchBar input:value(513)");
});

test.tags("focus required");
test("“backspace button” deletes the last character of the not focused input", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "123");
    const input = document.querySelector(".o-voip-Keypad-searchBar input:focus");
    input.blur();
    await click(".o-voip-Keypad-searchBar button[title=Backspace]");
    await contains(".o-voip-Keypad-searchBar input:value(12)");
});

test.tags("focus required");
test("“backspace button” deletes characters from cursor position", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "01123456");
    const input = document.querySelector(".o-voip-Keypad-searchBar input");
    input.setSelectionRange(3, 3);
    await click(".o-voip-Keypad-searchBar button[title=Backspace]");
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains(".o-voip-Keypad-searchBar input:value(0123456)");
});

test.tags("focus required");
test("“backspace button” deletes selected characters", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "011123456");
    const input = document.querySelector(".o-voip-Keypad-searchBar input");
    input.setSelectionRange(2, 4);
    await click(".o-voip-Keypad-searchBar button[title=Backspace]");
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains(".o-voip-Keypad-searchBar input:value(0123456)");
});

test.tags("focus required");
test("“backspace button” does nothing when the cursor is at the beginning of the input", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "0123456");
    const input = document.querySelector(".o-voip-Keypad-searchBar input");
    input.setSelectionRange(0, 0);
    await click(".o-voip-Keypad-searchBar button[title=Backspace]");
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(0);
    await contains(".o-voip-Keypad-searchBar input:value(0123456)");
});

test.tags("focus required");
test("clicking on a key appends it to the end of the not focused input", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "123");
    const input = document.querySelector(".o-voip-Keypad-searchBar input:focus");
    input.blur();
    await click(".o-voip-Keypad-digit:contains(0)");
    await contains(".o-voip-Keypad-searchBar input:value(1230)");
});

test.tags("focus required");
test("input is focused back after clicking on a key", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await click(".o-voip-Keypad-digit:contains(2)");
    await contains(".o-voip-Keypad-searchBar input:focus");
});

test.tags("focus required");
test("clicking on a key inserts the key behind the cursor", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "023456");
    const input = document.querySelector(".o-voip-Keypad-searchBar input");
    input.setSelectionRange(1, 1);
    await click(".o-voip-Keypad-digit:contains(1)");
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains(".o-voip-Keypad-searchBar input:value(0123456)");
});

test.tags("focus required");
test("cursor selection is replaced by the clicked key", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "0223456");
    const input = document.querySelector(".o-voip-Keypad-searchBar input");
    input.setSelectionRange(1, 2);
    await click(".o-voip-Keypad-digit:contains(1)");
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains(".o-voip-Keypad-searchBar input:value(0123456)");
});

test.tags("focus required");
test("pressing Enter in the input calls the dialed number", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "9223372036854775807");
    await triggerHotkey("Enter");
    expect(pyEnv["voip.call"].search_count([["phone_number", "=", "9223372036854775807"]])).toBe(1);
});

test.tags("focus required");
test("pressing Enter in the input doesn't make a call if the trimmed input is empty", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input:focus", "\t \n\r\v");
    await triggerHotkey("Enter");
    expect(pyEnv["voip.call"].search_count([])).toBe(0);
});

test("input font size classes update dynamically when input changes", async () => {
    await start();
    await click(".o_menu_systray [title='Open Softphone']");
    await click(".o-voip-Softphone nav button:contains(Keypad)");
    await insertText(".o-voip-Keypad-searchBar input", "12345");
    await contains(".o-voip-Keypad-input.fs-1:not(.fs-2):not(.fs-3)");
    await insertText(".o-voip-Keypad-searchBar input", "123456789012");
    await contains(".o-voip-Keypad-input.fs-2:not(.fs-1):not(.fs-3)");
    await insertText(".o-voip-Keypad-searchBar input", "123456789012345678");
    await contains(".o-voip-Keypad-input.fs-3:not(.fs-1):not(.fs-2)");
});
