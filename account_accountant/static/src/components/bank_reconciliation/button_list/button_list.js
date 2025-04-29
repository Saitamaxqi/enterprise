import { BankRecButton } from "../button/button";
import { BankRecFileUploader } from "../file_uploader/file_uploader";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { BankRecSelectCreateDialog } from "../search_dialog/search_dialog";
import { _t } from "@web/core/l10n/translation";
import { getCurrency } from "@web/core/currency";
import { roundDecimals } from "@web/core/utils/numbers";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { useBankReconciliation } from "../bank_reconciliation_service";

export class BankRecButtonList extends Component {
    static template = "account_accountant.BankRecButtonList";
    static components = {
        Dropdown,
        DropdownItem,
        BankRecButton,
        BankRecFileUploader,
    };
    static props = {
        statementLine: { type: Object },
        isTopLine: { type: Boolean, optional: true },
        suspenseAccountLine: { type: Object, optional: true },
        reconcileLineCount: { type: [Number, { value: null }], optional: true },
        reconcileModels: Array,
        preSelectedReconciliationModel: { type: Object, optional: true },
    };
    static defaultProps = {
        isTopLine: false,
        reconcileLineCount: 0,
    };

    setup() {
        this.action = useService("action");
        this.ui = useService("ui");
        this.orm = useService("orm");

        this.addDialog = useOwnedDialogs();
        this.currencyDigits = getCurrency(this.statementLineData.currency_id[0])?.digits || 2;
        this.bankReconciliation = useBankReconciliation();
    }

    /**
     * Displays a search dialog (no create option) for selecting a `res.partner` record.
     */
    setPartnerOnReconcileLine() {
        this.addDialog(SelectCreateDialog, {
            title: _t("Search: Partner"),
            noCreate: false,
            multiSelect: false,
            resModel: "res.partner",
            context: { default_name: this.statementLineData.partner_name },
            onSelected: async (partner) => {
                await this.orm.call(
                    "account.bank.statement.line",
                    "set_partner_bank_statement_line",
                    [this.statementLineData.id, partner[0]]
                );
                const recordsToLoad = [];
                if (this.statementLineData.partner_name) {
                    // Reload all impacted statement lines if we have a partner_name
                    recordsToLoad.push(
                        ...this.env.model.root.records.filter(
                            (record) =>
                                record.data.partner_name === this.statementLineData.partner_name
                        )
                    );
                } else {
                    recordsToLoad.push(this.props.statementLine);
                }
                await this.bankReconciliation.reloadRecords(recordsToLoad);
                await this.bankReconciliation.computeReconcileLineCountPerPartnerId(
                    this.env.model.root.records
                );
                this.bankReconciliation.reloadChatter();
            },
        });
    }

    /**
     * Opens a dialog to select an account and assigns it to the current reconcile line.
     */
    setAccountOnReconcileLine() {
        const context = {
            list_view_ref: "account_accountant.view_account_list_bank_rec_widget",
            ...(this.statementLineData.amount > 0
                ? { search_default_incomeacc: 1 }
                : { search_default_expensesacc: 1, search_default_assetsacc: 1 }),
        };

        this.addDialog(SelectCreateDialog, {
            title: _t("Search: Account"),
            noCreate: true,
            multiSelect: false,
            context: context,
            resModel: "account.account",
            onSelected: async (account) => {
                await this._setAccountOnReconcileLine(this.lastAccountMoveLine.data.id, account[0]);
            },
        });
    }

    /**
     * Assigns the given account to a specific account move line within the current bank statement line.
     *
     * @param {number} amlId - ID of the account move line to update.
     * @param {number} accountId - ID of the selected account to assign.
     */
    async _setAccountOnReconcileLine(amlId, accountId) {
        await this.orm.call("account.bank.statement.line", "set_account_bank_statement_line", [
            this.statementLineData.id,
            amlId,
            accountId,
        ]);
        this.props.statementLine.load();
        this.bankReconciliation.reloadChatter();
    }

