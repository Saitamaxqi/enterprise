import { Domain } from "@web/core/domain";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { formatMonetary } from "@web/views/fields/formatters";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class BankRecSelectCreateDialog extends SelectCreateDialog {
    static template = "account_accountant.BankRecSelectCreateDialog";
    static props = {
        ...SelectCreateDialog.props,
        suspenseAccountLine: Object,
        reference: String,
        date: DateTime,
        size: { type: String, optional: true },
    };

    static defaultProps = {
        ...SelectCreateDialog.defaultProps,
        size: "lg",
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state.remainingAmount = this.suspenseAccountLine.amount_currency;
        this.state.hideRemainingAmount = false;

        this.baseViewProps.onSelectionChanged = (resIds) => {
            this.state.resIds = resIds;
            this.changeInSelectedMoveLine();
        };
        this.displayedMoveLinesPerId = {};

        onWillStart(async () => {
            const context = this.props.context;
            let domain = this.props.domain;
            if (context.search_default_partner_id) {
                domain = Domain.and([
                    this.props.domain,
                    [["partner_id", "=", context.search_default_partner_id]],
                ]).toList(context);
            }
            await this.fetchMissingLines(domain);
        });
    }

    async changeInSelectedMoveLine() {
        const resIdsToFetch = this.state.resIds.filter((id) => {
            return !(id in this.displayedMoveLinesPerId);
        });

        if (resIdsToFetch.length) {
            await this.fetchMissingLines([["id", "in", resIdsToFetch]]);
        }

        let selectedLinesSum = 0;
        this.state.hideRemainingAmount = false;
        // When the suspense currency is different from the company one, we cannot compute the remaining amount correctly
        // due to the currency rates. So in this case, when the user select multiple currencies we add the remaining amount
        if (
            this.suspenseAccountLine.currency_id.id !==
                this.suspenseAccountLine.company_currency_id.id &&
            this.selectedLines.length
        ) {
            const selectedLineCurrencies = this.selectedLines.map(
                (id) => this.displayedMoveLinesPerId[id].currency_id
            );
            if (
                selectedLineCurrencies.length !== 1 ||
                (selectedLineCurrencies.length === 1 &&
                    selectedLineCurrencies[0] !== this.suspenseAccountLine.currency_id.id)
            ) {
                this.state.hideRemainingAmount = true;
                return;
            } else {
                selectedLinesSum = this.selectedLines.reduce((sum, id) => {
                    return sum + this.displayedMoveLinesPerId[id].amount_residual_currency;
                }, 0);
            }
        } else {
            selectedLinesSum = this.selectedLines.reduce((sum, id) => {
                return sum + this.displayedMoveLinesPerId[id].amount_residual;
            }, 0);
        }
        this.state.remainingAmount = this.suspenseAccountLine.amount_currency + selectedLinesSum;
    }

    async fetchMissingLines(domain) {
        const moveLines = await this.orm.searchRead(
            "account.move.line",
            domain,
            ["amount_residual", "amount_residual_currency", "currency_id"],
            { context: this.props.context }
        );
        moveLines.forEach((line) => {
            this.displayedMoveLinesPerId[line.id] = {
                amount_residual: line.amount_residual,
                amount_residual_currency: line.amount_residual_currency,
                currency_id: line.currency_id[0],
            };
        });
    }

    get suspenseAccountLine() {
        return this.props?.suspenseAccountLine;
    }

    get remainingAmountFormatted() {
        return formatMonetary(this.state.remainingAmount, {
            currencyId: this.suspenseAccountLine.currency_id.id,
        });
    }

    get formattedStatementLineDate() {
        return this.props.date?.toLocaleString();
    }

    get selectedLines() {
        return this.state.resIds.filter((id) => {
            return id in this.displayedMoveLinesPerId;
        });
    }
}
