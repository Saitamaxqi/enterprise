import { ListRenderer } from "@web/views/list/list_renderer";
import { PayslipActionHelper } from "../../components/payslip_action_helper/payslip_action_helper";
import { useService } from "@web/core/utils/hooks";

export class PayslipListRenderer extends ListRenderer {
    static template = "hr_payroll.PayslipListRenderer";
    static components = {
        ...ListRenderer.components,
        PayslipActionHelper,
    };
    static props = [
        ...ListRenderer.props,
        "onGenerate",
        "payRunInfo",
    ];

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    /**
     * @override
     */
    getActiveColumns(list) {
        let activeColumns = super.getActiveColumns(list);
        let hideColumnsForPayruns = activeColumns.filter((col) => Boolean(col.options?.hide_in_payrun) === true);
        if (hideColumnsForPayruns && this.props.payRunInfo.id && !this.props.payRunInfo.isOffCycle)
            return activeColumns.filter((col) => !hideColumnsForPayruns.includes(col));
        else if (this.props.payRunInfo.isOffCycle){
            return activeColumns.map(col => {
                if (col.options?.hide_in_payrun) {
                    return {
                        ...col,
                        options: {
                            ...col.options,
                            no_open: 1,
                        }
                    };
                }
                return col;
            });
        }
        return activeColumns;
    }
}
