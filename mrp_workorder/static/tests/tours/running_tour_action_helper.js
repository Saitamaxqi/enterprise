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
