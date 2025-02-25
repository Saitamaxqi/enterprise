declare module "services" {
    import { iotLongpollingService } from "@iot/iot_longpolling";
    import { IotWebsocketService } from "@iot/iot_websocket_service";

    export interface Services {
        iot_longpolling: typeof iotLongpollingService;
        iot_websocket: typeof IotWebsocketService
    }
}
