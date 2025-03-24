import { browser } from "@web/core/browser/browser";
import {
    contains,
    defineModels,
    onRpc,
    patchWithCleanup,
    webModels
} from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";

import { DocumentsModels, getBasicPermissionPanelData, getDocumentsTestServerData } from "./helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model";
import { basicDocumentsKanbanArch, mountDocumentsKanbanView } from "./helpers/views/kanban";

describe.current.tags("desktop");

defineModels({
    ...webModels,
    ...mailModels,
    ...DocumentsModels,
})

test("Open share with view user_permission", async function () {
    onRpc("/documents/touch/accessTokenFolder1", () => true);
    const serverData = getDocumentsTestServerData();
    const { id: folder1Id, name: folder1Name } = serverData.models["documents.document"].records[0];
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("Document url copied");
            expect(url).toBe("https://localhost:8069/odoo/documents/accessTokenFolder1");
        },
    });
    await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(folder1Id);
                expect.step("permission_panel_data");
                return getBasicPermissionPanelData({
                    access_url: "https://localhost:8069/odoo/documents/accessTokenFolder1",
                });
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    await mountDocumentsKanbanView();
    await contains(`.o_kanban_record:contains(${folder1Name}) .o_record_selector`).click({
        ctrlKey: true,
    });
    await contains("button:contains(Share)").click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["permission_panel_data", "Document url copied"]);
});


test("Colorless-tags are also visible on cards", async function () {
    const serverData = getDocumentsTestServerData([{
        id: 2,
        folder_id: 1,
        name: "Testing tags",
        tag_ids: [1, 2],
    }]);
    const { name: folder1Name} = serverData.models["documents.document"].records[0];
    const archWithTags =  basicDocumentsKanbanArch.replace(
        '<field name="name"/>',
        '<field name="name"/>\n' +
        '<field name="tag_ids" class="d-block text-wrap" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>'
    );
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView({ arch: archWithTags });
    await contains(`.o_kanban_record:contains(${folder1Name})`).click();
    await animationFrame();
    expect(".o_kanban_record:contains('Testing tags') div[name='tag_ids'] div .o_tag:nth-of-type(1)")
        .toHaveText('Colorless');
    expect(".o_kanban_record:contains('Testing tags') div[name='tag_ids'] div .o_tag:nth-of-type(2)")
        .toHaveText('Colorful');
});
