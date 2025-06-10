import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";
import { describe, test } from "@odoo/hoot";
import { defineVoipCRMModels } from "@voip_crm/../tests/voip_crm_test_helpers";

describe.current.tags("desktop");
defineVoipCRMModels();

test("LeadButton is hidden when user doesn't have sales team groups", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Test Partner",
        phone: "+1-555-123-4567",
    });
    pyEnv["crm.lead"].create({
        name: "Test Opportunity",
        partner_id: partnerId,
        type: "opportunity",
    });
    onRpc("has_group", () => false);
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button span:contains('Contacts')");
    await click(".o-voip-TabEntry:contains('Test Partner')");
    await contains("button[title='Leads']", { count: 0 });
});

test("LeadButton is shown when user has sales team groups", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Test Partner",
        phone: "+1-555-123-4567",
    });
    pyEnv["crm.lead"].create({
        name: "Test Opportunity",
        partner_id: partnerId,
        type: "opportunity",
    });
    onRpc("has_group", (args) => {
        const group = args.args[1];
        return group === "sales_team.group_sale_salesman";
    });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button span:contains('Contacts')");
    await click(".o-voip-TabEntry:contains('Test Partner')");
    await contains("button[title='Leads']");
});

test("LeadButton is shown when user has sales manager group", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Test Partner",
        phone: "+1-555-123-4567",
    });
    pyEnv["crm.lead"].create({
        name: "Test Opportunity",
        partner_id: partnerId,
        type: "opportunity",
    });
    onRpc("has_group", (args) => {
        const group = args.args[1];
        return group === "sales_team.group_sale_manager";
    });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button span:contains('Contacts')");
    await click(".o-voip-TabEntry:contains('Test Partner')");
    await contains("button[title='Leads']");
});
