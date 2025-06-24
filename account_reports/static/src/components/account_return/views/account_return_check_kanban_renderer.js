import {
    AccountReturnCheckKanbanRecord
} from "@account_reports/components/account_return/views/account_return_check_kanban_record";
import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {onWillStart, useEffect} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {parseXML} from "@web/core/utils/xml";
import {extractFieldsFromArchInfo, getFieldsSpec} from "@web/model/relational_model/utils";
import {RelationalModel} from "@web/model/relational_model/relational_model";
import {isNull} from "@web/views/utils";
import {AccountReturnKanbanRecord} from "./account_return_kanban_record";
import {Chatter} from "@mail/chatter/web_portal/chatter";


const viewRegistry = registry.category("views");


export class AccountReturnCheckKanbanRenderer extends KanbanRenderer {
    static template = "account_reports.account_return_check_kanban_renderer";

    static components = {
        ...KanbanRenderer.components,
        AccountReturnCheckKanbanRecord,
        AccountReturnKanbanRecord,
        Chatter,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.viewService = useService("view");
        useEffect(() => {this.runCurrentReturnChecks()}, () => [])

        onWillStart(async () => {
            const { fields, relatedModels, views } = await this.viewService.loadViews({
                resModel: "account.return",
                context: this.props.context,
                views: [[false, "kanban"]],
            });
            const { ArchParser } = viewRegistry.get("kanban");
            const xmlDoc = parseXML(views["kanban"].arch);
            this.returnArchInfo = new ArchParser().parse(xmlDoc, relatedModels, 'account.return');

            const extractedFields = extractFieldsFromArchInfo(this.returnArchInfo, fields);

            const accountReturnId = this.props.list.context?.account_return_id;
            if (!accountReturnId) return;
            this.specification = getFieldsSpec(extractedFields.activeFields, extractedFields.fields, this.props.list.context)

            const returnData = await this.orm.webRead(
                'account.return',
                    [accountReturnId],
                { specification: this.specification }
            );

            const modelParams = this.getModelParams(extractedFields.activeFields, extractedFields.fields);
            const model = new RelationalModel(this.env, modelParams, {orm: this.orm});

            this.returnRecord = new model.constructor.Record(
                model,
                {
                    context: { ...this.props.list.context, in_checks_view: true },
                    activeFields: extractedFields.activeFields,
                    resModel: 'account.return',
                    fields: extractedFields.fields,
                    resId: accountReturnId,
                    resIds: [accountReturnId],
                    isMonoRecord: true,
                    mode: 'readonly',
                },
                returnData[0],
                { manuallyAdded: !returnData.id }
            )

            const originalLoad = this.props.list.model.load.bind(this.props.list.model);

            this.props.list.model.load = async (params) => {
                // Reload return card
                const result = await originalLoad(params);
                const returnData = await this.orm.webRead(
                    'account.return',
                    [accountReturnId],
                    { specification: this.specification }
                );
                this.returnRecord._setData(returnData[0]);

                // Reload chatter messages
                this.env.bus.trigger("MAIL:RELOAD-THREAD", {
                    model: "account.return",
                    id: accountReturnId,
                });

                return result;
            };
        });
    }

    getModelParams(activeFields, fields) {
        const modelConfig = {
            resModel: 'account.return',
            fields,
            activeFields,
            openGroupsByDefault: true,
        };

        return {
            config: modelConfig,
            groupsLimit: Number.MAX_SAFE_INTEGER,
            limit: 1,
            countLimit: 1,
        };
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

    sortChecks(records) {
        const getCheckPriority = (check) => {
            const { result, bypassed } = check;
            if (result === 'failure') return bypassed ? 20 : 0;
            if (result === 'manual') return bypassed ? 21 : 1;
            if (result === 'success') return 30;
            return 10;
        };
        return records.toSorted((a, b) => getCheckPriority(a.data) - getCheckPriority(b.data));
    }

    get sortedChecksList() {
        const { records } = this.props.list;
        return { records: this.sortChecks(records) };
    }

    get groups() {
        const { list } = this.props;
        if (!list.isGrouped) {
            return false;
        }
        return list.groups.map((group, index) => ({
            ...group,
            records: this.sortChecks(group.records),
            key: isNull(group.value) ? `group_key_${index}` : String(group.value),
        }));
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
