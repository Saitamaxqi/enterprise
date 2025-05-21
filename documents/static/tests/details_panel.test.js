import { mailModels } from "@mail/../tests/mail_test_helpers";
import { omit } from "@web/core/utils/objects";
import { contains, defineModels, serverState, webModels } from "@web/../tests/web_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import {
    DocumentsModels,
    getDocumentsTestServerData,
    makeDocumentRecordData,
} from "@documents/../tests/helpers/data";
import { makeDocumentsMockEnv } from "@documents/../tests/helpers/model";
import {
    basicDocumentsKanbanArch,
    mountDocumentsKanbanView,
} from "@documents/../tests/helpers/views/kanban";

describe.current.tags("desktop");

defineModels({
    ...webModels,
    ...mailModels,
    ...DocumentsModels,
});

const archWithTags = basicDocumentsKanbanArch.replace(
    '<field name="name"/>',
    /* xml */ `
        <field name="name"/>
        <field name="tag_ids" class="d-block text-wrap" widget="many2many_tags" options="{'color_field': 'color'}"/>
        <field name="alias_domain_id"/>
        <field name="alias_name"/>
        <field name="alias_tag_ids" class="d-block text-wrap" widget="many2many_tags" options="{'color_field': 'color'}"/>
        <field name="create_activity_type_id"/>
        <field name="mail_alias_domain_count"/>
    `
);

const mockRPCIrModelDisplayNameFor = async function (route, args) {
    if (args.model === "ir.model" && args.method === "display_name_for") {
        return args.args[0];
    }
};

/**
 * Shortcut for details panel selector
 * @param selector
 * @return {string} `selector` prefixed with `".o_documents_details_panel "`.
 */
const dp = (selector) => `.o_documents_details_panel ${selector}`;

const binaryTestedValues = { tag_ids: [1, 2], owner_id: serverState.userId };
const folderTestedValues = {
    alias_id: 1,
    alias_domain_id: 1,
    alias_name: "alias",
    alias_tag_ids: [1, 2],
    mail_alias_domain_count: 2,
    owner_id: serverState.userId,
    type: "folder",
    create_activity_type_id: 1,
};

test("Details panel rendering for editors", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Testing tags", { folder_id: 1, ...binaryTestedValues }),
        makeDocumentRecordData(3, "Testing container", { folder_id: 1, ...folderTestedValues }),
    ]);
    await makeDocumentsMockEnv({ serverData, mockRPC: mockRPCIrModelDisplayNameFor });
    await mountDocumentsKanbanView({ arch: archWithTags });
    await contains(".o_kanban_record:contains('Testing tags')").click();
    await contains(".o_control_panel_navigation .fa-info-circle").click();
    await animationFrame();
    expect(dp(".o_documents_details_panel_name input")).toHaveCount(1);
    expect(dp(".o_documents_details_panel_name input")).toHaveValue("Testing tags");
    expect(dp(".o_field_tags input")).toHaveCount(1);
    await contains(dp(".o_field_tags span:contains('Colorless') a")).click();
    await contains(dp(".o_field_tags span:contains('Colorful') a")).click();
    expect(dp(".o_field_tags input[placeholder='Add tags...']")).toHaveCount(1);
    expect(dp("input[placeholder='No owner']")).toHaveValue("Mitchell Admin");

    await contains(".o_kanban_record:contains('Testing container')").click();
    expect(dp(".o_documents_details_panel_name input")).toHaveCount(1);
    expect(dp(".o_documents_details_panel_name input")).toHaveValue("Testing container");
    expect(dp("input[placeholder='No activity']")).toHaveValue("Email");
    expect(dp("input[placeholder='Activity assigned to']")).toHaveCount(1);

    await contains(dp(".o_field_tags span:contains('Colorless') a")).click();
    await contains(dp(".o_field_tags span:contains('Colorful') a")).click();
    await waitFor(dp(".o_field_tags input[placeholder='Add an alias tag...']"));
});

