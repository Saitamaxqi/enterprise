import { assert, fail } from "@stock/../tests/tours/tour_helper";
import { animationFrame } from "@odoo/hoot-dom";
import { patch } from "@web/core/utils/patch";
import { TourHelpers } from "@web_tour/tour_service/tour_helpers";

patch(TourHelpers.prototype, {
    async scan(barcode) {
        odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger("barcode_scanned", { barcode });
        await animationFrame();
    },
});

// Helper's methods.
export function getRecord(options = {}) {
    const recordEls = this.getRecords(...arguments);
    if (recordEls.length > 1) {
        fail("Multiple records found for selector.");
    }
    return recordEls[0];
}

export function getRecords(options = {}) {
    const selector = ".o_mrp_display_record";
    const recordsEl = document.querySelectorAll(selector);
    if (recordsEl.length === 0) {
        fail("No record found for selector.");
    }
    return recordsEl;
}

// Asserts.
export function assertProductionWorkorderCount(productionCard, expectedCount) {
    const workorderLinesEl = productionCard.querySelectorAll(".o_mrp_operation_name");
    assert(workorderLinesEl.length, expectedCount, "Not the right amount of WO.");
}

export function assertWorkOrderValues(values) {
    const { name, steps } = values;
    const recordEl = getRecords()[values.index];
    const headerEl = recordEl.querySelector("&>.card-header");
    const bodyEl = recordEl.querySelector("&>ul");
    const linesEl = bodyEl.querySelectorAll("&>li");
    assert(name, headerEl.querySelector(".o_record_name").innerText, "Wrong record's name");
    assert(
        headerEl.querySelector(".o_finished_product").innerText,
        values.product,
        `Wrong finished product for record "${name}"`
    );
    assert(
        headerEl.querySelector(".o_quantity").innerText,
        values.quantity,
        `Wrong quantity to produce for record "${name}"`
    );
    assert(linesEl.length, steps.length, `Record "${name}" should have ${steps.length} line(s)`);

    // Check every record's line label and value.
    for (let i = 0; i < steps.length; i++) {
        const { label, value } = steps[i];
        const lineEl = linesEl[i];
        const lineLabel = lineEl.querySelector(".o_line_label").innerText;
        const lineValue = lineEl.querySelector(".o_line_value")?.innerText;
        assert(lineLabel, label, `Wrong label for "${name}" line nbre ${i}`);
        if (value) {
            assert(lineValue, value, `"${name}" line "${lineLabel}" has wrong value`);
        } else if (lineValue) {
            fail(`"${name} line "${lineLabel}" should have no value: got "${lineValue}" instead.`);
        }
    }
}
