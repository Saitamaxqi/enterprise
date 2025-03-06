import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FloatField } from "@web/views/fields/float/float_field";

export class MrpQuantityDialog extends ConfirmationDialog {
    static template = "mrp_workorder.MrpQuantityDialog";
    static props = {
        ...ConfirmationDialog.props,
        record: Object,
    };
    static components = {
        ...ConfirmationDialog.components,
        FloatField,
    };

    async apply() {
        await this.props.record.save({ reload: false });
        return this._confirm();
    }

    remove() {
        this.props.record.delete();
        return this._confirm();
    }

    _dismiss() {
        this.props.record.discard();
    }
}
