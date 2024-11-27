/** @ts-check */

import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { useState } from "@odoo/owl";
import { BooleanMultiSelector } from "@spreadsheet/global_filters/components/boolean_multi_selector/boolean_multi_selector";

export class BooleanFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.BooleanFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        FilterEditorFieldMatching,
        BooleanMultiSelector,
    };

    setup() {
        super.setup();

        this.type = "boolean";
        this.booleanState = useState({
            defaultValue: [],
        });
        this.ALLOWED_FIELD_TYPES = ["boolean"];
    }

    /**
     * @override
     */
    shouldDisplayFieldMatching() {
        return this.fieldMatchings.length;
    }

    /**
     * @override
     */
    get filterValues() {
        const values = super.filterValues;
        const { defaultValue } = this.booleanState;
        return {
            ...values,
            defaultValue,
        };
    }

    /**
     * @override
     */
    loadSpecificFilterValues(globalFilter) {
        const { defaultValue } = globalFilter;
        this.booleanState.defaultValue = defaultValue;
    }

    updateDefaultValues(values) {
        this.booleanState.defaultValue = values;
    }
}
