import { defineDocumentSpreadsheetModels } from "@documents_spreadsheet/../tests/helpers/data";
import { createSpreadsheetFromPivotView } from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import { getHighlightsFromStore } from "@documents_spreadsheet/../tests/helpers/store_helpers";
import { describe, expect, getFixture, test, beforeEach } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { getBasicPivotArch } from "@spreadsheet/../tests/helpers/data";
import {
    getZoneOfInsertedDataSource,
    insertPivotInSpreadsheet,
} from "@spreadsheet/../tests/helpers/pivot";
import * as dsHelpers from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

let target;

beforeEach(() => {
    target = getFixture();
});

test("Update the pivot domain from the side panel", async function () {
    onRpc("/web/domain/validate", () => true);
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    await contains(".o_edit_domain").click();
    await dsHelpers.addNewRule();
    await contains(".modal-footer .btn-primary").click();
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([], {
        message: "update is deferred",
    });
    await contains(".pivot-defer-update .o-button-link").click();
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([["id", "=", 1]]);
    expect(dsHelpers.getConditionText()).toBe("Id is equal 1");
});

test("Opening the sidepanel of a pivot while the panel of another pivot is open updates the side panel", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    const arch = /* xml */ `
                    <pivot string="Product">
                        <field name="name" type="col"/>
                        <field name="active" type="row"/>
                        <field name="__count" type="measure"/>
                    </pivot>`;
    const pivotId2 = "PIVOT#2";
    await insertPivotInSpreadsheet(model, "PIVOT#2", {
        arch,
        resModel: "product",
        id: pivotId2,
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    expect(".o-section .o_model_name").toHaveText("Partner (partner)");

    env.openSidePanel("PivotSidePanel", { pivotId: pivotId2 });
    await animationFrame();
    expect(".o-section .o_model_name").toHaveText("Product (product)");
});

test("Deleting the pivot open the side panel with all pivots", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    await insertPivotInSpreadsheet(model, "pivot2", { arch: getBasicPivotArch() });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    expect(".o-sidePanelTitle").toHaveText("Pivot #1");

    model.dispatch("REMOVE_PIVOT", { pivotId });
    await animationFrame();
    expect(".o-sidePanel").toHaveCount(0);
});

test("Undo a pivot insertion open the side panel with all pivots", async function () {
    const { model, env } = await createSpreadsheetFromPivotView();
    await insertPivotInSpreadsheet(model, "pivot2", { arch: getBasicPivotArch() });
    env.openSidePanel("PivotSidePanel", { pivotId: "pivot2" });
    await animationFrame();
    expect(".o-sidePanelTitle").toHaveText("Pivot #2");

    /**
     * This is a bit bad because we need three undo to remove the pivot
     * - AUTORESIZE
     * - INSERT_PIVOT
     * - ADD_PIVOT
     */
    model.dispatch("REQUEST_UNDO");
    model.dispatch("REQUEST_UNDO");
    model.dispatch("REQUEST_UNDO");
    await animationFrame();
    expect(".o-sidePanel").toHaveCount(0);
});

test("Pivot cells are highlighted when their side panel is open", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    const sheetId = model.getters.getActiveSheetId();
    const zone = getZoneOfInsertedDataSource(model, "pivot", pivotId);
    expect(getHighlightsFromStore(env)).toEqual([
        { color: "#37A850", sheetId, zone, noFill: true },
    ]);
    await contains(".o-sidePanelClose").click();
    expect(getHighlightsFromStore(env)).toEqual([]);
});

test("Pivot side panel becomes non-interactive and grayed out in read-only mode", async function () {
    const { model, env } = await createSpreadsheetFromPivotView();

    const pivotId = model.getters.getPivotIds()[0];
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    const sidePanel = target.querySelector(".o-sidePanelBody > div");
    expect(sidePanel).not.toHaveClass("pe-none");
    expect(sidePanel).not.toHaveClass("opacity-50");

    model.updateMode("readonly");
    await animationFrame();

    expect(sidePanel).toHaveClass("pe-none");
    expect(sidePanel).toHaveClass("opacity-50");
    expect(sidePanel).toHaveAttribute("inert", "1");
});
