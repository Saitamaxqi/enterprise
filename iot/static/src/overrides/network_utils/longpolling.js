import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";
import { IoTLongpolling } from "@iot_base/network_utils/longpolling";
import { formatEndpoint } from "@iot_base/network_utils/http";
import { uniqueId } from "@web/core/utils/functions";
import { uuid } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

patch(IoTLongpolling.prototype, {
    setup() {
        super.setup(...arguments);
        // The subscription notification pops up too often, so we debounce it to at most once every 5 minutes
        this.subscriptionWarningDebounced = debounce(
            () => this.subscriptionWarning(),
            5 * 60 * 1000,
            { leading: true, trailing: false }
        );
    },

    subscriptionWarning() {
        this.notification.add(
            _t("Please contact your account manager to take advantage of your IoT Box's full potential."),
            { title: _t("No subscription linked to your IoT Box."), type: "warning" }
        );
    },

    /**
     * Send a message to the IoT Box (action route)
     * @param iotBoxIp IP Address of the IoT Box
     * @param message Data to send to the device
     * @param messageId Unique identifier for the message
     * @param fallback If longpolling has a fallback option (e.g. websocket), do not display errors to the user
     * @returns {Promise<*>} messageId if the request didn't throw an error
     */
    async sendMessage(iotBoxIp, message, messageId = null, fallback = false) {
        messageId ??= uuid();
        await this._rpcIoT(iotBoxIp, '/hw_drivers/action', { session_id: messageId, ...message }, undefined, fallback);

        return messageId;
    },

    /**
     * Listen for messages from the IoT Box (polling the IoT Box)
     * @param iotBoxIp IP Address of the IoT Box
     * @param iotDeviceIdentifier Identifier of the device connected to the IoT Box
     * @param onSuccess Callback to run when a successful response is received (can return ``message``, ``deviceIdentifier``, and ``messageId``)
     * @param onFailure Callback to run when the request fails (can return ``deviceIdentifier`` and ``messageId``)
     */
    onMessage(
        iotBoxIp,
        iotDeviceIdentifier,
        onSuccess = (_message, _deviceIdentifier, _messageId) => {},
        onFailure = (_message, _deviceIdentifier, _messageId) => {},
    ) {
        const listenerId = uniqueId('listener-');
        const listenerCallback = (message) => {
            this.removeListener(iotBoxIp, iotDeviceIdentifier, listenerId);
            if (message.status === "success" || message.status?.status === "connected") { // 'connected' is the serial driver success status
                onSuccess(message, iotDeviceIdentifier, listenerId);
            } else {
                onFailure(message, iotDeviceIdentifier, listenerId);
            }
        }
        return this.addListener(iotBoxIp, [ iotDeviceIdentifier ], listenerId, listenerCallback, true);
    },

    async _rpcIoT(iot_ip, route, params, timeout = undefined, fallback = false, headers = undefined) {
        // Sign the request
        const requestUrl = formatEndpoint(iot_ip, route);
        const { signature, isSslCertificateValid } =
            await this.orm.call("iot.box", "sign_communication", [iot_ip, requestUrl, params]);

        if (!isSslCertificateValid) {
            this.subscriptionWarningDebounced();
        }

        return super._rpcIoT(iot_ip, route, params, timeout, fallback, { ...headers, "Authorization": signature });
    }
});
