import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatDate, parseDate } from "@web/core/l10n/dates";
import { Component, useState, onWillStart } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
const { DateTime } = luxon;

export class AccountReturnDashboardList extends Component {
    static template = "account_reports.account_return_dashboard_list";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.accountReturns = useState([]);
        onWillStart(this.fetchNextReturns);
    }

    formatReturn(accountReturn) {
        return {
            id: accountReturn.id,
            name: accountReturn.name,
            deadline: formatDate(parseDate(accountReturn.date_deadline)),
            isOverdue: parseDate(accountReturn.date_deadline) < DateTime.now(),
        }
    }

    async fetchNextReturns() {
        const returns = await this.orm.call(
            'account.return',
            'get_next_return_for_dashboard',
            [this.props.record.resId], //allow_multiple_by_types
        );

        this.accountReturns = returns.map(this.formatReturn);
    }
}


export const accountReturnDashboardList = {
    component: AccountReturnDashboardList,
}

registry.category("view_widgets").add("account_return_dashboard_list", accountReturnDashboardList);
