import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { stores } from "@odoo/o-spreadsheet";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { addGlobalFilterWithoutReload, updatePivot } from "@spreadsheet/../tests/helpers/commands";
import { getBasicServerData, defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { assertDateDomainEqual } from "@spreadsheet/../tests/helpers/date_domain";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import { contains, serverState, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { user } from "@web/core/user";
import { Component, onMounted, onWillUnmount, xml } from "@odoo/owl";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { GlobalFiltersSidePanel } from "@spreadsheet_edition/bundle/global_filters/global_filters_side_panel";

const { useStoreProvider, ModelStore } = stores;

defineSpreadsheetModels();
describe.current.tags("desktop");

/**
 * @typedef {import("@spreadsheet").FixedPeriodDateGlobalFilter} FixedPeriodDateGlobalFilter
 */

let target;

const FILTER_CREATION_SELECTORS = {
    text: ".o_global_filter_new_text",
    date: ".o_global_filter_new_time",
    relation: ".o_global_filter_new_relation",
    boolean: ".o_global_filter_new_boolean",
};

class Parent extends Component {
    static template = xml`<GlobalFiltersSidePanel/>`;
    static components = { GlobalFiltersSidePanel };
    static props = {
        model: Object,
    };

    setup() {
        const stores = useStoreProvider();
        stores.inject(ModelStore, this.props.model);

        onMounted(() => {
            this.props.model.on("update", this, () => this.render(true));
            stores.on("store-updated", this, this.render.bind(this, true));
        });
        onWillUnmount(() => {
            this.props.model.off("update", this);
            stores.off("store-updated", this);
        });
    }
}

async function openSidePanel(model, env) {
    env.openSidePanel = env.openSidePanel ?? (() => {});
    await mountWithCleanup(Parent, { env, props: { model } });
}

/**
 * @param {"text" | "date" | "relation"} type
 */
async function clickCreateFilter(type) {
    await contains(FILTER_CREATION_SELECTORS[type]).click();
}

beforeEach(() => {
    target = getFixture();
});

test("Simple display", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    await openSidePanel(model, env);
    expect(".o_spreadsheet_global_filters_side_panel").toHaveCount(1);

    const buttons = target.querySelectorAll(".o_spreadsheet_global_filters_side_panel .o-button");
    expect(buttons.length).toBe(4);
    expect(buttons[0]).toHaveClass("o_global_filter_new_time");
    expect(buttons[1]).toHaveClass("o_global_filter_new_relation");
    expect(buttons[2]).toHaveClass("o_global_filter_new_text");
    expect(buttons[3]).toHaveClass("o_global_filter_new_boolean");
});

test("Display with an existing 'Date' global filter", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    const label = "This year";
    addGlobalFilterWithoutReload(model, {
        id: "42",
        type: "date",
        label,
    });
    env.openSidePanel = (_, props) => expect.step(props.id);
    await openSidePanel(model, env);
    const sections = target.querySelectorAll(".o_spreadsheet_global_filters_side_panel .o-section");
    expect(sections.length).toBe(2);
    const labelElement = sections[0].querySelector(".o_side_panel_filter_label");
    expect(labelElement).toHaveText(label);

    expect.verifySteps([]);
    await contains(sections[0].querySelector(".o_side_panel_filter_icon.fa-cog")).click();
    expect.verifySteps(["42"]);
});

test("Create a new boolean global filter", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    env.openSidePanel = (name) => expect.step(name);
    await openSidePanel(model, env);
    await clickCreateFilter("boolean");
    expect.verifySteps(["BOOLEAN_FILTERS_SIDE_PANEL"]);
});

test("Create a new text global filter", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    env.openSidePanel = (name) => expect.step(name);
    await openSidePanel(model, env);
    await clickCreateFilter("text");
    expect.verifySteps(["TEXT_FILTER_SIDE_PANEL"]);
});

test("Create a new date global filter", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    env.openSidePanel = (name) => expect.step(name);
    await openSidePanel(model, env);
    await clickCreateFilter("date");
    expect.verifySteps(["DATE_FILTER_SIDE_PANEL"]);
});

test("Create a new relation global filter", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    env.openSidePanel = (name) => expect.step(name);
    await openSidePanel(model, env);
    await clickCreateFilter("relation");
    expect.verifySteps(["RELATION_FILTER_SIDE_PANEL"]);
});

test("Cannot create a relation filter without data source", async function () {
    const { model, env } = await createModelWithDataSource();
    await openSidePanel(model, env);
    expect(".o_global_filter_new_time").toHaveCount(1);
    expect(".o_global_filter_new_relation").toHaveCount(0);
    expect(".o_global_filter_new_text").toHaveCount(1);
});

test("Can create a relation filter with at least a data source", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    await openSidePanel(model, env);
    expect(".o_global_filter_new_time").toHaveCount(1);
    expect(".o_global_filter_new_relation").toHaveCount(1);
    expect(".o_global_filter_new_text").toHaveCount(1);
});

