import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    /**
     * @override
     */
    async setup() {
        await super.setup(...arguments);
        this.delivery_order_count = { urbanpiper: {} };
        this.delivery_providers = [];
        this.total_new_order = 0;
        const storedToggleState =
            JSON.parse(localStorage.getItem("toggle_state_" + this.config.id)) || {};
        const toggleState = {};
        this.config.urbanpiper_delivery_provider_ids.forEach((provider) => {
            toggleState[provider.technical_name] =
                provider.technical_name in storedToggleState
                    ? storedToggleState[provider.technical_name]
                    : true;
        });
        localStorage.setItem("toggle_state_" + this.config.id, JSON.stringify(toggleState));
        this.toggleState = {
            enableProviders:
                JSON.parse(localStorage.getItem("toggle_state_" + this.config.id)) || {},
        };
        if (this.config.module_pos_urban_piper && this.config.urbanpiper_store_identifier) {
            await this._fetchUrbanpiperOrderCount(false);
            const storageKey = "toggle_state_" + this.config.id;
            const storedToggleState = JSON.parse(localStorage.getItem(storageKey)) || {};
            this.config.urbanpiper_delivery_provider_ids.forEach(async (provider) => {
                const isEnabled = storedToggleState[provider.technical_name] ?? true; // default to true

                const data = {
                    status: true,
                    platform: provider.technical_name,
                    action: isEnabled ? "enable" : "disable",
                };

                await this._fetchStoreAction(data);
            });
        }
    },

    async updateStoreStatus(status = false, providerName = false) {
        if (this.config.module_pos_urban_piper && this.config.urbanpiper_store_identifier) {
            await this.data.call("pos.config", "update_store_status", [this.config.id, status], {
                context: {
                    providerName: providerName,
                },
            });
            if (status) {
                localStorage.setItem(
                    "toggle_state_" + this.config.id,
                    JSON.stringify(this.toggleState.enableProviders)
                );
            }
        }
    },

    async closePos() {
        await this.updateStoreStatus();
        localStorage.removeItem("toggle_state_" + this.config.id);
        return super.closePos();
    },

    async getServerOrders() {
        if (this.config.module_pos_urban_piper && this.config.urbanpiper_store_identifier) {
            return await this.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                [
                    "delivery_provider_id",
                    "in",
                    this.config.urbanpiper_delivery_provider_ids.map((provider) => provider.id),
                ],
            ]);
        } else {
            return await super.getServerOrders(...arguments);
        }
    },
    _fetchStoreAction(data) {
        const params = {
            type: "success",
            sticky: false,
        };
        let message = "";
        // Initialize or get existing toggle state from localStorage
        const storageKey = "toggle_state_" + this.config.id;
        const toggleState = JSON.parse(localStorage.getItem(storageKey)) || {};
        if (data.status) {
            toggleState[data.platform] = data.action === "enable";
        }
        localStorage.setItem(storageKey, JSON.stringify(toggleState));

        this.toggleState = {
            enableProviders: toggleState,
        };
        // Prepare notification message
        if (!data.status) {
            params.type = "danger";
            message = _t("Error occurred while updating " + data.platform + " status.");
        } else if (data.action === "enable") {
            message = _t(this.config.name + " is online on " + data.platform + ".");
        } else if (data.action === "disable") {
            message = _t(this.config.name + " is offline on " + data.platform + ".");
        }

        if (message) {
            this.notification.add(message, params);
        }
    },
    get notificationOptions() {
        return {
            type: "success",
            sticky: false,
            buttons: [
                {
                    name: _t("Review Orders"),
                    onClick: () => {
                        const stateOverride = {
                            search: {
                                fieldName: "DELIVERYPROVIDER",
                                searchTerm:
                                    this.deliveryOrderNotification?.delivery_provider_id.name,
                            },
                            filter: "ACTIVE_ORDERS",
                        };
                        this.setOrder(this.deliveryOrderNotification);
                        if (this.router.state.current == "TicketScreen") {
                            const next = this.defaultPage;
                            this.navigate(next.page, next.params);
                            setTimeout(() => {
                                this.navigate("TicketScreen", { stateOverride });
                                this.env.services.ui.unblock();
                            }, 300);
                            return;
                        }
                        return this.navigate("TicketScreen", { stateOverride });
                    },
                },
            ],
        };
    },

    async _fetchUrbanpiperOrderCount(order_id) {
        try {
            await this.getServerOrders();
        } catch {
            this.notification.add(_t("Order does not load from server"), {
                type: "warning",
                sticky: false,
            });
        }
        const response = await this.data.call(
            "pos.config",
            "get_delivery_data",
            [this.config.id],
            {}
        );
        this.delivery_order_count = response.delivery_order_count;
        this.delivery_providers = response.delivery_providers;
        this.total_new_order = response.total_new_order;
        const deliveryOrder = order_id ? this.models["pos.order"].get(order_id) : false;
        if (!deliveryOrder) {
            return;
        }
        if (deliveryOrder.delivery_status === "acknowledged" && deliveryOrder.state != "cancel") {
            if (!deliveryOrder.isFutureOrder()) {
                await this.sendOrderInPreparationUpdateLastChange(deliveryOrder);
            }
        } else if (deliveryOrder.delivery_status === "placed") {
            this.sound.play("notification");
            this.deliveryOrderNotification = deliveryOrder;
            this.notification.add(_t("New online order received."), this.notificationOptions);
        } else if (deliveryOrder.delivery_status === "food_ready") {
            deliveryOrder.uiState.locked = true;
        }
    },

    /**
     * @override
     */
    addOrderIfEmpty(forceEmpty) {
        if (
            !this.getOrder() ||
            (this.getOrder().delivery_identifier && this.getOrder().state == "paid")
        ) {
            return this.addNewOrder();
        }
        return super.addOrderIfEmpty(...arguments);
    },

    async goToBack() {
        this.addPendingOrder([this.getOrder().id]);
        await this.syncAllOrders();
        this.navigate("TicketScreen");
        if (this.getOrder().delivery_status !== "placed") {
            try {
                await this.sendOrderInPreparation(this.getOrder());
            } catch {
                this.notification.add(_t("Error to send in preparation display."), {
                    type: "warning",
                    sticky: false,
                });
            }
        }
    },

    getOrderData(order, reprint) {
        let orderData = super.getOrderData(order, reprint);
        if (order.delivery_provider_id) {
            orderData = {
                ...orderData,
                delivery_provider_id: order.delivery_provider_id,
                order_otp: JSON.parse(order.delivery_json)?.order?.details?.ext_platforms?.[0].id,
                prep_time: order.prep_time,
            };
        }
        return orderData;
    },
});