test("Details panel rendering for viewers - m2o/m2m values", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Testing tags", {
            folder_id: 1,
            ...binaryTestedValues,
            user_permission: "view",
        }),
        makeDocumentRecordData(3, "Testing container", {
            folder_id: 1,
            ...folderTestedValues,
            user_permission: "view",
        }),
    ]);
    await makeDocumentsMockEnv({ serverData, mockRPC: mockRPCIrModelDisplayNameFor });
    await mountDocumentsKanbanView({ arch: archWithTags });
    await contains(".o_kanban_record:contains('Testing tags')").click();
    await contains(".o_control_panel_navigation .fa-info-circle").click();
    await animationFrame();

    await waitFor(dp(".o_documents_details_panel_name span:contains('Testing Tags')"));
    expect(dp(".o_documents_details_panel_name input")).toHaveCount(0);
    expect(dp(".o_field_tags span:contains('Colorless')")).toHaveCount(1);
    expect(dp(".o_field_tags span:contains('Colorful')")).toHaveCount(1);
    expect(dp("span:contains('Mitchell Admin')")).toHaveCount(1);

    await contains(".o_kanban_record:contains('Testing container')").click();
    await waitFor(dp(".o_documents_details_panel_name span:contains('Testing Container')"));
    expect(dp(".o_field_tags input")).toHaveCount(0);
    expect(dp(".o_field_tags span:contains('Colorless')")).toHaveCount(1);
    expect(dp(".o_field_tags span:contains('Colorful')")).toHaveCount(1);
    expect(dp("div:contains('alias@odoo.com')")).toHaveCount(3); // nested wrappers
    expect(dp("span:contains('Email')")).toHaveCount(1); // activity type
    expect(dp("span:contains('No activity assignee')")).toHaveCount(1); // activity type
});

test("Details panel rendering for viewers - m2o/m2m pseudo-placeholders", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Testing tags", { folder_id: 1, user_permission: "view" }),
        makeDocumentRecordData(3, "Testing container", {
            folder_id: 1,
            ...omit(folderTestedValues, "alias_tag_ids"),
            user_permission: "view",
        }),
    ]);
    await makeDocumentsMockEnv({ serverData, mockRPC: mockRPCIrModelDisplayNameFor });
    await mountDocumentsKanbanView({ arch: archWithTags });
    await contains(".o_kanban_record:contains('Testing tags')").click();
    await contains(".o_control_panel_navigation .fa-info-circle").click();
    await animationFrame();

    await waitFor(dp(".o_documents_details_panel_name span:contains('Testing Tags')"));
    expect(dp(".o_field_tags span.o_documents_details_panel_placeholder")).toHaveText("No tags");
    await waitFor(dp("span.o_documents_details_panel_placeholder:contains('No owner')"));

    await contains(".o_kanban_record:contains('Testing container')").click();
    await waitFor(dp(".o_documents_details_panel_name span:contains('Testing Container')"));
    await waitFor(dp("div:contains('alias@odoo.com')"));
    await waitFor(dp("span:contains('No activity')"));
    expect(dp(".o_field_tags span.o_documents_details_panel_placeholder")).toHaveText(
        "No alias tags"
    );
});

test("Details panel root folder placeholders", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "In COMPANY"),
        makeDocumentRecordData(3, "In MY DRIVE", { owner_id: serverState.userId }),
        makeDocumentRecordData(4, "In SHARED WITH ME", { owner_id: serverState.odoobotId }),
        makeDocumentRecordData(5, "In COMPANY (readonly)", { user_permission: "view" }),
    ]);
    await makeDocumentsMockEnv({ serverData, mockRPC: mockRPCIrModelDisplayNameFor });
    await mountDocumentsKanbanView({ arch: archWithTags });
    await contains(".o_control_panel_navigation .fa-info-circle").click();
    // Edit mode
    for (const [documentName, rootPlaceholder] of [
        ["In COMPANY", "Company"],
        ["In MY DRIVE", "My Drive"],
        ["In SHARED WITH ME", "Shared with me"],
    ]) {
        await contains(`.o_kanban_record:contains('${documentName}')`).click();
        await animationFrame();
        expect(dp(".o_documents_details_panel_name input")).toHaveCount(1);
        expect(dp(".o_documents_details_panel_name input")).toHaveValue(documentName);
        expect(dp(".fa-folder + .o_field_many2one input")).toHaveAttribute(
            "placeholder",
            rootPlaceholder,
            { message: "Document should have correct root folder placeholder (editors)." }
        );
    }
    // Readonly mode
    await contains(".o_kanban_record:contains('In COMPANY (readonly)')").click();
    await animationFrame();
    expect(dp(".o_documents_details_panel_name span")).toHaveCount(1);
    expect(dp(".o_documents_details_panel_name span")).toHaveText("In COMPANY (readonly)");
    expect(dp(".fa-folder + .o_field_many2one .o_documents_details_panel_placeholder")).toHaveText(
        "Company",
        { message: "Document should have correct root folder placeholder (viewers)." }
    );
});
