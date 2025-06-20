/** @ts-check */

import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { TextFilterValue } from "@spreadsheet/global_filters/components/filter_text_value/filter_text_value";

import { components } from "@odoo/o-spreadsheet";
import { ModelSelector } from "@web/core/model_selector/model_selector";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { SelectionFilterValue } from "@spreadsheet/global_filters/components/selection_filter_value/selection_filter_value";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const { SelectionInput } = components;

/**
 * This is the side panel to define/edit a global filter of type "selection".
 */
export class SelectionFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.SelectionFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        FilterEditorFieldMatching,
        ModelSelector,
        ModelFieldSelector,
        TextFilterValue,
        SelectionInput,
        SelectionFilterValue,
    };

    setup() {
        super.setup();

        this.orm = useService("orm");
        onWillStart(async () => {
            if (!this.store.filter.resModel) {
                return;
            }
            const result = await this.orm
                .cached()
                .call("ir.model", "display_name_for", [[this.store.filter.resModel]]);
            const label = result[0]?.display_name;
            this.store.updateSelectionModelLabel(label);
        });
    }

    get type() {
        return "selection";
    }

    filterSelectionsFields(field) {
        if (!field.searchable || field.type !== "selection") {
            return false;
        }
        return true;
    }

    /**
     * We only want to show the selection field if it is the one
     * selected in the filter (same resModel and selectionField), or
     * if it is a relation field.
     */
    filterModelFieldSelectorField(field, path, resModel) {
        if (
            this.store.filter.resModel === resModel &&
            field.name === this.store.filter.selectionField
        ) {
            return true;
        }
        return !!field.relation;
    }
}
