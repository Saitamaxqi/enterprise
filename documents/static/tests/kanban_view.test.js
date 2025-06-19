import { browser } from "@web/core/browser/browser";
import {
    contains,
    defineModels,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { keyDown, queryAll, queryAllTexts, queryFirst, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import {
    DocumentsModels,
    getBasicPermissionPanelData,
    getDocumentsTestServerData,
    makeDocumentRecordData,
    mimetypeExamplesBase64,
} from "./helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model";
import { embeddedActionsServerData } from "./helpers/test_server_data";
import { basicDocumentsKanbanArch, mountDocumentsKanbanView } from "./helpers/views/kanban";

import { DocumentsPermissionPanel } from "@documents/components/documents_permission_panel/documents_permission_panel";
import { documentsClientThumbnailService } from "@documents/views/helper/documents_client_thumbnail_service";
import { Deferred } from "@web/core/utils/concurrency";

describe.current.tags("desktop");

defineModels({
    ...webModels,
    ...mailModels,
    ...DocumentsModels,
});

test("Open share with edit user_permission", async function () {
    onRpc("/documents/touch/accessTokenFolder1", () => true);
    const serverData = getDocumentsTestServerData();
    const { id: folder1Id, name: folder1Name } = serverData.models["documents.document"].records[0];
    patchWithCleanup(DocumentsPermissionPanel.prototype, {
        async onInviteMembersSelected(selectedPartners) {
            expect(selectedPartners.length).toEqual(1);
            expect(selectedPartners[0].display_name).toEqual("Hermit");
            expect.step("Select invite member");
        },
    });
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
                    access_internal: "edit",
                    user_permission: "edit",
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

    // Check that selecting a partner calls onInviteMembersSelected with the partner (to open the access invite wizard)
    await contains("input.o-autocomplete--input").click();
    await contains(".dropdown-item", { text: "Hermit" }).click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["permission_panel_data", "Select invite member", "Document url copied"]);
});

test("Colorless-tags are also visible on cards", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Testing tags", { folder_id: 1, tag_ids: [1, 2] }),
    ]);
    const { name: folder1Name } = serverData.models["documents.document"].records[0];
    const archWithTags = basicDocumentsKanbanArch.replace(
        '<field name="name"/>',
        '<field name="name"/>\n' +
            '<field name="tag_ids" class="d-block text-wrap" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>'
    );
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView({ arch: archWithTags });
    await contains(`.o_kanban_record:contains(${folder1Name})`).click();
    await animationFrame();
    expect(
        ".o_kanban_record:contains('Testing tags') div[name='tag_ids'] div .o_tag:nth-of-type(1)"
    ).toHaveText("Colorless");
    expect(
        ".o_kanban_record:contains('Testing tags') div[name='tag_ids'] div .o_tag:nth-of-type(2)"
    ).toHaveText("Colorful");
});

test("Download button availability", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Request", { folder_id: 1 }),
        makeDocumentRecordData(3, "Binary", { attachment_id: 1, folder_id: 1 }),
    ]);
    serverData.models["ir.attachment"] = {
        records: [{ id: 1, name: "binary" }],
    };
    const { name: folder1Name } = serverData.models["documents.document"].records[0];
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();
    await contains(`.o_kanban_record:contains(${folder1Name})`).click({ ctrlKey: true });
    // Folder should be downloadable
    await waitFor(".o_control_panel_actions:contains('Download')");

    await contains(`.o_kanban_record:contains(${folder1Name})`).click({ ctrlKey: true });
    // Request should not be downloadable
    await contains(".o_kanban_record:contains('Request')").click();
    await waitForNone(".o_control_panel_actions:contains('Download')");

    // Binary should be downloadable
    await contains(".o_kanban_record:contains('Binary')").click();
    await waitFor(".o_control_panel_actions:contains('Download')");
    // Multiple documents can be downloaded
    await contains(`.o_kanban_record:contains(${folder1Name})`).click({ ctrlKey: true });
    await waitFor(".o_control_panel_actions:contains('Download')");

    // Button should remain even if some records are not downloadable
    await contains(".o_kanban_record:contains('Request')").click({ ctrlKey: true });
    await waitFor(".o_control_panel_actions:contains('Download')");
});

