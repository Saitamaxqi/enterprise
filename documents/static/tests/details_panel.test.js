import { mailModels } from "@mail/../tests/mail_test_helpers";
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
    '<field name="name"/>\n' +
        '<field name="tag_ids" class="d-block text-wrap" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>'
);

const mockRPCIrModelDisplayNameFor = async function (route, args) {
    if (args.model === "ir.model" && args.method === "display_name_for") {
        return args.args[0];
    }
};

/**
 * Shortcut for details panel selector
 * @param selector
 * @return {`.o_documents_details_panel ${string}`}
 */
const dp = (selector) => `.o_documents_details_panel ${selector}`;

const testedValues = { tag_ids: [1, 2], owner_id: serverState.userId };

test("Details panel rendering for editors", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Testing tags", { folder_id: 1, ...testedValues }),
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
});

test("Details panel rendering for viewers - m2o/m2m values", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Testing tags", {
            folder_id: 1,
            ...testedValues,
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
    await waitFor(dp("span:contains('Mitchell Admin')"));
});

test("Details panel rendering for viewers - m2o/m2m pseudo-placeholders", async function () {
    const serverData = getDocumentsTestServerData([
        makeDocumentRecordData(2, "Testing tags", { folder_id: 1, user_permission: "view" }),
    ]);
    await makeDocumentsMockEnv({ serverData, mockRPC: mockRPCIrModelDisplayNameFor });
    await mountDocumentsKanbanView({ arch: archWithTags });
    await contains(".o_kanban_record:contains('Testing tags')").click();
    await contains(".o_control_panel_navigation .fa-info-circle").click();
    await animationFrame();

    await waitFor(dp(".o_documents_details_panel_name span:contains('Testing Tags')"));
    expect(dp(".o_field_tags span.o_documents_details_panel_placeholder")).toHaveText("No tags");
    await waitFor(dp("span.o_documents_details_panel_placeholder:contains('No owner')"));
});
