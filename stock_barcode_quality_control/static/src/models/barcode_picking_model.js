import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(BarcodePickingModel.prototype, {
    openQualityChecksMethod: "check_quality",

    get displayOnDemandQualityCheckButton() {
        const { record } = this;
        return record && record.id && !["draft", "done", "cancel"].includes(record.state);
    },

    get hasQualityChecksTodo() {
        return this.record && this.record.quality_check_todo;
    },

    async checkQuality() {
        await this.save();
        const res = await this.orm.call(this.resModel, this.openQualityChecksMethod, [
            [this.resId || this.record.id],
        ]);
        if (typeof res === "object" && res !== null) {
            return this.action.doAction(res, {
                onClose: () => this.trigger("refresh", { recordId: this.record.id }),
            });
        } else {
            this.notification.add(_t("All the quality checks have been done"));
        }
    },

    async onDemandQualityCheck() {
        await this.save();
        const res = await this.orm.call(this.resModel, "action_open_on_demand_quality_check", [
            [this.resId],
        ]);
        if (typeof res === "object" && res !== null) {
            return this.action.doAction(res, {
                onClose: () => this.trigger("refresh", { recordId: this.record.id }),
            });
        }
    },

    /* Function called on press of X in quality control */
    async _closeValidate(ev) {
        super._closeValidate(ev);
        // When going from draft to assign, need to reload JS to show quality check button
        if (this.record.state === "draft") {
            this.trigger("refresh", { recordId: this.record.id });
        }
    },
});
