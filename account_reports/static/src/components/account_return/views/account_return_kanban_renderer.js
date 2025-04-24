import { useService } from "@web/core/utils/hooks";
import { isNull } from "@web/views/utils";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

import { Component, useEffect} from "@odoo/owl";
const { DateTime } = luxon;

export class AccountReturnKanbanRenderer extends Component {
    static template="account_reports.account_return_kanban_renderer";

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
        KanbanRecord,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        useEffect(() => {this.runAllReturnChecks()}, () => []);
    }

    async runAllReturnChecks() {
        const additionalDomain = [
            ['date_from', '<=', DateTime.now().endOf("month").toISODate()]
        ]

        const returnIds = await this.orm.call(
            'account.return',
            'get_next_returns_ids',
            [
                null,
                additionalDomain,
                true, //allow_multiple_by_types
            ],
        );

        await this.orm.call(
            'account.return',
            'refresh_checks',
            [returnIds]
        );

        // reload records
        await this.props.list.model.load();
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
}
