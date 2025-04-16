import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
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
test("Keypad input is focused when opening the keypad.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    await contains(".o-voip-Dialer input:focus");
});

test.tags("focus required");
test("Keypad input content is persisted when closing then re-opening the keypad.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "513");
    await contains("button span:contains('Recent')");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    await contains(".o-voip-Dialer input", { value: "513" });
});

test.tags("focus required");
test("Clicking on the “Backspace button” deletes the last character of the number input.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "123");
    await click("button[title='Backspace']");
    await contains(".o-voip-Dialer input", { value: "12" });
});

test.tags("focus required");
test("Cursor is taken into account when clicking Backspace.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "01123456");
    const input = document.querySelector(".o-voip-Dialer input");
    input.setSelectionRange(3, 3);
    await click("button[title='Backspace']");
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains(".o-voip-Dialer input", { value: "0123456" });
});

test.tags("focus required");
test("Cursor range selection is taken into account when clicking Backspace.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "011123456");
    const input = document.querySelector(".o-voip-Dialer input");
    input.setSelectionRange(2, 4);
    await click("button[title='Backspace']");
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains(".o-voip-Dialer input", { value: "0123456" });
});

test.tags("focus required");
test("When cursor is at the beginning of the input, clicking Backspace does nothing.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "0123456");
    const input = document.querySelector(".o-voip-Dialer input");
    input.setSelectionRange(0, 0);
    await click("button[title='Backspace']");
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(0);
    await contains(".o-voip-Dialer input", { value: "0123456" });
});

test.tags("focus required");
test("Clicking on a key appends it to the number input.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "123");
    await click("button i.fa-hashtag");
    await tick();
    await contains(".o-voip-Dialer input", { value: "123#" });
});

test.tags("focus required");
test("Number input is focused after clicking on a key.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    await click("button span", { text: "2" });
    await tick();
    await contains(".o-voip-Dialer input:focus");
});

test.tags("focus required");
test("Cursor is taken into account when clicking on a key.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "023456");
    const input = document.querySelector(".o-voip-Dialer input");
    input.setSelectionRange(1, 1);
    await click("button span", { text: "1" });
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains(".o-voip-Dialer input", { value: "0123456" });
});

test.tags("focus required");
test("Cursor range selection is taken into account when clicking on a key.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "0223456");
    const input = document.querySelector(".o-voip-Dialer input");
    input.setSelectionRange(1, 2);
    await click("button span", { text: "1" });
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains(".o-voip-Dialer input", { value: "0123456" });
});

test.tags("focus required");
test("Pressing Enter in the input makes a call to the dialed number.", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "9223372036854775807");
    await triggerHotkey("Enter");
    expect(pyEnv["voip.call"].search_count([["phone_number", "=", "9223372036854775807"]])).toBe(1);
});

test.tags("focus required");
test("Pressing Enter in the input doesn't make a call if the trimmed input is empty string.", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button span:contains('Keypad')");
    await click("button span:contains('Keypad')");
    // ensure initial focusing is done before inserting text to avoid focus reset
    await contains(".o-voip-Dialer input:focus");
    await insertText(".o-voip-Dialer input:focus", "\t \n\r\v");
    await triggerHotkey("Enter");
    expect(pyEnv["voip.call"].search_count([])).toBe(0);
});