test("Display name for 'Relation' global filter values can be updated correctly", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    const label = "MyFoo";
    addGlobalFilterWithoutReload(model, {
        id: "42",
        type: "relation",
        modelName: "product",
        label,
    });
    await openSidePanel(model, env, "42");
    await contains(".o-autocomplete--input.o_input").click();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);
    const item1 = target.querySelector(".o-autocomplete--dropdown-item");
    await contains(item1).click();
    expect(model.getters.getFilterDisplayValue(label)[0][0].value).toBe(item1.innerText);
});

test("Edit the value of a relative date filter", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model, pivotId, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(
        model,
        {
            id: "42",
            type: "date",
            label: "label",
            defaultValue: "last_7_days",
        },
        {
            pivot: { [pivotId]: { chain: "date", type: "date" } },
        }
    );
    await openSidePanel(model, env);
    await contains(".o-filter-value input").click();
    await contains(".o-dropdown-item[data-id='last_12_months']").click();

    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        type: "relative",
        period: "last_12_months",
    });
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);
    assertDateDomainEqual("date", "2021-07-01", "2022-06-30", pivotDomain);
});

test("Edit the value to empty of a relative date filter", async () => {
    mockDate("2022-07-14 00:00:00");
    const { model, pivotId, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(
        model,
        {
            id: "42",
            type: "date",
            label: "label",
            defaultValue: "last_7_days",
        },
        {
            pivot: { [pivotId]: { chain: "date", type: "date" } },
        }
    );
    await openSidePanel(model, env);
    await contains(".o-filter-value input").click();
    await contains(".o-dropdown-item:not([data-id])").click();

    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
    const pivotDomain = model.getters.getPivotComputedDomain(pivotId);

    expect(pivotDomain).toEqual([]);
});

test("Readonly user can update text filter values", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: ["abc"],
    });
    model.updateMode("readonly");
    await openSidePanel(model, env);

    const pivots = target.querySelectorAll(".pivot_filter_section");
    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(0);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(pivots[0].querySelector(".o_side_panel_filter_label")).toHaveText("Text Filter");

    const input = pivots[0].querySelector(".pivot_filter_input input");
    expect(".pivot_filter_input .o_tag").toHaveText("abc");

    await contains(input).edit("something");
    await contains(input).press("Enter");

    expect(model.getters.getGlobalFilterValue("42")).toEqual(["abc", "something"]);
});

test("Readonly user can update date filter values", async function () {
    mockDate("2022-11-10 00:00:00");
    const { model, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(model, {
        id: "43",
        type: "date",
        label: "Date Filter",
        defaultValue: "this_quarter",
    });
    model.updateMode("readonly");

    await openSidePanel(model, env);

    const pivots = target.querySelectorAll(".pivot_filter_section");
    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(0);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(pivots[0].querySelector(".o_side_panel_filter_label")).toHaveText("Date Filter");

    await contains(".o-filter-value input").click();
    await contains(".o-dropdown-item[data-id='quarter'] .btn-previous").click();

    expect(model.getters.getGlobalFilterValue("43")).toEqual({
        type: "quarter",
        year: 2022,
        quarter: 3,
    });
});

test("Readonly user can update relation filter values", async function () {
    const tagSelector = ".o_multi_record_selector .badge";
    const { model, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(model, {
        id: "42",
        type: "relation",
        label: "Relation Filter",
        modelName: "product",
        defaultValue: [41],
    });
    expect(model.getters.getGlobalFilters().length).toBe(1);
    model.updateMode("readonly");

    await openSidePanel(model, env);

    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(0);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(".pivot_filter_section .o_side_panel_filter_label").toHaveText("Relation Filter");
    expect(tagSelector).toHaveCount(1);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual(["xpad"]);

    await contains(".pivot_filter_section .pivot_filter_input input.o-autocomplete--input").click();
    await contains("ul.ui-autocomplete li:first-child").click();

    expect(tagSelector).toHaveCount(2);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual(["xpad", "xphone"]);
    expect(model.getters.getGlobalFilterValue("42")).toEqual([41, 37]);
});

test("Can clear a text filter values", async function () {
    const { model, pivotId, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(
        model,
        {
            id: "42",
            type: "text",
            label: "Text Filter",
        },
        {
            pivot: { [pivotId]: { chain: "name", type: "char" } },
        }
    );
    await openSidePanel(model, env);

    const pivots = target.querySelectorAll(".pivot_filter_section");
    const input = pivots[0].querySelector(".pivot_filter_input input");
    expect(input).toHaveValue("");
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(1);
    // no default value
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);

    await contains(input).edit("something");
    await contains(input).press("Enter");
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([["name", "ilike", "something"]]);

    await contains("i.o_side_panel_filter_icon.fa-times").click();
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);
    expect(input).toHaveValue("");
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can clear a date filter values", async function () {
    mockDate("2022-11-10 00:00:00");
    const { model, pivotId, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(
        model,
        {
            id: "43",
            type: "date",
            label: "Date Filter",
        },
        {
            pivot: { [pivotId]: { chain: "date", type: "date" } },
        }
    );
    await openSidePanel(model, env);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(1);
    // no default value
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);

    await contains(".o-filter-value input").click();
    await contains(".o-dropdown-item[data-id='last_7_days']").click();

    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([
        "&",
        ["date", ">=", "2022-11-04"],
        ["date", "<=", "2022-11-10"],
    ]);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);

    await contains("i.o_side_panel_filter_icon.fa-times").click();
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can clear a relation filter values", async function () {
    const tagSelector = ".o_multi_record_selector .badge";
    const { model, pivotId, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
            modelName: "product",
        },
        {
            pivot: { [pivotId]: { chain: "product_id", type: "many2one" } },
        }
    );
    expect(model.getters.getGlobalFilters().length).toBe(1);

    await openSidePanel(model, env);

    expect(".pivot_filter_section").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-cog").toHaveCount(1);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);
    expect(".pivot_filter_section .o_side_panel_filter_label").toHaveText("Relation Filter");
    expect(tagSelector).toHaveCount(0);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual([]);

    await contains(".pivot_filter_section .pivot_filter_input input.o-autocomplete--input").click();
    await contains("ul.ui-autocomplete li:first-child").click();

    expect(tagSelector).toHaveCount(1);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual(["xphone"]);
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(1);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([["product_id", "in", [37]]]);

    // clear filter
    await contains("i.o_side_panel_filter_icon.fa-times").click();
    expect("i.o_side_panel_filter_icon.fa-times").toHaveCount(0);
    expect(tagSelector).toHaveCount(0);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual([]);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can clear automatic default user with the global clear button", async function () {
    const uid = user.userId;
    const tagSelector = ".o_multi_record_selector .o_tag";
    const serverData = getBasicServerData();
    serverData.models["res.users"].records = [
        { id: uid, active: true, partner_id: serverState.partnerId },
    ];
    const { model, pivotId, env } = await createSpreadsheetWithPivot({ serverData });
    addGlobalFilterWithoutReload(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
            modelName: "res.users",
            defaultValue: "current_user",
        },
        {
            pivot: { [pivotId]: { chain: "user_ids", type: "many2many" } },
        }
    );

    await openSidePanel(model, env);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([["user_ids", "in", [uid]]]);
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual(["Mitchell Admin"]);
    // clear filter
    await contains("i.o_side_panel_filter_icon.fa-times").click();
    expect(queryAllTexts(`.pivot_filter_section ${tagSelector}`)).toEqual([]);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can clear automatic default user from the record selector tag", async function () {
    const uid = user.userId;
    const { model, pivotId, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
            modelName: "res.users",
            defaultValue: "current_user",
        },
        {
            pivot: { [pivotId]: { chain: "user_ids", type: "many2many" } },
        }
    );

    await openSidePanel(model, env);
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([["user_ids", "in", [uid]]]);
    // clear filter
    await contains(".o_multi_record_selector .o_delete", { visible: false }).click();
    expect(model.getters.getPivotComputedDomain(pivotId)).toEqual([]);
});

