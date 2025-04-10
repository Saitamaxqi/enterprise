import { MrpWorkorder } from "./mrp_workorder";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { useRef, useState } from "@odoo/owl";
import { MrpWorksheetDialog } from "../dialog/mrp_worksheet_dialog";

export class QualityCheck extends MrpWorkorder {
    static template = "mrp_workorder.QualityCheck";
    static components = {
        ...MrpWorkorder.components,
        FileUploader,
    };
    static props = {
        ...MrpWorkorder.props,
        registerProduction: { type: Function, optional: true },
        qtyProducing: { type: String, optional: true },
        isCurrent: Boolean,
    };

    setup() {
        this.action = useService("action");
        this.fileUploaderToggle = useRef("fileUploaderToggle");
        this.unique = useState({ epoch: Date.now() });
        this.dialog = useService("dialog");
    }

    get passed() {
        return this.check.quality_state === "pass";
    }

    get failed() {
        return this.check.quality_state === "fail";
    }

    get type() {
        return this.check.test_type;
    }

    get isComplete() {
        return this.passed || this.failed;
    }

    get showImage() {
        return this.passed && this.type === "picture";
    }

    get check() {
        return this.props.record.data;
    }

    get label() {
        return this.check.title || this.check.name;
    }

    get imageUrl() {
        const { resId } = this.props.record;
        return `/web/image/quality.check/${resId}/picture?unique=${this.unique.epoch}`;
    }

    get icon() {
        switch (this.type) {
            case "picture":
                return this.passed ? "mw" : "fa fa-camera";
            case "instructions":
                return this.passed ? "fa fa-undo" : "fa fa-check";
            case "print_label":
                return "fa fa-print";
            case "register_production":
                return "fa fa-plus";
            default:
                return "";
        }
    }

    get isActive() {
        return this.props.isCurrent;
    }

    get activeClass() {
        return "btn-primary";
    }

    get hasInstruction() {
        const { note, worksheet_document } = this.check;
        return (note && note.length) || worksheet_document;
    }

    get showQty() {
        const { lot_id } = this.check;
        if (this.type === "register_production" && this.passed) {
            return lot_id ? lot_id[1] : this.props.qtyProducing;
        }
        return false;
    }

    clicked() {
        switch (this.type) {
            case "instructions":
                if (this.isComplete) {
                    this.props.record.data.quality_state = "none";
                    return;
                } else {
                    return this.doActionAndNext("action_next");
                }
            case "print_label":
                return this.doActionAndNext("action_print");
            case "picture":
                return this.fileUploaderToggle.el.click();
            case "register_production":
                return this.isComplete
                    ? this.props.registerProduction(this.props.record)
                    : this.quickRegisterProduction();
        }
    }

    async quickRegisterProduction() {
        await this.doActionAndNext("action_register_production");
        return this.env.reload(this.props.record);
    }

    async onFileUploaded(info) {
        await this.props.record.update({ picture: info.data });
        await this.props.record.save({ reload: false });
        await this.doActionAndNext("action_next");
        this.unique.epoch = Date.now();
    }

    async doActionAndNext(action, stateToSet = "pass", actionParams = {}) {
        const { model, resModel, resId, data, _parentRecord } = this.props.record;
        const result = await model.orm.call(resModel, action, [resId]);
        if ("next_check_id" in result) {
            data.quality_state = stateToSet;
            _parentRecord.data.current_quality_check_id = [result.next_check_id];
            _parentRecord.model.notify();
        }
        if ("type" in result) {
            const params = {};
            if (result.type === "ir.actions.act_window") {
                params.onClose = () => this.env.reload(this.props.record);
                data.quality_state = "none";
            }
            if (result.type === "ir.actions.client") {
                result.params = { ...result.params, ...actionParams };
            }
            return this.action.doAction(result, params);
        }
    }

    async showWorksheet() {
        const { data, model, resId } = this.props.record;
        let worksheetData = false;
        if (data.worksheet_document) {
            const sheet = await model.orm.read("quality.check", [resId], ["worksheet_document"]);
            worksheetData = {
                resModel: "quality.check",
                resId,
                resField: "worksheet_document",
                value: sheet[0].worksheet_document,
                page: 1,
            };
        }
        this.dialog.add(MrpWorksheetDialog, {
            worksheetText: data.note,
            worksheetData,
        });
    }
}
