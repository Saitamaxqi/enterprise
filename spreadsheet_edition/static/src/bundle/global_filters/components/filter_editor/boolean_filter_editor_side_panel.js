/** @ts-check */

import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { BooleanMultiSelector } from "@spreadsheet/global_filters/components/boolean_multi_selector/boolean_multi_selector";

export class BooleanFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.BooleanFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        FilterEditorFieldMatching,
        BooleanMultiSelector,
    };

    get type() {
        return "boolean";
    }
}
