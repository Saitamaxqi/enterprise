import { Component } from "@odoo/owl";

export default class HeaderComponent extends Component {
    static props = ["displayUOM", "openDetails", "line"];
    static template = "stock_barcode_mrp.HeaderComponent";

    setup() {
        this.line = this.props.line;
    }

    get order() {
        return this.env.model.record;
    }

    get qtyDemand() {
        return this.order.product_qty;
    }

    get incrementQty() {
        return Math.max(this.order.product_qty - this.order.qty_producing, 0);
    }

    get qtyDone() {
        return this.order.qty_producing;
    }

    get isTracked() {
        return this.order.product_id.tracking !== "none";
    }

    get lotName() {
        if(this.order.lot_producing_ids.length == 1) {
            return this.order.lot_producing_ids[0].name;
        }
        return this.order.lot_name || "";
    }

    get isComplete() {
        return this.env.model.isComplete;
    }

    get componentClasses() {
        return this.isComplete ? "o_header_completed" : "";
    }

    get hideProduceButton() {
        return this.incrementQty === 0;
    }

    get isSelected() {
        return true;
    }
}
