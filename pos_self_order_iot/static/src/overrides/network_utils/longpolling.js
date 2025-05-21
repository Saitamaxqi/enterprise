import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { IoTLongpolling } from "@iot_base/network_utils/longpolling";
import { formatEndpoint } from "@iot_base/network_utils/http";
import { rpc } from "@web/core/network/rpc";

patch(IoTLongpolling.prototype, {
    async _rpcIoT(
        iot_box_ip,
        route,
        payload,
        timeout = undefined,
        fallback = false,
        headers = undefined
    ) {
        const url = formatEndpoint(iot_box_ip, route);
        const access_token = new URLSearchParams(browser.location.search).get("access_token");
        const { signature } = await rpc("/pos-self-order/sign-iot-message", {
            access_token,
            iot_box_ip,
            url,
            payload,
        });

        return super._rpcIoT(iot_box_ip, route, payload, timeout, fallback, {
            ...headers,
            Authorization: signature,
        });
    },
});