test("Can reorder filters with drag & drop", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    addGlobalFilterWithoutReload(model, THIS_YEAR_GLOBAL_FILTER);
    const id_1 = THIS_YEAR_GLOBAL_FILTER.id;
    const id_2 = "filter_id_2";
    addGlobalFilterWithoutReload(model, {
        ...THIS_YEAR_GLOBAL_FILTER,
        label: "second filter",
        id: id_2,
    });
    let filters = model.getters.getGlobalFilters();
    expect(filters[0].id).toBe(id_1);
    expect(filters[1].id).toBe(id_2);
    await openSidePanel(model, env);
    const handle = target.querySelector(".o-filter-drag-handle");
    const sections = target.querySelectorAll(".pivot_filter_section");

    await contains(handle, { visible: false }).dragAndDrop(sections[1], { position: "bottom" });

    filters = model.getters.getGlobalFilters();
    expect(filters[0].id).toBe(id_2);
    expect(filters[1].id).toBe(id_1);
});

describe("integration", () => {
    test("suggestions", async () => {
        onRpc("get_search_view_archs", ({ args }) => {
            expect(args).toEqual([["action_partner"]]);
            return {
                partner: [
                    /*xml*/ `
                    <search>
                        <field name="product_id" string="My product filter"/>
                    </search>
                    `,
                ],
            };
        });
        const { model } = await createSpreadsheetWithPivot();
        await mountSpreadsheet(model);
        const [pivotId] = model.getters.getPivotIds();
        updatePivot(model, pivotId, { actionXmlId: "action_partner" });
        await contains(".o_topbar_filter_icon").click();
        await contains(".global-filter-suggestions .btn").click();
        await waitFor(".o_spreadsheet_filter_editor_side_panel");
        await contains(".o_global_filter_save").click();
        const globalFilter = model.getters.getGlobalFilters()[0];
        const filterId = globalFilter.id;
        expect(model.getters.getPivotFieldMatching(pivotId, filterId)).toEqual({
            chain: "product_id",
            type: "many2one",
        });
        expect(globalFilter).toEqual({
            defaultValue: undefined,
            id: filterId,
            domainOfAllowedValues: [],
            label: "My product filter",
            modelName: "product",
            type: "relation",
        });
        await waitFor(".o_spreadsheet_global_filters_side_panel");
        expect(".global-filter-suggestions").toHaveCount(0);
    });
});
