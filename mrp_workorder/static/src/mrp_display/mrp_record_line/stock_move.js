import { _t } from "@web/core/l10n/translation";
import { useActiveActions, useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { QualityCheck } from "./quality_check";
import { MrpQuantityDialog } from "../dialog/mrp_quantity_dialog";
import { MrpSelectQuantDialog } from "../dialog/mrp_select_quant_dialog";

export class StockMove extends QualityCheck {
    static props = {
        ...QualityCheck.props,
        displayUOM: Boolean,
        check: { optional: true, type: Object },
    };
    static template = "mrp_workorder.StockMove";

    setup() {
        this.dialog = useService("dialog");
        this.props.record.component = this;
        if (this.props.check) {
            this.props.check.component = this;
        }
        const activeActions = useActiveActions({
            fieldType: "one2many",
            getEvalParams: (props) => ({
                readonly: props.record.data.has_tracking === "none",
            }),
        });
        this.openQuantRecord = useOpenMany2XRecord({
            resModel: "stock.quant",
            activeActions: activeActions,
            onRecordSaved: (record) => this.selectQuant([record.resId]),
            fieldString: "Move Line",
            is2Many: true,
        });
    }

    get label() {
        return this.check ? super.label : this.props.record.data.product_id[1];
    }

    get isComplete() {
        return Boolean(this.props.record.data.picked);
    }

    get toConsumeQuantity() {
        const move = this.props.record.data;
        const parent = this.props.record._parentRecord.data;
        let toConsumeQuantity = move.should_consume_qty || move.product_uom_qty;
        if (parent.product_tracking === "serial") {
            toConsumeQuantity /= parent.product_qty;
        }
        return toConsumeQuantity;
    }

    get quantityDone() {
        return this.props.record.data.quantity;
    }

    get uom() {
        if (this.props.displayUOM) {
            return this.props.record.data.product_uom.display_name;
        }
        return this.toConsumeQuantity === 1 ? _t("Unit") : _t("Units");
    }

    get check() {
        return this.props.check ? this.props.check.data : false;
    }

    get hasInstruction() {
        return this.check ? super.hasInstruction : false;
    }

    get visibleMoveLines() {
        const { move_line_ids, picking_type_prefill_shop_floor_lots, has_tracking } =
            this.props.record.data;
        return picking_type_prefill_shop_floor_lots || has_tracking === "none"
            ? move_line_ids.records
            : move_line_ids.records.filter((ml) => ml.data.picked);
    }

    clicked() {
        const tracked = this.props.record.data.has_tracking !== "none";
        const [productId, productName] = this.props.record.data.product_id;
        this.dialog.add(MrpSelectQuantDialog, {
            resModel: "stock.quant",
            noCreate: !tracked,
            multiSelect: false,
            domain: [["product_id", "=", productId]],
            title: _t("Add line: %(productName)s", { productName }),
            context: {
                single_product: true,
                list_view_ref: "stock.view_stock_quant_tree_simple",
                search_default_on_hand: true,
                search_default_in_stock: true,
                hide_lot: this.props.record.data.has_tracking === "none",
                hide_available: true,
            },
            onSelected: (resIds) => this.selectQuant(resIds),
            onCreateEdit: () => this.createQuant(),
            record: this.props.record,
        });
    }

    async selectQuant(quantIds) {
        const { resId, model } = this.props.record;
        await model.orm.call("stock.move", "action_add_from_quant", [resId, quantIds[0]]);
        await this.env.reload(this.props.record._parentRecord);
    }

    createQuant() {
        return this.openQuantRecord({
            context: {
                form_view_ref: "stock.view_stock_quant_form",
                default_product_id: this.props.record.data.product_id[0],
            },
            immediate: true,
        });
    }

    editQuantity(record) {
        this.dialog.add(MrpQuantityDialog, {
            record,
            confirm: this.env.reload.bind(this, this.props.record._parentRecord),
        });
    }
}
