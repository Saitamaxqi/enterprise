import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { Many2One } from "./many2one/many2one";

export class HostPage extends Component {
    static template = "frontdesk.HostPage";
    static components = { Many2One };
    static props = {
        setHostData: Function,
        showScreen: Function,
        stationId: Number,
        token: String,
    };

    setup() {
        this.state = useState({
            hostName: "",
        });
    }

    /**
     * This method is triggered when the confirm button is clicked.
     * It sets the host data and displays the RegisterPage component.
     *
     * @private
     */
    _onConfirm() {
        this.props.setHostData(this.host);
        this.props.showScreen("RegisterPage");
    }

    /**
     * @param {object | null} host
     */
    selectedHost(host) {
        this.host = host;
        this.state.hostName = host?.display_name ?? "";
    }
}

registry.category("frontdesk_screens").add("HostPage", HostPage);
