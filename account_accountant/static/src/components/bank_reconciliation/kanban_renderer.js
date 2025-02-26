import { BankRecChatter } from "./chatter/chatter";
import { BankRecQuickCreate } from "./quick_create/quick_create";
import { BankRecKanbanController } from "./kanban_controller";
import { BankRecStatementLine } from "./statement_line/statement_line";
import { BankRecStatementSummary } from "./statement_summary/statement_summary";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";
import { onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BankRecKanbanRenderer extends KanbanRenderer {
    static template = "account_accountant.BankRecKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        BankRecQuickCreate,
        BankRecStatementSummary,
        BankRecStatementLine,
        BankRecChatter,
    };

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.globalState = useState({
            resModel: this.env.model.config.resModel,
            context: this.env.model.config.context,
            quickCreate: {
                isVisible: false,
                quickCreateView: this.props.archInfo.quickCreateView,
            },
            journalId: this.env.model.config.context.active_id,
            totalJournalAmount: "",
            chatterState: {
                visible: false,
                moveId: false,
                statementLine: false,
            },
            reconcileCountPerPartnerId: {},
            reconcileModels: [],
        });
        this.env.bus.addEventListener("createRecordQuickCreate", () => {
            this.globalState.quickCreate.isVisible = true;
        });
        this.env.bus.addEventListener("openChatter", (event) => {
            const moveId = event.detail.moveId;
            if (this.globalState.chatterState.moveId !== moveId) {
                this.globalState.chatterState.visible = true;
                this.globalState.chatterState.moveId = moveId;
                this.globalState.chatterState.statementLine = event.detail.statementLine;
            } else {
                this.globalState.chatterState.visible = false;
                this.globalState.chatterState.moveId = false;
            }
        });

        this.env.bus.addEventListener("RECOMPUTE_AVAILABLE_RECONCILE_LINES", (ev) => {
            this.computeReconcileLineCountPerPartnerId();
        });
        this.env.bus.addEventListener("RELOAD_STATEMENT_LINES_FOR_PARTNER_NAME", (ev) => {
            const recordsToLoad = this.env.model.root.records.filter(
                (record) => record.data.partner_name === ev.detail
            );
            for (const record of recordsToLoad) {
                record.load();
            }
        });

        onWillStart(async () => {
            this.getJournalTotalAmount();
            await this.computeReconcileLineCountPerPartnerId();
            await this.getReconcileModels();
        });
    }

    /**
        Override.
    **/
    cancelQuickCreate() {
        this.globalState.quickCreate.isVisible = false;
    }

    /**
        Override.
    **/
    async validateQuickCreate(_recordId, mode) {
        // When adding a record, some information needs to be recomputed
        await this.env.model.load();
        await this.getJournalTotalAmount();

        if (mode === "add_close") {
            this.globalState.quickCreate.isVisible = false;
        }
    }

    async computeReconcileLineCountPerPartnerId(recordIds = null) {
        if (!recordIds) {
            recordIds = this.env.model.root.records.map((record) => record.data.id);
        }
        const result = await this.orm.webReadGroup(
            "account.move.line",
            [
                ["parent_state", "in", ["draft", "posted"]],
                [
                    "partner_id",
                    "in",
                    this.env.model.root.records
                        .filter((record) => !!record.data.partner_id.id)
                        .map((record) => record.data.partner_id.id),
                ],
                [
                    "company_id",
                    "child_of",
                    this.env.model.root.records.map((record) => record.data.company_id.id),
                ],
                ["account_id.reconcile", "=", true],
                ["display_type", "not in", ["line_section", "line_note"]],
                ["reconciled", "=", false],
                "|",
                ["account_id.account_type", "not in", ["asset_receivable", "liability_payable"]],
                ["payment_id", "=", false],
                ["statement_line_id", "not in", recordIds],
            ],
            ["partner_id"],
            ["id:count"]
        );

        result.groups.forEach((group) => {
            this.globalState.reconcileCountPerPartnerId[group.partner_id[0]] = group["id:count"];
        });
    }

    async getJournalTotalAmount() {
        const value = await this.orm.call("account.journal", "get_total_journal_amount", [
            this.globalState.journalId,
        ]);
        this.globalState.totalJournalAmount = value.balance_amount;
    }

    async getReconcileModels() {
        const result = await this.orm.webSearchRead(
            "account.reconcile.model",
            [
                "|",
                ["match_journal_ids", "=", false],
                ["match_journal_ids", "=", this.globalState.journalId],
            ],
            {
                specification: {
                    id: {},
                    display_name: {},
                },
            }
        );
        this.globalState.reconcileModels = result.records;
    }

    // -----------------------------------------------------------------------------
    // ACTION
    // -----------------------------------------------------------------------------
    async actionOpenBankGL() {
        const actionData = await this.orm.call(
            "account.journal",
            "action_open_bank_balance_in_gl",
            [this.env.model.config.context.active_id]
        );
        this.action.doAction(actionData);
    }

    actionOpenStatement(statementId) {
        const action = {
            type: "ir.actions.act_window",
            res_model: "account.bank.statement",
            res_id: statementId,
            views: [[false, "form"]],
            target: "current",
            context: {
                form_view_ref: "account_accountant.view_bank_statement_form_bank_rec_widget",
            },
        };

        this.action.doAction(action);
    }

    // -----------------------------------------------------------------------------
    // GETTER
    // -----------------------------------------------------------------------------

    get quickCreateContext() {
        return {
            ...this.globalState.context,
            auto_statement_processing: true,
        };
    }

    get hideCurrentBalance() {
        return this.env.searchModel.context?.hide_current_balance;
    }

    get hasStatementLine() {
        return this.env.model.root.count;
    }

    get totalJournalLabel() {
        return _t("Current Balance");
    }

    /**
    Prepares a list of statements based on the statement_id of the bank statement line records.
    Statements are only displayed above the first line of the statement (all lines might not be visible in the kanban)
    **/
    get statementGroups() {
        const statementGroups = {};
        let lastStatementId = null;
        for (const record of this.env.model.root.records) {
            const statementId = record.data.statement_id?.[0];
            if (statementId && statementId !== lastStatementId) {
                // Add the statement group information to the statementGroups object
                statementGroups[record.data.id] = {
                    statementId: statementId,
                    name: record.data.statement_name,
                    balance: formatMonetary(record.data.statement_balance_end_real, {
                        currencyId: record.data.currency_id[0],
                    }),
                };
                lastStatementId = statementId;
            } else {
                if (
                    Object.keys(statementGroups).length &&
                    !statementId &&
                    typeof lastStatementId !== "string"
                ) {
                    statementGroups[record.data.id] = {
                        name: _t("No Bank Statement"),
                    };
                    lastStatementId = "no_bank_statement";
                }
            }
        }
        return statementGroups;
    }

    get isQuickCreateVisible() {
        return this.globalState.quickCreate.isVisible;
    }
}

export const BankRecKanbanView = {
    ...kanbanView,
    Controller: BankRecKanbanController,
    Renderer: BankRecKanbanRenderer,
    searchMenuTypes: ["filter", "favorite"],
};

registry.category("views").add("bank_rec_widget_kanban", BankRecKanbanView);
