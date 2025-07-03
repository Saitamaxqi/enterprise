import { ValuationChart } from "@equity/components/valuation_chart/valuation_chart";
import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class ValuationChartAction extends Component {
    static template = "equity.ValuationChartAction";
    static props = { ...standardActionServiceProps };
    static components = { ValuationChart };

    setup() {
        super.setup();
        this.orm = useService('orm');
        onWillStart(async () => {
            this.chartData = await this.orm.call("equity.valuation", "get_all_partners_valuation_chart_data", []);
        });
    }
}

registry.category("actions").add("equity.ValuationChart", ValuationChartAction);
