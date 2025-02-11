import { EsgHrGenderParityBox } from "@esg_hr/components/esg_dashboard/esg_hr_gender_parity_box/esg_hr_gender_parity_box";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(EsgHrGenderParityBox.prototype, {
    get overallPayGapPercentage() {
        if (this.props.data.overall_pay_gap === false) {
            return _t("N/A");
        }
        return _t("%(overall_pay_gap)s%", { overall_pay_gap: this.props.data.overall_pay_gap });
    },
});
