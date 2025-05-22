import { Component, useRef } from "@odoo/owl";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { useBankReconciliation } from "../bank_reconciliation_service";
import { usePopover } from "@web/core/popover/popover_hook";
import { BankRecLineInfoPopOver } from "../line_info_pop_over/line_info_pop_over";

export class BankRecLineToReconcile extends Component {
    static template = "account_accountant.BankRecLineToReconcile";

    static props = {
        line: Object,
        statementLine: Object,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.bankReconciliation = useBankReconciliation();

        this.lineInfoRef = useRef("line-info-ref");
        this.lineInfoPopOver = usePopover(BankRecLineInfoPopOver, {
            position: "left",
            closeOnClickAway: true,
        });
    }

    /**
     * Opens a dialog to edit a bank statement line and saves any changes.
     *
     * This method:
     * - Opens a dialog (`FormViewDialog`) to allow the user to edit the current `account.move.line`.
     * - On saving, the dialog triggers the `onRecordSave` callback, which:
     *   - Calls `edit_bank_statement_line` on the ORM to update the bank statement line.
     *   - Reloads the statement line data.
     *   - Updates the chatter on the related journal entry.
     */
    toggleEditLine() {
        this.dialogService.add(FormViewDialog, {
            title: _t("Edit Line"),
            resModel: "account.move.line",
            resId: this.lineData.id,
            context: {
                form_view_ref: "account_accountant.view_bank_rec_edit_line",
            },
            onRecordSave: async (record) => {
                await this.orm.call("account.bank.statement.line", "edit_reconcile_line", [
                    this.statementLineData.id,
                    this.lineData.id,
                    await record.getChanges(),
                ]);
                this.props.statementLine.load();
                this.bankReconciliation.reloadChatter();
                return true;
            },
        });
    }

    /**
     * Deletes a line to reconcile.
     *
     * This method:
     * - Calls `delete_reconciled_line` on the ORM to delete the line.
     * - Reloads the statement line data after deletion.
     * - Updates the chatter on the related journal entry.
     */
    async deleteLine() {
        await this.orm.call("account.bank.statement.line", "delete_reconciled_line", [
            this.statementLineData.id,
            this.lineData.id,
        ]);
        if (this.lineData.reconciled_lines_ids.records.length) {
            // Only update the line count per partner if we delete
            // a line which is reconciled to another move line
            // We don't use await here as it could be reloaded asynchronously.
            this.bankReconciliation.computeReconcileLineCountPerPartnerId(
                this.env.model.root.records
            );
        }
        this.props.statementLine.load();
        this.bankReconciliation.reloadChatter();
    }

    // -----------------------------------------------------------------------------
    // ACTION
    // -----------------------------------------------------------------------------
    openMove() {
        if (this.moveData.id !== this.statementLineData.move_id.id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "account.move",
                res_id: this.moveData.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    openPartner() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: this.lineData.partner_id.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openLineInfoPopOver() {
        if (this.lineInfoPopOver.isOpen || !this.showLineInfo) {
            this.lineInfoPopOver.close();
        } else {
            this.lineInfoPopOver.open(this.lineInfoRef.el, {
                statementLineData: this.statementLineData,
                lineData: this.lineData,
                exchangeMove: this.exchangeMove,
                isPartiallyReconciled: this.isPartiallyReconciled,
            });
        }
    }

    // -----------------------------------------------------------------------------
    // GETTER
    // -----------------------------------------------------------------------------
    get statementLineData() {
        return this.props.statementLine.data;
    }

    get lineData() {
        return this.props.line;
    }

    get reconciledLineId() {
        return this.lineData.reconciled_lines_ids.records.length === 1
            ? this.lineData.reconciled_lines_ids.records[0].data
            : null;
    }

    get reconciledLineExcludingExchangeDiffId() {
        return this.lineData.reconciled_lines_excluding_exchange_diff_ids.records.length === 1
            ? this.lineData.reconciled_lines_excluding_exchange_diff_ids.records[0].data
            : null;
    }

    get moveData() {
        return (
            this.reconciledLineId?.move_id ||
            this.reconciledLineExcludingExchangeDiffId?.move_id ||
            this.lineData.move_id
        );
    }

    get isPartiallyReconciled() {
        if (!this.reconciledLineId) {
            return false;
        }
        return !this.reconciledLineId.full_reconcile_id?.id;
    }

    get hasDifferentCurrencies() {
        return this.lineData.currency_id.id !== this.statementLineData.currency_id.id;
    }

    get formattedAmountCurrencyOfLine() {
        return formatMonetary(this.lineData.amount_currency, {
            currencyId: this.lineData.currency_id.id,
        });
    }

    get formattedAmountCurrencyOfStatementLine() {
        return formatMonetary(this.lineData.amount_currency, {
            currencyId: this.statementLineData.currency_id.id,
        });
    }

    get exchangeMove() {
        return (
            this.lineData.matched_debit_ids.records[0]?.data.exchange_move_id ||
            this.lineData.matched_credit_ids.records[0]?.data.exchange_move_id
        );
    }

    get showLineInfo() {
        return this.isPartiallyReconciled || this.exchangeMove?.id;
    }
}
