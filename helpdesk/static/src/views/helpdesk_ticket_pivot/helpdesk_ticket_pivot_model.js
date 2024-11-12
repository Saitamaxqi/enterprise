import { _t } from "@web/core/l10n/translation";
import { PivotModel } from "@web/views/pivot/pivot_model";

export class HelpdeskTicketPivotModel extends PivotModel {
    /**
     * @override
     */
    _getEmptyGroupLabel(fieldName) {
        if (fieldName === "sla_deadline") {
            return _t("Deadline reached");
        } else if (fieldName === "user_id") {
            return _t("Unassigned");
        } else {
            return super._getEmptyGroupLabel(fieldName);
        }
    }
}
