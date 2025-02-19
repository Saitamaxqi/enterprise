import { Component, onWillRender} from "@odoo/owl";


export class StatusBubble extends Component {
    static template = "hr_payroll.StatusBubble";
    static props = {
        selection: {type: Array},
        activeOption: {type: String},
        warningCount: {type: Number, optional: true},
        errorCount: {type: Number, optional: true},
        removeOptions: {type: Array, optional: true},
    };
    static defaultProps = {
        warningCount: 0,
        errorCount: 0,
        removeOptions: [],
    };

    setup() {
        onWillRender(() => {
            if (this.props.removeOptions.length) {
                this.props.selection = this.props.selection.filter(o => !this.props.removeOptions.includes(o[0]));
            }
        });
    }

    get activeIndex() {
        return this.props.selection.findIndex(([key,]) => key === this.props.activeOption);
    }
}