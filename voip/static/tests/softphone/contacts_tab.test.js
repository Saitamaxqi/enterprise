import {
    click,
    contains,
    insertText,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { expect, describe, test } from "@odoo/hoot";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Partners with a phone number are displayed in Contacts tab", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create([
        { name: "Michel Landline", phone: "+1-307-555-0120" },
        { name: "Patrice Nomo" },
    ]);
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button span:contains('Contacts')");
    await contains(".o-voip-TabEntry", { count: 1 });
    await contains(".o-voip-TabEntry span", { text: "Michel Landline" });
    await contains(".o-voip-TabEntry span", { text: "Patrice Nomo", count: 0 });
});

test("Typing in the search bar fetches and displays the matching contacts", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button span:contains('Contacts')");
    pyEnv["res.partner"].create([
        { name: "Morshu RTX", phone: "+61-855-527-77" },
        { name: "Gargamel", phone: "+61-855-583-671" },
    ]);
    await insertText("input[id='o-voip-Tab-searchInput']", "Morshu");
    await contains(".o-voip-TabEntry span", { text: "Morshu RTX" });
    await contains(".o-voip-TabEntry span", { text: "Gargamel", count: 0 });
});

test("Scrolling to bottom loads more contacts", async () => {
    const pyEnv = await startServer();
    let rpcCount = 0;
    onRpc("res.partner", "get_contacts", () => { ++rpcCount; });
    await start();
    for (let i = 0; i < 10; ++i) {
        pyEnv["res.partner"].create({ name: `Contact ${i}`, phone: `09225 982 ext. ${i}` });
    }
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button span:contains('Contacts')");
    await contains(".o-voip-TabEntry", { count: 10 });
    expect(rpcCount).toBe(1);
    for (let i = 0; i < 10; ++i) {
        pyEnv["res.partner"].create({ name: `Contact ${i + 10}`, phone: `040 2805 ext. ${i}` });
    }
    await contains(".o-voip-TabEntry", { count: 10 });
    await scroll(".o-voip-AddressBook div.overflow-auto", "bottom");
    await contains(".o-voip-TabEntry", { count: 20 });
    expect(rpcCount).toBe(2);
});
