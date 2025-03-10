import { Component, onWillUnmount } from "@odoo/owl";
import { registries, stores } from "@spreadsheet/o_spreadsheet/o_spreadsheet";
import { usePopover } from "@web/core/popover/popover_hook";

const { useStore, ClientFocusStore } = stores;
const { topbarComponentRegistry } = registries;

class SpreadsheetUsersTooltip extends Component {
    static template = "spreadsheet_edition.SpreadsheetUsersTooltip";
    static props = {
        users: Object,
        onMouseLeave: Function,
        onMouseEnter: Function,
        onClick: Function,
        close: { optional: true, type: Function },
    };
}

export class CollaborativeStatus extends Component {
    static template = "spreadsheet_edition.CollaborativeStatus";
    static props = {};

    setup() {
        super.setup();
        this.popover = usePopover(SpreadsheetUsersTooltip, { position: "bottom" });
        this.clientFocusStore = useStore(ClientFocusStore);

        onWillUnmount(() => {
            if (this.timeoutId) {
                clearTimeout(this.timeoutId);
            }
        });
    }

    get isSynced() {
        return this.env.model.getters.isFullySynchronized();
    }

    get connectedUsers() {
        const connectedUsers = [];
        for (const client of this.env.model.getters.getConnectedClients()) {
            if (!connectedUsers.some((user) => user.id === client.userId)) {
                connectedUsers.push({
                    id: client.userId,
                    name: client.name,
                    clientId: client.id,
                    color: client.color,
                });
            }
        }
        return connectedUsers;
    }

    get tooltipInfo() {
        return this.connectedUsers.map((/**@type User*/ user) => ({
            name: user.name,
            avatar: `/web/image?model=res.users&field=avatar_128&id=${user.id}`,
            id: user.id,
            clientId: user.clientId,
            color: user.color,
        }));
    }

    jumpToUser(user) {
        this.clientFocusStore.jumpToClient(user.clientId);
    }

    openPopover(ev) {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
        } else if (this.connectedUsers.length > 1) {
            this.popover.open(ev.currentTarget, {
                users: this.tooltipInfo,
                onMouseEnter: this.openPopover.bind(this),
                onMouseLeave: this.closePopover.bind(this),
                onClick: this.jumpToUser.bind(this),
            });
            this.clientFocusStore.showClientTag();
        }
    }

    closePopover(ev) {
        this.timeoutId = setTimeout(() => this.cleanupPopover(), 300);
    }

    cleanupPopover() {
        this.timeoutId = undefined;
        this.popover.close();
        this.clientFocusStore.hideClientTag();
    }
}

topbarComponentRegistry.add("collaborative_status", {
    component: CollaborativeStatus,
    sequence: 10,
});