test("Drag and Drop - Search panel expand folders", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Sub Folder", { folder_id: 1, type: "folder" }),
        makeDocumentRecordData(3, "Test Folder", { type: "folder" }),
    ]);
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    const searchPanelSelector = ".o_search_panel_category_value .o_search_panel_label_title";
    // Check that when we drag hover the Company folder it opens up to display its children
    expect(queryAllTexts(searchPanelSelector)).toEqual([
        "All",
        "Company",
        "My Drive",
        "Shared with me",
        "Recent",
        "Trash",
    ]);
    const { cancel, moveTo } = await contains(".o_kanban_record[data-value-id='3']").drag();
    await moveTo(
        ".o_search_panel_category_value[data-value-id='COMPANY'] div.o_search_panel_label"
    );
    expect(queryAllTexts(searchPanelSelector)).toEqual([
        "All",
        "Company",
        "Folder 1",
        "Test Folder",
        "My Drive",
        "Shared with me",
        "Recent",
        "Trash",
    ]);
    await moveTo(".o_search_panel_category_value[data-value-id='1'] div.o_search_panel_label");
    expect(queryAllTexts(searchPanelSelector)).toEqual([
        "All",
        "Company",
        "Folder 1",
        "Sub Folder",
        "Test Folder",
        "My Drive",
        "Shared with me",
        "Recent",
        "Trash",
    ]);
    await cancel();
});

test("Drag and Drop - A folder into itself or its children", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Sub Folder", { folder_id: 1, type: "folder" }),
        makeDocumentRecordData(3, "Folder 2", { type: "folder" }),
    ]);
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    const folder1 = queryFirst(".o_kanban_record[data-value-id='1']");
    const folder2 = queryFirst(".o_kanban_record[data-value-id='2']");
    const folder3 = queryFirst(".o_kanban_record[data-value-id='3']");

    const { cancel, moveTo } = await contains(folder1).drag();
    await moveTo(folder2);
    expect(folder2).toHaveClass("o_drag_invalid");
    expect(".o_documents_dnd_text").toHaveText(
        "You cannot move a folder into itself or a children."
    );
    await moveTo(folder3);
    expect(folder3).toHaveClass("o_drag_hover");
    expect(".o_documents_dnd_text").toHaveText("Folder 1");
    await moveTo(folder1);
    expect(folder1).toHaveClass("o_drag_invalid");
    expect(".o_documents_dnd_text").toHaveText(
        "You cannot move a folder into itself or a children."
    );
    await cancel();
});

test("Drag and Drop - After selecting multiple documents", async function () {
    const serverData = getDocumentsTestServerData(
        [1, 2, 3].map((idx) =>
            makeDocumentRecordData(idx + 1, `Test Document ${idx}`, { folder_id: 1 })
        )
    );
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    const document2 = queryFirst(".o_kanban_record[data-value-id='2']");
    const document4 = queryFirst(".o_kanban_record[data-value-id='4']");

    await contains(document2).click({ ctrlKey: true });
    await contains(document4).click({ ctrlKey: true });

    let { cancel } = await contains(document2).drag();
    expect(document2).toHaveStyle({ opacity: "0.3" });
    expect(document4).toHaveStyle({ opacity: "0.3" });
    expect(".o_documents_dnd_text").toHaveText("Test Document 1");
    await cancel();

    ({ cancel } = await contains(document4).drag());
    expect(document2).toHaveStyle({ opacity: "0.3" });
    expect(document4).toHaveStyle({ opacity: "0.3" });
    expect(".o_documents_dnd_text").toHaveText("Test Document 3");
    await cancel();
});

test("Drag and Drop - Check permission when dropping documents", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Test Document 1"),
        makeDocumentRecordData(3, "Test Document 2", { user_permission: "view" }),
    ]);
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    let { drop, moveTo } = await contains(".o_kanban_record[data-value-id='2']").drag();
    await moveTo(".o_kanban_record[data-value-id='1']");
    await drop();
    await waitFor(".o_notification");
    expect(queryAll(".o_notification_content").at(-1)).toHaveText("The document has been moved.");

    ({ drop, moveTo } = await contains(".o_kanban_record[data-value-id='3']").drag());
    await moveTo(".o_kanban_record[data-value-id='1']");
    await drop();
    await waitFor(".o_notification");
    expect(queryAll(".o_notification_content").at(-1)).toHaveText(
        "At least one document could not be moved due to access rights."
    );
});

test("Drag and Drop - Drop multiple documents at once", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Test Document 1"),
        makeDocumentRecordData(3, "Test Document 2", { user_permission: "view" }),
    ]);
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    await contains(".o_kanban_record[data-value-id='2']").click({ ctrlKey: true });
    await contains(".o_kanban_record[data-value-id='3']").click({ ctrlKey: true });

    const { drop, moveTo } = await contains(".o_kanban_record[data-value-id='2']").drag();
    await moveTo(".o_kanban_record[data-value-id='1']");
    await drop();
    await waitFor(".o_notification");
    expect(queryAllTexts(".o_notification_content")).toEqual([
        "At least one document could not be moved due to access rights.",
        "The document has been moved.",
    ]);
});

