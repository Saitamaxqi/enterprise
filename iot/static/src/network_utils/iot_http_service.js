import { registry } from "@web/core/registry";
import { post, formatEndpoint } from "@iot_base/network_utils/http";
import { uuid } from "@web/core/utils/strings";
import { IotWebsocket } from "@iot/network_utils/iot_websocket";
import { _t } from "@web/core/l10n/translation";
import { IotWebRtc } from "./iot_webrtc";
import { browser } from "@web/core/browser/browser";

/**
 * Class to handle IoT actions
 * The class is used to send actions to IoT devices and handle fallbacks
 * in case the request fails: it will try to send the request using
 * HTTP POST method and then using the websocket.
 */
export class IotAction {
    longpollingFailedTimestamp = null;
    connectionStatus = "local"; // local, online, offline
    /**
     *
     * @param {import("@iot_base/network_utils/longpolling").IotLongpolling} longpolling Longpolling service
     * @param {import("@iot/network_utils/iot_websocket").IotWebsocket} websocket Websocket service
     * @param {import("@iot/network_utils/iot_webrtc").IotWebRtc} webRtc WebRTC service
     * @param notification Notification service
     * @param orm ORM service
     */
    constructor(longpolling, websocket, webRtc, notification, orm) {
        this.longpolling = longpolling;
        this.websocket = websocket;
        this.webRtc = webRtc;
        this.notification = notification;
        this.orm = orm;
    }

    onFailure(_message, deviceIdentifier, _messageId) {
        this.notification.add(_t("Failed to reach the IoT Box for device: %s", deviceIdentifier), { type: "danger" });
    }

    async getIotBoxData(iotBoxId) {
        const [iotBoxData] = await this.orm.searchRead("iot.box", [["id", "=", iotBoxId]], ["ip", "identifier"]);
        return iotBoxData;
    }

    /**
     * Call for an action method on the IoT Box
     * @param iotBoxId IoT Box record ID
     * @param deviceIdentifier Identifier of the device connected to the IoT Box
     * @param data Data to send
     * @param {(message: Record<string, unknown>, deviceId: string) => void} onSuccess Callback to run when a message is received
     * @param {(message: Record<string, unknown>, deviceId: string) => void} onFailure Callback to run when the request fails
     * @returns {Promise<void>}
     */
    async action(
        iotBoxId,
        deviceIdentifier,
        data,
        onSuccess = () => {},
        onFailure = (...args) => this.onFailure(...args),
    ) {
        if (!["number", "string"].includes(typeof iotBoxId)) {
            iotBoxId = iotBoxId[0]; // iotBoxId is the ``Many2one`` field, we need the actual ID
        }

        const { ip, identifier } = await this.getIotBoxData(iotBoxId);

        // generate a unique request ID for this request (ensure the callback corresponds to the request)
        const actionId = uuid();

        // Define the connection types in the order of executions to try
        const connectionTypes = [
            async () => {
                await this.webRtc.onMessage(identifier, deviceIdentifier, actionId, onSuccess, onFailure);
                await this.webRtc.sendMessage(identifier, { device_identifier: deviceIdentifier, data }, actionId);
            },
            async () => {
                if (
                    this.longpollingFailedTimestamp &&
                    Date.now() - this.longpollingFailedTimestamp < 20 * 60 * 1000
                ) {
                    throw new Error("Longpolling is temporarily disabled due to a recent failure.");
                }
                this.longpolling.onMessage(ip, deviceIdentifier, onSuccess, onFailure, actionId);
                await this.longpolling.sendMessage(ip, { device_identifier: deviceIdentifier, data }, actionId, true);
                this.connectionStatus = "local";
            },
            async () => {
                const onFailureWithTimeout = (...args) => {
                    onFailure(...args);
                    this.connectionStatus = "offline";
                };
                this.websocket.onMessage(identifier, deviceIdentifier, onSuccess, onFailureWithTimeout, "operation_confirmation", actionId);
                await this.websocket.sendMessage(identifier, { device_identifiers: [deviceIdentifier], ...data }, actionId);
                this.connectionStatus = "online";
            },
        ];

        // Try to send the request using the connection types
        for (const connectionType of connectionTypes) {
            try {
                return await connectionType();
            } catch (e) {
                console.debug("IoT Box action: attempted method failed, attempting another protocol.", e);
                this.longpollingFailedTimestamp = Date.now();
            }
        }

        // If all the connection types failed, run the onFailure callback
        onFailure({ status: "disconnected" }, deviceIdentifier);
    }

    async testLongpollingAvailability(iotBoxIp) {
        try {
            await browser.fetch(formatEndpoint(iotBoxIp, '/iot_drivers/ping'));
            this.longpollingFailedTimestamp = null;
            this.connectionStatus = "local";
        } catch {
            this.longpollingFailedTimestamp = Date.now();
        }
    }
}


export const iotHttpService = {
    dependencies: ["notification", "orm", "bus_service", "iot_longpolling"],

    start(env, { notification, orm, bus_service, iot_longpolling }) {
        const iotWebsocket = new IotWebsocket({ bus_service, orm });
        const iotWebRtc = new IotWebRtc(bus_service, iotWebsocket);

        const longpolling = {
            sendMessage: iot_longpolling.sendMessage.bind(iot_longpolling),
            onMessage: iot_longpolling.onMessage.bind(iot_longpolling),
        };

        const websocket = {
            sendMessage: iotWebsocket.sendMessage.bind(iotWebsocket),
            onMessage: iotWebsocket.onMessage.bind(iotWebsocket),
        };

        const iotAction = new IotAction(
            iot_longpolling,
            iotWebsocket,
            iotWebRtc,
            notification,
            orm
        );
        const action = iotAction.action.bind(iotAction);
        const refresh = iotAction.testLongpollingAvailability.bind(iotAction);

        // Expose only those functions to the environment
        // status is a getter to have a reactive value
        return {
            post, action, longpolling, websocket, refresh, get status() {
                return iotAction.connectionStatus;
            }
        };
    },
};

registry.category("services").add("iot_http", iotHttpService);
