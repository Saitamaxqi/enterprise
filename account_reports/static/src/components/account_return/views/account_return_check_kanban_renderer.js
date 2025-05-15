import { useService } from "@web/core/utils/hooks";
import { isNull } from "@web/views/utils";
import { AccountReturnCheckKanbanRecord } from "@account_reports/components/account_return/views/account_return_check_kanban_record";

import { Component, useEffect} from "@odoo/owl";
export class AccountReturnCheckKanbanRenderer extends Component {
    static template="account_reports.account_return_check_kanban_renderer";

    static props = [
        "archInfo",
        "Compiler",
        "list",
        "deleteRecord",
        "openRecord",
        "readonly?",
        "forceGlobalClick?",
        "noContentHelp?",
        "scrollTop?",
        "canQuickCreate?",
        "quickCreateState?",
        "progressBarState?",
        "addLabel?",
        "onAdd?",
    ];

    static components = {
        KanbanRecord: AccountReturnCheckKanbanRecord,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        useEffect(() => {this.runCurrentReturnChecks()}, () => [])
    }

    async runCurrentReturnChecks() {
        const records = this.props.list.records;
        if (records.length > 0) {
            const account_return = records[0].data.return_id;
            await this.orm.call(
                'account.return',
                'refresh_checks',
                [account_return.id]
            );
            await this.props.list.model.load();
        }
    }

    get groups() {
        const { list } = this.props;
        if (list.isGrouped) {
            const groups = [...list.groups]
                .map((group, i) => ({
                    ...group,
                    key: isNull(group.value) ? `group_key_${i}` : String(group.value),
                }));
            return groups;
        }
        return false;
    }

    async openRecord(record, params) {
        const recordId = record.resId;
        if (record.resModel === "account.return.check") {
            const result = await this.orm.call(
                record.resModel,
                "action_review",
                [recordId]
            );

            if (result) {
                this.action.doAction(result);
            }
        }
    }
}