test("Drag and Drop - Drop document while holding CTRL", async function () {
    const serverData = getDocumentsTestServerData([makeDocumentRecordData(2, "Test Document")]);
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    const { drop, moveTo } = await contains(".o_kanban_record[data-value-id='2']").drag();
    expect(".o_documents_dnd_modifier").not.toBeVisible();
    await keyDown("Control");
    expect(".o_documents_dnd_modifier").toBeVisible();
    await moveTo(
        ".o_search_panel_category_value[data-value-id='COMPANY'] div.o_search_panel_label"
    );
    await moveTo(".o_search_panel_category_value[data-value-id='1'] div.o_search_panel_label");
    expect(".o_documents_dnd_modifier").toBeVisible(); // check after moveTo to be sure it's still visible
    await drop();
    await waitFor(".o_notification");
    expect(queryAll(".o_notification_content").at(-1)).toHaveText("A shortcut has been created.");
});

test("Drag and Drop - Dropping in 'My Drive' should create a shortcut", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Test Document", { folder_id: 1 }),
    ]);
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    const { drop, moveTo } = await contains(".o_kanban_record[data-value-id='2']").drag();
    await moveTo(".o_search_panel_category_value[data-value-id='MY'] div.o_search_panel_label");
    expect(".o_documents_dnd_modifier").toBeVisible();
    await drop();
    await waitFor(".o_notification");
    expect(queryAll(".o_notification_content").at(-1)).toHaveText("A shortcut has been created.");
});

test("Lock action availability and check", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Binary", { folder_id: 1 }),
    ]);
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    const folder = queryFirst(".o_kanban_record[data-value-id='1']");

    // Folder should not be lockable
    await contains(folder).click({ ctrlKey: true });
    await contains(".o_cp_action_menus button").click();
    await waitForNone(".o-dropdown--menu .o-dropdown-item:contains('Lock')");

    // Binary should be lockable
    await contains(".o_kanban_record:contains('Binary')").click();
    await contains(".o_cp_action_menus button").click();
    await contains(".o-dropdown--menu .o-dropdown-item:contains('Lock')").click();
    await waitFor(".o_kanban_record i.fa-lock");

    // Unlock the binary record
    await contains(".o_cp_action_menus button").click();
    await contains(".o-dropdown--menu .o-dropdown-item:contains('Unlock')").click();
    expect(".modal-body").toHaveText(
        "This document is locked by OdooBot.\nAre you sure you want to unlock it?"
    );
    await contains(".modal .modal-footer .btn-primary").click();
    await waitForNone(".o_kanban_record i.fa-lock");

    // Multiple documents cannot be locked
    await contains(folder).click({ ctrlKey: true });
    await contains(".o_cp_action_menus button").click();
    await waitForNone(".o-dropdown--menu .o-dropdown-item:contains('Lock')");
});

test("only show common available actions", async function () {
    await makeDocumentsMockEnv({ serverData: embeddedActionsServerData });
    await mountDocumentsKanbanView();

    await contains(`.o_kanban_record:contains('Request 1')`).click();
    await waitFor(".o_control_panel_actions:contains('Action 1')");

    await contains(`.o_kanban_record:contains('Request 2')`).click();
    await waitForNone(".o_control_panel_actions:contains('Action 1')");
    await waitFor(".o_control_panel_actions:contains('Action 2 only')");
    await waitFor(".o_control_panel_actions:contains('Action 2 and 3')");

    await contains(`.o_kanban_record:contains('Request 3')`).click({ ctrlKey: true });
    await waitForNone(".o_control_panel_actions:contains('Action 2 only')");
    await waitFor(".o_control_panel_actions:contains('Action 2 and 3')");
});

test("Thumbnail: webp thumbnail generation", async function () {
    onRpc("/documents/document/3/update_thumbnail", async (args) => {
        const { params } = await args.json();
        expect.step("thumbnail generated");
        expect(params.thumbnail.startsWith("/9j/")).toEqual(true);
        return true;
    });
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(3, "Test Document", {
            thumbnail_status: "client_generated",
            attachment_id: 2,
            folder_id: 1,
            mimetype: "image/webp",
        }),
    ]);
    serverData.models["ir.attachment"] = {
        records: [{ id: 2, name: "binary" }],
    };
    await makeDocumentsMockEnv({ serverData });
    patchWithCleanup(documentsClientThumbnailService, {
        _getLoadedImage() {
            const img = new Image();
            const imagePromise = new Deferred();
            img.onload = () => imagePromise.resolve(img);
            img.src = "data:image/webp;base64," + mimetypeExamplesBase64.WEBP;
            return imagePromise;
        },
    });
    await mountDocumentsKanbanView();
    expect.verifySteps(["thumbnail generated"]);
});
