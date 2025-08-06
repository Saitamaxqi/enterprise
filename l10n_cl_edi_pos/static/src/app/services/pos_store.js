import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    // @Override
    async processServerData() {
        await super.processServerData();

        if (this.isChileanCompany()) {
            this["l10n_latam.identification.type"] =
                this.models["l10n_latam.identification.type"].getFirst();
        }
    },
    isChileanCompany() {
        return this.company.country_id?.code == "CL";
    },
    getSyncAllOrdersContext(orders, options = {}) {
        let context = super.getSyncAllOrdersContext(...arguments);
        if (this.isChileanCompany() && orders) {
            // FIXME in master: when processing multiple orders, and at least one is an invoice of type Factura,
            //  then we will generate the pdf for all invoices linked to the orders,
            //  since the context is applicable for the whole RPC requests `create_from_ui` on all orders.
            const noOrderRequiresInvoicePrinting = orders.every(
                (order) => order.to_invoice && order.invoice_type === "boleta"
            );
            if (noOrderRequiresInvoicePrinting) {
                context = { ...context, generate_pdf: false };
            }
        }
        return context;
    },
    createNewOrder() {
        const order = super.createNewOrder(...arguments);
        if (!order.partner_id && this.isChileanCompany()) {
            order.partner_id = this.config._consumidor_final_anonimo_id;
        }
        return order;
    },

    async askBeforeValidation() {
        if (
            this.isChileanCompany() &&
            this.getOrder()?.payment_ids?.some((line) => line.payment_method_id.is_card_payment)
        ) {
            const voucherNumber = await makeAwaitable(this.dialog, TextInputPopup, {
                rows: 4,
                title: _t("Please register the voucher number"),
            });
            if (!voucherNumber) {
                return;
            }
            this.getOrder().voucher_number = voucherNumber;
        }
        return await super.askBeforeValidation();
    },
});
