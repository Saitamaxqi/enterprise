import { Chatter } from "@mail/chatter/web_portal/chatter";
import { useService, useBus } from "@web/core/utils/hooks";
import { isNull } from "@web/views/utils";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AccountReturnKanbanRecord } from "@account_reports/components/account_return/views/account_return_kanban_record";
import { useEffect } from "@odoo/owl";
const { DateTime } = luxon;
import { browser } from "@web/core/browser/browser";


export class AccountReturnKanbanRenderer extends KanbanRenderer {
    static template="account_reports.account_return_kanban_renderer";

    static props = [
        ...KanbanRenderer.props,
        "chatterState",
    ]

    static components = {
        ...KanbanRenderer.components,
        AccountReturnKanbanRecord,
        Chatter,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.ui = useService("ui");
        useEffect(() => {this.runAllReturnChecks()}, () => []);
        useBus(this.env.bus, "return_reload_model", (ev) => {
            const recordIds = ev.detail.resIds;
            let recordToReload = this.records.filter((record) => recordIds.includes(record.resId));
            for (let record of recordToReload) {
                record.model.load();
            }
        });
        useEffect(() => {
            if (!this.visibleReturnIds.has(this.props.chatterState.returnId)) {
                this.props.chatterState.returnId = null;
                this.props.chatterState.visible = false;
                browser.sessionStorage.removeItem("account_return.chatterReturnId");
            }
        }, () => [this.props.list]);
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
            'try_auto_review',
            [returnIds],
        );

        await this.orm.call(
            'account.return',
            'refresh_checks',
            [returnIds]
        );

        // reload records
        await this.props.list.model.load();
    }

    get records() {
        const { list } = this.props;
        if (list.isGrouped) {
            return list.groups.flatMap((group) => group.list.records);
        }
        else {
            return list.records;
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

    get visibleReturnIds() {
        const { list } = this.props;
        if (!list.isGrouped) {
            return new Set(
                list.records.map(record => record.resId)
            );
        }
        return new Set(
            list.groups.flatMap(group =>
                group.list.records.map(record => record.resId)
            )
        );
    }

}
