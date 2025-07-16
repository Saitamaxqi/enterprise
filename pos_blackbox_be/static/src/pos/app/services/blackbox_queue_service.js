import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { BlackboxError } from "@pos_blackbox_be/pos/app/utils/blackbox_error";

export const blackboxQueueService = {
    dependencies: ["hardware_proxy", "dialog", "pos_data", "bus_service", "iot_http"],
    start(env, { hardware_proxy, dialog, pos_data, bus_service, iot_http }) {
        return new BlackboxQueueService(env, {
            hardware_proxy,
            dialog,
            pos_data,
            bus_service,
            iot_http,
        });
    },
};
class BlackboxQueueService {
    constructor(...args) {
        this.setup(...args);
    }
    setup(env, { hardware_proxy, dialog, pos_data, bus_service, iot_http }) {
        this.hardwareProxy = hardware_proxy;
        this.dialog = dialog;
        this.data = pos_data;
        this.bus = bus_service;
        this.iotHttp = iot_http;
        this.queue = JSON.parse(localStorage.getItem(this.key)) || [];
        this.waitForNextRequest = false;
        this.isFlushing = false;
        this.debounceFlush = debounce(this.flush.bind(this), 1000); //Flush after 1 second of inactivity
        this.callbacks = {
            default_callback: (data) => data,
        };
    }
    get key() {
        return `pos_bb_queue_${odoo.access_token}`;
    }
    addCallback(callback, callbackName) {
        this.callbacks[callbackName] = callback;
    }
    async enqueue(
        requestData,
        action = "registerReceipt",
        callbackName = "default_callback",
        args = [],
        force = false
    ) {
        this.waitForNextRequest = false; // Reset the flag when a new request is added
        this.queue.push({ requestData, action, callbackName, args, force });
        localStorage.setItem(this.key, JSON.stringify(this.queue));
        if (force) {
            this.debounceFlush.cancel(); // Cancel any pending flush and flush immediately
            return this.flush();
        } else {
            this.debounceFlush();
            return;
        }
    }

    async callback(blackboxResponse, callbackName, args) {
        try {
            const result = this.extractResult(blackboxResponse);
            if (!result?.error?.errorCode.startsWith("000")) {
                throw result.error;
            }
            return this.callbacks[callbackName](result, ...args);
        } catch (err) {
            //the catch might actually not be an error
            const result = this.extractResult(err);
            if (result?.error?.errorCode.startsWith("000")) {
                return this.callbacks[callbackName](result, ...args);
            }
            if (err.errorCode?.startsWith("202")) {
                this.dialog.add(NumberPopup, {
                    title: _t("Enter Pin Code"),
                    getPayload: (num) => {
                        this.enqueue(num, "registerPIN");
                    },
                });
                throw new Error(_t("Pin code required"));
            } else {
                throw new BlackboxError(err.errorCode, err.errorMessage);
            }
        }
    }

    async flush() {
        if (this.queue.length === 0 || this.waitForNextRequest) {
            return;
        }
        if (this.isFlushing) {
            await new Promise((resolve) => setTimeout(resolve, 2000)); // wait 2 seconds for the previous call to complete then reflush
            return this.flush();
        }
        this.isFlushing = true;

        const batch = this.queue.splice(0); // take all and clear queue
        localStorage.setItem(this.key, JSON.stringify(this.queue));
        let i = 0;
        try {
            const responses = await this.pushDataToBlackbox(
                batch.map((item) => [item.requestData, item.action])
            );
            // Assume responses[i] matches batch[i]
            for (const item of batch.values()) {
                if (this.callbacks[item.callbackName]) {
                    await this.callback(responses.result[i], item.callbackName, item.args);
                } else {
                    await this.callback(responses.result[i], "default_callback", item.args);
                }
                i++;
            }
        } catch (err) {
            if (
                !(err instanceof BlackboxError) ||
                !err.code ||
                !err.code.toString().startsWith("207")
            ) {
                for (const item of batch.slice(i)) {
                    if (item.force) {
                        break;
                    }
                    await this.enqueue(item.requestData, item.action, item.callbackName, item.args);
                }
                this.waitForNextRequest = true;
            }
            throw err;
        } finally {
            this.isFlushing = false;
        }
    }

    async pushDataToBlackbox(batch) {
        const fdm = this.hardwareProxy.deviceControllers.fiscal_data_module;

        return new Promise((resolve, reject) => {
            this.iotHttp.action(
                fdm.iotId,
                fdm.identifier,
                { action: "batchAction", high_level_message: batch },
                (message) => resolve(message),
                (message) => {
                    if (message.status.status == "error") {
                        reject(new BlackboxError(426));
                    }
                    reject(new BlackboxError(message.status.status));
                }
            );
        });
    }

    extractResult(data) {
        if (Array.isArray(data)) {
            return data[0];
        } else {
            return data;
        }
    }
}

registry.category("services").add("blackbox_queue_service", blackboxQueueService);
