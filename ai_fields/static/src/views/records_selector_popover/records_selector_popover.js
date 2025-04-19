import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";

import { Component, useState } from "@odoo/owl";

export class RecordsSelectorPopover extends Component {
    static components = { MultiRecordSelector };
    static template = "aiFields.RecordsSelectorPopover";
    static props = {
        resModel: { type: String },
        close: { type: Function },
        domain: { type: Array, optional: true },
        validate: { type: Function },
    };

    setup() {
        this.state = useState({
            resIds: [],
        });
    }

    update(resIds) {
        this.state.resIds = resIds;
    }

    validate() {
        this.props.validate(this.state.resIds);
        this.props.close();
    }
}
