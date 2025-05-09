import { useSubEnv } from "@odoo/owl";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { makeActiveField } from "@web/model/relational_model/utils";
import { useService } from "@web/core/utils/hooks";
import { useBankReconciliation } from "./bank_reconciliation_service";

export class BankRecKanbanController extends KanbanController {
    static template = "account_accountant.BankRecoKanbanController";

    async setup() {
        super.setup();
        this.orm = useService("orm");
        this.bankReconciliation = useBankReconciliation();
        useSubEnv({
            bus: this.bankReconciliation.bus,
        });
    }

    async createRecord() {
        this.env.bus.trigger("createRecordQuickCreate");
    }

    get modelParams() {
        const params = super.modelParams;
        params.config.activeFields.move_id = makeActiveField();
        params.config.activeFields.move_id.related = {
            fields: {
                id: { name: "id", type: "int" },
                display_name: { name: "display_name", type: "char" },
                attachment_ids: { name: "attachment_ids", type: "one2many" },
            },
            activeFields: {
                attachment_ids: makeActiveField(),
            },
        };

        params.config.activeFields.partner_id = makeActiveField();
        params.config.activeFields.partner_id.related = {
            fields: {
                id: { name: "id", type: "int" },
                display_name: { name: "display_name", type: "char" },
                property_account_receivable_id: {
                    name: "property_account_receivable_id",
                    type: "many2one",
                },
                property_account_payable_id: {
                    name: "property_account_payable_id",
                    type: "many2one",
                },
                customer_rank: { name: "customer_rank", type: "int"},
                supplier_rank: { name: "supplier_rank", type: "int"},
            },
            activeFields: {
                id: makeActiveField(),
                display_name: makeActiveField(),
                property_account_receivable_id: makeActiveField(),
                property_account_payable_id: makeActiveField(),
                customer_rank: makeActiveField(),
                supplier_rank: makeActiveField(),
            },
        };

        params.config.activeFields.line_ids = makeActiveField();
        params.config.activeFields.line_ids.related = {
            fields: {
                id: { name: "id", type: "int" },
                display_name: { name: "display_name", type: "char" },
                name: { name: "name", type: "char" },
                balance: { name: "balance", type: "monetary" },
                amount_currency: { name: "amount_currency", type: "monetary" },
                currency_id: { name: "currency_id", type: "many2one" },
                currency_rate: { name: "currency_rate", type: "float" },
                is_same_currency: { name: "is_same_currency", type: "boolean" },
                company_currency_id: { name: "company_currency_id", type: "many2one" },
                account_id: { name: "account_id", type: "many2one" },
                partner_id: { name: "partner_id", type: "many2one" },
                move_id: { name: "move_id", type: "many2one" },
                move_attachment_ids: { name: "move_attachment_ids", type: "move_attachment_ids" },
                reconciled_lines_ids: { name: "reconciled_lines_ids", type: "many2many" },
                reconciled_lines_excluding_exchange_diff_ids: { name: "reconciled_lines_excluding_exchange_diff_ids", type: "many2many" },
                reconcile_model_id: { name: "reconcile_model_id", type: "many2one" },
            },
            activeFields: {
                id: makeActiveField(),
                display_name: makeActiveField(),
                name: makeActiveField(),
                balance: makeActiveField(),
                amount_currency: makeActiveField(),
                currency_id: makeActiveField(),
                currency_rate: makeActiveField(),
                is_same_currency: makeActiveField(),
                company_currency_id: makeActiveField(),
                account_id: makeActiveField(),
                partner_id: makeActiveField(),
                move_id: makeActiveField(),
                move_attachment_ids: makeActiveField(),
                reconciled_lines_ids: makeActiveField(),
                reconciled_lines_excluding_exchange_diff_ids: makeActiveField(),
                reconcile_model_id: makeActiveField(),
            },
        };
        params.config.activeFields.line_ids.related.activeFields.reconciled_lines_ids.related = {
            fields: {
                id: { name: "id", type: "int" },
                display_name: { name: "display_name", type: "char" },
                move_name: { name: "move_name", type: "char" },
                move_id: { name: "move_id", type: "many2one" },
                balance: { name: "balance", type: "monetary" },
                amount_currency: { name: "amount_currency", type: "monetary" },
                amount_residual: { name: "amount_residual", type: "monetary" },
                amount_residual_currency: { name: "amount_residual_currency", type: "monetary" },
                currency_id: { name: "currency_id", type: "many2one" },
            },
            activeFields: {
                id: makeActiveField(),
                display_name: makeActiveField(),
                move_name: makeActiveField(),
                move_id: makeActiveField(),
                balance: makeActiveField(),
                amount_currency: makeActiveField(),
                amount_residual: makeActiveField(),
                amount_residual_currency: makeActiveField(),
                currency_id: makeActiveField(),
            },
        };
        params.config.activeFields.line_ids.related.activeFields.reconciled_lines_excluding_exchange_diff_ids.related = {
            fields: {
                id: { name: "id", type: "int" },
                move_name: { name: "move_name", type: "char" },
                move_id: { name: "move_id", type: "many2one" },
            },
            activeFields: {
                id: makeActiveField(),
                move_name: makeActiveField(),
                move_id: makeActiveField(),
            },
        };
        params.config.activeFields.line_ids.related.activeFields.partner_id.related = {
            fields: {
                id: { name: "id", type: "int" },
                display_name: { name: "display_name", type: "char" },
                property_account_receivable_id: {
                    name: "property_account_receivable_id",
                    type: "many2one",
                },
                property_account_payable_id: {
                    name: "property_account_payable_id",
                    type: "many2one",
                },
            },
            activeFields: {
                id: makeActiveField(),
                display_name: makeActiveField(),
                property_account_receivable_id: makeActiveField(),
                property_account_payable_id: makeActiveField(),
            },
        };
        params.config.activeFields.line_ids.related.activeFields.account_id.related = {
            fields: {
                id: { name: "id", type: "int" },
                display_name: { name: "display_name", type: "char" },
                account_type: { name: "account_type", type: "char" },
            },
            activeFields: {
                id: makeActiveField(),
                display_name: makeActiveField(),
                account_type: makeActiveField(),
            },
        };
        params.config.activeFields.journal_id = makeActiveField();
        params.config.activeFields.journal_id.related = {
            fields: {
                id: { name: "id", type: "int" },
                suspense_account_id: { name: "suspense_account_id", type: "many2one" },
                default_account_id: { name: "default_account_id", type: "many2one" },
                currency_id: { name: "currency_id", type: "many2one" },
            },
            activeFields: {
                id: makeActiveField(),
                suspense_account_id: makeActiveField(),
                default_account_id: makeActiveField(),
                currency_id: makeActiveField(),
            },
        };
        params.config.activeFields.company_id = makeActiveField();
        params.config.activeFields.company_id.related = {
            fields: {
                id: { name: "id", type: "int" },
                currency_id: { name: "currency_id", type: "many2one" },
            },
            activeFields: {
                id: makeActiveField(),
                currency_id: makeActiveField(),
            },
        };
        return params;
    }
}
