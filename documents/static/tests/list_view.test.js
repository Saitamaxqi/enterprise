import { browser } from "@web/core/browser/browser";
import {
    contains,
    defineModels,
    mountView,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import {
    DocumentsModels,
    getBasicPermissionPanelData,
    getDocumentsTestServerData,
    makeDocumentRecordData,
} from "./helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model";
import { embeddedActionsServerData } from "./helpers/test_server_data";
import { basicDocumentsListArch } from "./helpers/views/list";
import { getEnrichedSearchArch } from "./helpers/views/search";

describe.current.tags("desktop");

defineModels({
    ...webModels,
    ...mailModels,
    ...DocumentsModels,
});

/**
 * Shortcut for details panel selector
 * @param selector
 * @return {`.o_documents_details_panel ${string}`}
 */
const dp = (selector) => `.o_documents_details_panel ${selector}`;

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
        },
    });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    await contains(`.o_data_row:contains(${folder1Name}) .o_list_record_selector`).click();
    await contains("button:contains(Share)").click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["permission_panel_data", "Document url copied"]);
});

test("Right panel shows and updates focused or container record only", async function () {
    onRpc("/documents/touch/accessTokenFolder1", () => true);
    onRpc("/documents/touch/accessTokenFile1", () => true);
    onRpc("/documents/touch/accessTokenFile2", () => true);
    onRpc("/documents/touch/accessTokenFile3", () => true);

    const file2Id = 3;
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "File 1", { attachment_id: 1, folder_id: 1 }),
        makeDocumentRecordData(file2Id, "File 2", { attachment_id: 2, folder_id: 1 }),
        makeDocumentRecordData(4, "File 3", { attachment_id: 3, folder_id: 1 }),
    ]);
    serverData.models["ir.attachment"] = {
        records: [
            { id: 1, name: "One" },
            { id: 2, name: "Two" },
            { id: 3, name: "Three" },
        ],
    };
    const { name: folder1Name } = serverData.models["documents.document"].records[0];
    onRpc("web_save", ({ args }) => {
        if (args[0].length === 1 && args[0][0] === file2Id) {
            expect.step("edit_request_2");
        }
    });
    await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.model === "ir.model" && args.method === "display_name_for") {
                return args.args[0].map((model) => ({ model, display_name: model }));
            }
        },
    });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    // Open right panel
    await contains(".o_control_panel_navigation .fa-info-circle").click();
    await waitFor(".documents_chatter_disabled_overlay");
    // Focus without selection
    await contains(`.o_data_row td[name='name']:contains(${folder1Name})`).click();
    await animationFrame();
    expect(dp(".o_documents_details_panel_name input")).toHaveValue(folder1Name);
    await contains(`.o_list_renderer`).click(); // de-focus

    await waitFor(".documents_chatter_disabled_overlay"); // As we're in all/company
    // Enter folder
    await contains(`.o_data_row:contains(${folder1Name}) .fa-folder-o`).click();
    await animationFrame();
    expect(`.o_data_row .o_list_record_selector`).toHaveCount(3);
    expect(dp(".o_documents_details_panel_name input")).toHaveValue(folder1Name);

    // Focus without selection
    await contains(".o_data_row :contains('File 1')").click();
    expect(dp(".o_documents_details_panel_name input")).toHaveValue("File 1");
    // Unfocus
    await contains(`.o_list_renderer`).click();
    expect(dp(".o_documents_details_panel_name input")).toHaveValue(folder1Name);

    // select record focuses it
    await contains(".o_data_row:contains('File 1') .o_list_record_selector").click();
    expect(dp(".o_documents_details_panel_name input")).toHaveValue("File 1");
    // Focus without selection
    await contains(".o_data_row :contains('File 2')").click();
    expect(dp(".o_documents_details_panel_name input")).toHaveValue("File 2");
    // Editing unselected File 2 only
    await contains(dp(".o_documents_details_panel_name input")).edit("File 4");
    // Row is modified, not File 1
    await waitFor(".o_data_row :contains('File 4')");
    await waitFor(".o_data_row :contains('File 1')");

    expect.verifySteps(["edit_request_2"]);
});

test("Document actions are hidden when focused record is not selected", async function () {
    onRpc("/documents/touch/accessTokenFolder1", () => true);
    onRpc("/documents/touch/accessTokenFile1", () => true);
    onRpc("/documents/touch/accessTokenFile2", () => true);

    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "File 1", { attachment_id: 1, folder_id: 1 }),
        makeDocumentRecordData(3, "File 2", { attachment_id: 2, folder_id: 1 }),
    ]);
    serverData.models["ir.attachment"] = {
        records: [
            { id: 1, name: "One" },
            { id: 2, name: "Two" },
        ],
    };
    await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.model === "ir.model" && args.method === "display_name_for") {
                return args.args[0].map((model) => ({ model, display_name: model }));
            }
        },
    });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    // select record focuses it
    await contains(".o_data_row:contains('File 1') .o_list_record_selector").click();
    // Actions are visible as selection is focused
    await waitFor(".o_control_panel_actions:contains('Download')");
    // Focus without selection
    await contains(".o_data_row :contains('File 2')").click();
    await waitFor(".o_selection_container");
    // Actions are no longer visible as focused is not selected
    await waitFor(".o_control_panel_actions:not(:contains('Download'))");
    // Select it to show actions again
    await contains(".o_data_row:contains('File 2') .o_list_record_selector").click();
    await waitFor(".o_control_panel_actions:contains('Download')");
});

test("only show common available actions", async function () {
    await makeDocumentsMockEnv({ serverData: embeddedActionsServerData });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(`.o_data_row:contains('Request 1') .o_list_record_selector`).click();
    await waitFor(".o_control_panel_actions:contains('Action 1')");
    await contains(`.o_data_row:contains('Request 1') .o_list_record_selector`).click();

    await contains(`.o_data_row:contains('Request 2') .o_list_record_selector`).click();
    await waitForNone(".o_control_panel_actions:contains('Action 1')");
    await waitFor(".o_control_panel_actions:contains('Action 2 only')");
    await waitFor(".o_control_panel_actions:contains('Action 2 and 3')");

    await contains(`.o_data_row:contains('Request 3') .o_list_record_selector`).click();
    await waitForNone(".o_control_panel_actions:contains('Action 2 only')");
    await waitFor(".o_control_panel_actions:contains('Action 2 and 3')");
});

test("Required document name", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Testing file", { folder_id: 1 }),
        makeDocumentRecordData(3, "Testing folder", { folder_id: 1 }),
    ]);
    await makeDocumentsMockEnv({ serverData });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    const lr = (documentName, selector) => `.o_data_row:contains('${documentName}') ${selector}`;
    for (const documentName of ["Testing folder", "Testing file"]) {
        await contains(lr(documentName, ".o_list_record_selector")).click();
        await contains(lr(documentName, ".o_data_cell[name='name']")).click();
        await expect(lr(documentName, ".o_data_cell[name='name'] input")).toHaveCount(1);
        await expect(lr(documentName, ".o_data_cell[name='name'] input")).toHaveValue(documentName);
        // Set empty name
        await contains(lr(documentName, ".o_data_cell[name='name'] input")).edit("");
        await animationFrame();
        expect(".o_notification").toHaveCount(1);
        expect(".o_notification").toHaveText("Name cannot be empty.");
        await contains(".o_notification .o_notification_close").click();
        await expect(lr(documentName, ".o_data_cell[name='name'] input")).toHaveValue(documentName);
        // Remove selection and close record edition
        await contains(".o_list_renderer").click();
        await contains(".o_list_button_discard").click();
        await animationFrame();
    }
});