    /**
     * Sets the account receivable on the current reconcile line.
     */
    async setAccountReceivableOnReconcileLine() {
        let accountId;
        if (this.props.statementLine.data.partner_id.property_account_receivable_id.id) {
            accountId = this.props.statementLine.data.partner_id.property_account_receivable_id.id;
        } else {
            accountId = await this.orm.webSearchRead("account.account", [
                ["account_type", "=", "asset_receivable"],
            ]);
        }
        await this._setAccountOnReconcileLine(this.lastAccountMoveLine.data.id, accountId);
    }

    /**
     * Sets the account payable on the current reconcile line..
     */
    async setAccountPayableOnReconcileLine() {
        let accountId;
        if (this.statementLineData.partner_id.property_account_payable_id.id) {
            accountId = this.props.statementLine.data.partner_id.property_account_payable_id.id;
        } else {
            accountId = await this.orm.webSearchRead("account.account", [
                ["account_type", "=", "liability_payable"],
            ]);
        }
        await this._setAccountOnReconcileLine(this.lastAccountMoveLine.data.id, accountId);
    }

    /**
     * Opens a dialog to search and select journal items to reconcile with the current bank statement line.
     */
    reconcileOnReconcileLine() {
        const context = {
            list_view_ref: "account_accountant.view_account_move_line_list_bank_rec_widget",
            ...(this.statementLineData.partner_id
                ? { search_default_partner_id: this.statementLineData.partner_id[0] }
                : {}),
        };

        this.addDialog(BankRecSelectCreateDialog, {
            title: _t("Search: Journal Items to Match"),
            noCreate: true,
            domain: this.getReconcileButtonDomain(),
            resModel: "account.move.line",
            size: "xl",
            context: context,
            onSelected: async (moveLines) => {
                await this.orm.call("account.bank.statement.line", "set_line_bank_statement_line", [
                    this.statementLineData.id,
                    moveLines,
                ]);
                await this.bankReconciliation.computeReconcileLineCountPerPartnerId(
                    this.env.model.root.records
                );
                this.props.statementLine.load();
                this.bankReconciliation.reloadChatter();
            },
            suspenseAccountLine: this.props.suspenseAccountLine,
            reference: this.statementLineData.payment_ref,
            date: this.statementLineData.date,
        });
    }

    getReconcileButtonDomain(partnerId = null) {
        const partnerDomain = partnerId
            ? ["partner_id", "=", partnerId]
            : ["partner_id", "!=", false];
        return [
            ["parent_state", "in", ["draft", "posted"]],
            partnerDomain,
            ["company_id", "child_of", this.statementLineData.company_id.id],
            ["account_id.reconcile", "=", true],
            ["display_type", "not in", ["line_section", "line_note"]],
            ["reconciled", "=", false],
            "|",
            ["account_id.account_type", "not in", ["asset_receivable", "liability_payable"]],
            ["payment_id", "=", false],
            ["statement_line_id", "!=", this.statementLineData.id],
        ];
    }

