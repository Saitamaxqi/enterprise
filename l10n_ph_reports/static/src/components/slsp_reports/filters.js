import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

patch(AccountReportFilters.prototype, {
    get filterExtraOptionsData() {
        return {
            ...super.filterExtraOptionsData,
            'include_no_tin': {
                'name': _t("Including Partners Without TIN"),
            },
            'include_imports': {
                'name': _t("Including Importations"),
            },
        };
    },

    get selectedExtraOptions() {
        let selectedExtraOptionsName = super.selectedExtraOptions;

        if ("include_no_tin" in this.controller.options) {
            const includeNoTINName = _t("With Partners without TIN");

            selectedExtraOptionsName = selectedExtraOptionsName
                ? `${selectedExtraOptionsName}, ${includeNoTINName}`
                : includeNoTINName;
        }

        if ("include_imports" in this.controller.options) {
            const includeImportsName = _t("With Importations");
            selectedExtraOptionsName = selectedExtraOptionsName
                ? `${selectedExtraOptionsName}, ${includeImportsName}`
                : includeImportsName;
        }

        return selectedExtraOptionsName;
    },

});
