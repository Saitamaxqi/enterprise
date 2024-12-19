import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

patch(AccountReportFilters.prototype, {
    get filterExtraOptionsData() {
        return {
            ...super.filterExtraOptionsData,
            'vehicle_split': {
                'name': _t("Vehicle Split"),
            },
        };
    },
});
