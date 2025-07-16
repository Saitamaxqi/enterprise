import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { selectionField, SelectionField } from "@web/views/fields/selection/selection_field";

export class MpsPeriodSelectionField extends SelectionField {
    get options() {
        const mrp_mps_dates = this.props.record.evalContext.context["manufacturingPeriods"] || [];
        return Object.entries(mrp_mps_dates).map((date) => date);
    }
}

export const mpsPeriodSelectionField = {
    ...selectionField,
    component: MpsPeriodSelectionField,
    displayName: _t("MPS Period Selection"),
    supportedTypes: ["selection"],
};

registry.category("fields").add("mps_period_selection", mpsPeriodSelectionField);
