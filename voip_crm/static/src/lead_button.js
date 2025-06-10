import { Call } from "@voip/core/call_model";
import { Persona } from "@mail/core/common/persona_model";

import { Component } from "@odoo/owl";

import { ActionButton } from "@voip/softphone/action_button";

import { useService } from "@web/core/utils/hooks";

export class LeadButton extends Component {
    static components = { ActionButton };
    static props = {
        contact: { type: Persona, optional: true },
        call: { type: Call, optional: true },
    };
    static template = "voip_crm.LeadButton";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.voip = useService("voip");
    }

    get partner() {
        if (this.props.call) {
            return this.props.call.partner_id;
        }
        return this.props.contact;
    }

    get opportunityCount() {
        return this.partner?.opportunity_count || 0;
    }

    get shouldShowLeadButton() {
        return this.voip.softphone.shouldShowLeadButton;
    }

    /** @param {ev} MouseEvent */
    async onClickLead(ev) {
        const action = await this.orm.call("res.partner", "get_view_opportunities_action", [
            this.partner?.id,
            this.props.call?.phone_number,
        ]);
        action.target = this.ui.isSmall ? "new" : "current";
        this.action.doAction(action);
    }
}