    /**
     * Deletes the current bank statement line.
     */
    async deleteTransaction() {
        this.addDialog(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this statement line?"),
            confirm: async () => {
                await this.orm.unlink("account.bank.statement.line", [this.statementLineData.id]);
                this.env.model.load();
            },
            cancel: () => {},
        });
    }

    // -----------------------------------------------------------------------------
    // Reconciliation Model
    // -----------------------------------------------------------------------------
    /**
     * Applies a reconciliation model to the current bank statement line.
     *
     * @param {number} reconciliationModelId - The ID of the reconciliation model to apply.
     */
    async triggerReconciliationModel(reconciliationModelId) {
        await this.orm.call("account.reconcile.model", "trigger_reconciliation_model", [
            reconciliationModelId,
            this.statementLineData.id,
        ]);
        this.props.statementLine.load();
        this.bankReconciliation.reloadChatter();
    }

    // -----------------------------------------------------------------------------
    // File Uploader
    // -----------------------------------------------------------------------------
    get bankRecFileUploaderRecord() {
        return {
            statementLineId: this.statementLineData.id,
        };
    }

    // -----------------------------------------------------------------------------
    // ACTION
    // -----------------------------------------------------------------------------
    openJournalEntry() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: this.statementLineData.move_id.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    actionViewRecoModels() {
        return this.action.doAction("account.action_account_reconcile_model");
    }

    // -----------------------------------------------------------------------------
    // GETTER
    // -----------------------------------------------------------------------------
    get statementLineData() {
        return this.props.statementLine.data;
    }

    get lastAccountMoveLine() {
        return this.statementLineData.line_ids.records.at(-1);
    }

    get isPositiveOr0() {
        return roundDecimals(this.statementLineData.amount, this.currencyDigits) >= 0;
    }

    get isSetPartnerButtonShown() {
        return !this.statementLineData.partner_id;
    }

    get isSetAccountButtonShown() {
        return !this.statementLineData.account_id;
    }

    get isSetReceivableButtonShown() {
        return this.isPositiveOr0 && !this.isSetPartnerButtonShown;
    }

    get isSetPayableButtonShown() {
        return !this.isPositiveOr0 && !this.isSetPartnerButtonShown;
    }

    get isReconcileButtonShown() {
        // Show the button if we have more than one reconciliable line
        // or if we didn't compute it yet
        return this.props.reconcileLineCount === null || this.props.reconcileLineCount;
    }

    /**
     * Dynamically builds the list of action buttons to be shown in the reconciliation interface.
     *
     * @returns {Object} buttonsToDisplay - A dictionary of buttons to render in the UI.
     */
    get buttons() {
        const buttonsToDisplay = {};
        if (this.isSetPartnerButtonShown) {
            buttonsToDisplay.partner = {
                label: _t("Set Partner"),
                action: this.setPartnerOnReconcileLine.bind(this),
            };
        }

        if (this.isReconcileButtonShown) {
            buttonsToDisplay.reconcile = {
                label: _t("Reconcile"),
                action: this.reconcileOnReconcileLine.bind(this),
                count: this.props.reconcileLineCount,
            };
        }

        if (this.isSetReceivableButtonShown) {
            buttonsToDisplay.receivable = {
                label: _t("Receivable"),
                action: this.setAccountReceivableOnReconcileLine.bind(this),
            };
        } else if (this.isSetPayableButtonShown) {
            buttonsToDisplay.payable = {
                label: _t("Payable"),
                action: this.setAccountPayableOnReconcileLine.bind(this),
            };
        }

        if (this.isSetAccountButtonShown) {
            buttonsToDisplay.account = {
                label: _t("Set Account"),
                action: this.setAccountOnReconcileLine.bind(this),
            };
        }

        return buttonsToDisplay;
    }

    /**
     * Prioritizing which buttons are shown and which one is marked as "primary".
     *
     * @returns {Array<Object>} An array of button objects, each with label, action, and optionally `primary`.
     */
    get buttonsToDisplay() {
        const buttons = this.buttons;
        if (this.props.isTopLine) {
            if (this.isPositiveOr0 && buttons?.partner) {
                return [{ ...buttons.partner, primary: true }];
            }
            if (buttons?.partner && buttons?.account) {
                return [
                    { ...buttons.partner, primary: true },
                    { ...buttons.account, primary: true },
                ];
            }
            if (buttons?.reconcile && !!buttons.reconcile?.count) {
                return [{ ...buttons.reconcile, primary: true }];
            }
            if (buttons?.receivable) {
                return [{ ...buttons.receivable, primary: true }];
            }
            if (buttons?.payable) {
                return [{ ...buttons.payable, primary: true }];
            }
        }
        const buttonsVals = Object.values(buttons);

        if (this.ui.isSmall) {
            return [buttonsVals[0]];
        }
        return buttonsVals;
    }

    get mobileButtonsToDisplay() {
        const buttons = Object.values(this.buttonsToDisplay);
        return buttons.slice(1);
    }
}
