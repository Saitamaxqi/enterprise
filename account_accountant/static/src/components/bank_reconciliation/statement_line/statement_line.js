import { BankRecButtonList } from "../button_list/button_list";
import { BankRecLineToReconcile } from "../line_to_reconcile/line_to_reconcile";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { formatMonetary } from "@web/views/fields/formatters";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { useBankReconciliation } from "../bank_reconciliation_service";

export class BankRecStatementLine extends KanbanRecord {
    static template = "account_accountant.BankRecStatementLine";
    static components = {
        BankRecLineToReconcile,
        BankRecButtonList,
        DropdownItem,
    };
    static props = [...KanbanRecord.props, "reconcileCountPerPartnerId", "reconcileModels"];

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.bankReconciliation = useBankReconciliation();
        this.state = useState({
            isUnfolded: false,
        });
    }

    // -----------------------------------------------------------------------------
    // ACTION
    // -----------------------------------------------------------------------------

    openStatementCreate() {
        this.action.doAction("account_accountant.action_bank_statement_form_bank_rec_widget", {
            additionalContext: {
                split_line_id: this.recordData.id,
                default_journal_id: this.recordData.journal_id.id,
            },
            onClose: async () => {
                this.env.model.load();
            },
        });
    }

    openJournalEntry() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: this.recordData.move_id.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // -----------------------------------------------------------------------------
    // HELPER
    // -----------------------------------------------------------------------------

    get record() {
        return this.props.record;
    }

    get recordData() {
        return this.props.record.data;
    }

    toggleUnfold() {
        this.state.isUnfolded = !this.isUnfolded;
        // Update the chatter with the last selected element
        this.bankReconciliation.selectStatementLine(this.record);
    }

    openChatter() {
        this.bankReconciliation.selectStatementLine(this.record);
        this.bankReconciliation.openChatter();
    }

    get isUnfolded() {
        return this.state.isUnfolded;
    }

    get formattedAmount() {
        const currencyId = this.recordData.currency_id[0];
        return formatMonetary(this.recordData.amount, { currencyId });
    }

    get formattedDate() {
        return this.recordData.date.toLocaleString({
            month: "short",
            day: "2-digit",
        });
    }

    get partner() {
        return this.recordData.partner_id;
    }

    get linesToReconcile() {
        return this.accountMoveLines.filter((line) => {
            return (
                line.account_id.id !== this.recordData.journal_id?.suspense_account_id.id &&
                line.account_id.id !== this.recordData.journal_id?.default_account_id.id
            );
        });
    }

    get suspenseAccountLine() {
        return this.accountMoveLines.filter((line) => {
            return line.account_id.id === this.recordData.journal_id.suspense_account_id.id;
        })?.[0];
    }

    get accountMoveLines() {
        return [...this.recordData.line_ids.records.map((line) => line.data)];
    }

    get suspenseAccountLineFormattedAmount() {
        return formatMonetary(this.suspenseAccountLine.amount_currency, {
            currencyId: this.suspenseAccountLine?.currency_id.id,
        });
    }

    get activityNumber() {
        return this.recordData.activity_ids.count;
    }

    get hasAttachment() {
        return this.recordData.move_id.attachment_ids.length;
    }

    get amountClasses() {
        const classes = this.recordData.foreign_currency_id ? "w-50" : "w-100";
        if (this.recordData.amount > 0) {
            return `${classes} text-success fw-bold`;
        }
        if (this.recordData.amount < 0) {
            return `${classes} text-danger fw-bold`;
        }
        return `${classes} text-secondary`;
    }

    get buttonListProps() {
        return {
            statementLine: this.record,
            reconcileLineCount:
                this.props.reconcileCountPerPartnerId[this.recordData.partner_id.id] ?? null,
            reconcileModels: this.props.reconcileModels,
            preSelectedReconciliationModel: this.accountMoveLines
                .filter((line) => line.reconcile_model_id.id)
                .map((line) => line.reconcile_model_id)?.[0],
        };
    }

    get formattedAmountCurrencyInForeign() {
        return formatMonetary(this.recordData.amount_currency, {
            currencyId: this.recordData.foreign_currency_id.id,
        });
    }

    get reconciledLineName() {
        const reconciledLineName = [];
        for (const line of this.linesToReconcile) {
            if (
                line.reconciled_lines_ids.records.length === 1 &&
                line.reconciled_lines_ids.records[0].data.move_name
            ) {
                reconciledLineName.push(line.reconciled_lines_ids.records[0].data.move_name);
            } else {
                reconciledLineName.push(line.account_id.display_name);
            }
        }
        return reconciledLineName.join(", ");
    }

    get isChatterOpen() {
        return (
            this.bankReconciliation.chatterState.visible &&
            this.recordData.move_id.id === this.bankReconciliation.statementLineMoveId
        );
    }
}
