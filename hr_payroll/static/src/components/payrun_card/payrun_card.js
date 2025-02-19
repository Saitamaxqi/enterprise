import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillRender } from "@odoo/owl";
import { formatMonetary } from "@web/views/fields/formatters";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useDeleteRecords } from "@web/views/view_hook";
import { _t } from "@web/core/l10n/translation";
import { PayRunActionButtonBox, PayRunButtonBox } from "./payrun_button_box";
import { ViewButton } from "@web/views/view_button/view_button";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";
import { download } from "@web/core/network/download";
import { isBinarySize } from "@web/core/utils/binary";
import { StatusBubble } from "../status_bubble/status_bubble";


export class PayRunCard extends Component {
    static template = "hr_payroll.PayRunCard";
    static props = {
        ...standardWidgetProps,
        archInfo: { type: Object },
    };
    static components = {
        Dropdown,
        DropdownItem,
        PayRunButtonBox,
        PayRunActionButtonBox,
        ViewButton,
        Field,
        Widget,
        StatusBubble,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.deleteRecordsWithConfirmation = useDeleteRecords(this.props.record.model);
        this.state = useState({});
        this.formatMonetary = formatMonetary;
        this.evaluateBooleanExpr = evaluateBooleanExpr;

        onWillRender(() => {
            this.state.data = this.props.record.data;
        });
    }

    get payrun() {
        return this.state.data;
    }

    get dateStart() {
        return luxon.DateTime.fromISO(this.state.data.date_start, {
            locale: this.env.model.config.context.lang.replace("_", "-")
        }).toLocaleString(luxon.DateTime.DATE_MED);
    }

    get dateEnd() {
        return luxon.DateTime.fromISO(this.state.data.date_end, {
            locale: this.env.model.config.context.lang.replace("_", "-")
        }).toLocaleString(luxon.DateTime.DATE_MED);
    }

    async downloadReport() {
        await download({
            data: {
                model: this.props.record.resModel,
                id: this.props.record.resId,
                field: "payment_report",
                filename_field: "payment_report_filename",
                filename: this.state.data.payment_report_filename || "",
                download: true,
                data: isBinarySize(this.state.data.payment_report)
                    ? null
                    : this.state.data.payment_report,
            },
            url: "/web/content",
        });
    }

    async payrunAction(method){
        await this.orm.call("hr.payslip.run", method, [this.props.record.resId]);
        this.env.model.root.load();
        this.props.record.load();
    }

    get deleteConfirmationDialogProps() {
        return {
            body: _t("Do you really want to delete %s Pay Run?", this.props.record.data.name),
            confirm: async () => {
                await this.props.record.delete();
                if (!this.props.record.resId && this.env.model.config.resModel === "hr.payslip") {
                    this.env.config.historyBack();
                } else {
                    await this.action.doAction({
                        "type": "ir.actions.client",
                        "tag": "soft_reload",
                    });
                }
            },
        };
    }

    onDelete() {
        this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps, [this.props.record]);
    }

    async onChange(ev){
        await this.props.record.update({name: ev.target.value});
        await this.props.record.save();
    }
}