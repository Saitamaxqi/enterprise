/** @ts-check */

import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { TextFilterValue } from "@spreadsheet/global_filters/components/filter_text_value/filter_text_value";

import { components } from "@odoo/o-spreadsheet";
import { useState } from "@odoo/owl";

const { SelectionInput } = components;

/**
 * This is the side panel to define/edit a global filter of type "text".
 */
export class TextFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.TextFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        FilterEditorFieldMatching,
        TextFilterValue,
        SelectionInput,
    };

    setup() {
        super.setup();
        this.state = useState({
            rangeRestriction: !!this.store.filter.rangeOfAllowedValues,
        });
    }

    get type() {
        return "text";
    }

    toggleRangeRestriction(isChecked) {
        if (!isChecked) {
            this.onRangeChanged([]);
            this.store.update({ rangeOfAllowedValues: undefined });
        }
        this.state.rangeRestriction = isChecked;
    }

    onRangeChanged(ranges) {
        this.range = ranges[0];
    }

    onRangeConfirmed() {
        const rangeOfAllowedValues =
            this.state.rangeRestriction &&
            this.range &&
            this.env.model.getters.getRangeFromSheetXC(
                this.env.model.getters.getActiveSheetId(),
                this.range
            );
        this.range = undefined;
        this.store.update({ rangeOfAllowedValues });
    }
}
