import { PaymentWorldline } from "@pos_iot/app/payment";

export class PaymentSix extends PaymentWorldline {
    getPaymentData(uuid) {
        const paymentline = this.pos.getOrder().getPaymentlineByUuid(uuid);
        const pos = this.pos;
        return {
            messageType: "Transaction",
            transactionType: paymentline.transactionType,
            amount: Math.round(paymentline.amount * 100),
            currency: pos.currency.name,
            cid: uuid,
            posId: pos.session.name,
            userId: pos.session.user_id.id,
        };
    }

    sendPaymentRequest(uuid) {
        const paymentline = this.pos.getOrder().getPaymentlineByUuid(uuid);
        paymentline.transactionType = "Payment";

        return super.sendPaymentRequest(uuid);
    }
}
