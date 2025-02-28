/** @ts-check */

import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { Select } from "../../../components/select/select";

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").OdooField} OdooField
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").FixedPeriods} FixedPeriods
 */

/**
 * This is the side panel to define/edit a global filter of type "date".
 */
export class DateFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.DateFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        Select,
    };

    get type() {
        return "date";
    }

    onRangeTypeSelected(rangeType) {
        this.store.update({ rangeType, defaultValue: undefined });
    }

    /**
     * @param {number} id
     * @param {string|undefined} chain
     * @param {OdooField|undefined} field
     */
    onSelectedField(id, chain, field) {
        this.store.updateFieldMatching(id, chain, field);
        this.store.updateFieldMatchingOffset(id, 0);
    }

    /**
     * @param {number} id
     * @param {number} offset
     */
    onOffsetSelected(id, offset) {
        this.store.updateFieldMatchingOffset(id, offset);
    }
}
