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
        this.state.remainingAmount = this.suspenseAccountLine.balance;

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

        const selectedLinesSum = this.selectedLines.reduce((sum, id) => {
            return sum + this.displayedMoveLinesPerId[id].amount_residual;
        }, 0);

        this.state.remainingAmount = this.suspenseAccountLine.balance + selectedLinesSum;
    }

    async fetchMissingLines(domain) {
        const moveLines = await this.orm.searchRead(
            "account.move.line",
            domain,
            ["amount_residual"],
            { context: this.props.context }
        );
        moveLines.forEach((line) => {
            this.displayedMoveLinesPerId[line.id] = {
                amount_residual: line.amount_residual,
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
