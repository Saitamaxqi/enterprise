import { _t } from "@web/core/l10n/translation";
import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";

/**
 * Used to send print requests to the IoT box through the provided `device` - a `DeviceController` instance.
 */
export class IoTPrinter extends BasePrinter {
    setup({ device, iot_http }) {
        super.setup(...arguments);
        this.device = device;
        this.iotBox = iot_http;
    }

    /**
     * @override
     */
    openCashbox() {
        return this.action({ action: "cashbox" });
    }

    /**
     * @override
     */
    sendPrintingJob(img) {
        return this.action({ action: "print_receipt", receipt: img });
    }

    async action(data) {
        return new Promise((resolve) => {
            this.iotBox.action(this.device.iotId, this.device.identifier, data);
            resolve(true);
        });
    }

    /**
     * @override
     */
    getActionError() {
        if (window.isSecureContext && this.device.iotIp.endsWith(".odoo-iot.com")) {
            return {
                successful: false,
                canRetry: true,
                message: {
                    title: _t("Connection to IoT Box failed"),
                    body: _t(
                        "Your IoT box is registered, but your browser could not reach it.\n" +
                            "Ensure it is powered on and connected to the network.\n\n" +
                            "If you have just paired the IoT box, you may be experiencing a DNS issue.\n" +
                            "If you wait for some time the problem may resolve itself."
                    ),
                },
            };
        }
        return super.getActionError();
    }
}
