import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Component } from "@odoo/owl";

export class Many2One extends Component {
    static template = "frontdesk.Many2One";
    static components = { AutoComplete };
    static props = {
        stationId: Number,
        token: String,
        update: Function,
        value: String,
    };

    async loadOptionsSource(request) {
        if (this.lastProm) {
            this.lastProm.abort(false);
        }
        if (!request) {
            return []; // Do not fetch data if input is empty
        }
        this.lastProm = this.search(request);
        const records = await this.lastProm;
        return records.map(([id, display_name]) => ({
            data: { id },
            label: display_name.split("\n")[0],
            onSelect: () => this.props.update({ id, display_name }),
        }));
    }

    /* This method triggers when a user types in the input field */
    search(name) {
        return rpc(`/frontdesk/${this.props.stationId}/${this.props.token}/get_hosts`, {
            name: name,
        });
    }

    get sources() {
        return [this.optionsSource];
    }

    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
            optionSlot: "option",
        };
    }
}
