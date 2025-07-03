import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formatPercentage, formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class CapTable extends Component {
    static template = "equity.CapTable";
    static props = { ...standardActionServiceProps };
    static components = { ControlPanel };

    setup() {
        super.setup();

        this.orm = useService("orm");
        this.action = useService("action");
        this.partnerHolderData = useState({});
        this.partnerClassesIds = useState({});
        this.partnerData = useState({});
        this.classData = useState({});

        onWillStart(async () => {
            const res = await this.orm.call("equity.cap.table", "get_cap_table_data", [(this.props.action.context?.active_ids || [])]);
            this.partnerHolderData = res["partner_holder_data"];
            this.partnerClassesIds = res["partner_classes_ids"];
            this.partnerData = res["partner_data"];
            this.classData = res["class_data"];
        });
    }

    createTransaction() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "equity.transaction",
            target: "current",
            views: [[false, "form"]],
        });
    }

    async sendToPartner(partnerId) {
        const action = await this.orm.call("res.partner", "action_partner_send", [parseInt(partnerId)]);
        this.action.doAction(action);
    }

    openRecord(resModel, resId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: parseInt(resId),
            views: [[false, "form"]],
            target: "current",
        });
    }

    openTransactions(partnerId, holderId, classId, type, totalCell = false) {
        const today = new Date().toISOString().split('T')[0];
        const domain = [["partner_id", "=", parseInt(partnerId)], "|", ["transaction_type", "!=", "option"], ["expiration_date", ">=", today]];

        if (holderId && !isNaN(holderId)) {
            holderId = parseInt(holderId);
            domain.push("|", ["subscriber_id", "=", holderId], ["seller_id", "=", holderId]);
        }
        else if (!totalCell) {
            domain.push(["subscriber_id", "=", false]);
        }
        if (classId && !isNaN(classId)) {
            domain.push(["share_class_id", "=", parseInt(classId)]);
        }
        switch (type) {
            case "shares": domain.push(["transaction_type", "in", ["share", "sale"]]); break;
            case "options": domain.push(["transaction_type", "in", ["option"]]); break;
        }

        this.action.doAction({
            name: _t("Transactions"),
            type: "ir.actions.act_window",
            res_model: "equity.transaction",
            domain,
            target: "current",
            views: [[false, "list"], [false, "form"]],
        });
    }

    getHeadersLength(partnerId) {
        return this.partnerClassesIds[partnerId].length + 6;
    }

    getHeaders(partnerId) {
        return [
            { label: _t("Holders") },
            ...this.partnerClassesIds[partnerId].map(classId => ({
                label: this.classData[classId]["display_name"],
                onClick: () => this.openRecord("equity.share.class", classId),
            })),
            { label: _t("Total") },
            { label: _t("Ownership") },
            { label: _t("Voting Rights") },
            { label: _t("Fully Diluted") },
            { label: _t("Valuation") },
        ];
    }

    getSecurities(partnerId, holderId, classId, type) {
        let res = 0;
        const partnerHolderData = this.partnerHolderData[partnerId];
        for (const innerHolderId of Object.keys(partnerHolderData)) {
            if (!holderId || innerHolderId == holderId) {
                const innerHolderRow = partnerHolderData[innerHolderId]["classes"];
                for (const innerClassId of Object.keys(innerHolderRow)) {
                    if (!classId || innerClassId == classId) {
                        res += innerHolderRow[innerClassId][type];
                    }
                }
            }
        }
        return res;
    }

    getOwnership(partnerId, holderId, type) {
        if (type == "options") {
            return "";
        }

        let res = 0;
        const partnerHolderData = this.partnerHolderData[partnerId];
        for (const innerHolderId of Object.keys(partnerHolderData)) {
            if (!holderId || innerHolderId == holderId) {
                res += partnerHolderData[innerHolderId]["ownership"];
            }
        }
        return formatPercentage(res);
    }

    getVotingRights(partnerId, holderId, type) {
        if (type == "options") {
            return "";
        }

        let res = 0;
        const partnerHolderData = this.partnerHolderData[partnerId];
        for (const innerHolderId of Object.keys(partnerHolderData)) {
            if (!holderId || innerHolderId == holderId) {
                res += partnerHolderData[innerHolderId]["voting_rights"];
            }
        }
        return formatPercentage(res);
    }

    getDilution(partnerId, holderId, type) {
        let res = 0;
        const partnerHolderData = this.partnerHolderData[partnerId];
        for (const innerHolderId of Object.keys(partnerHolderData)) {
            if (!holderId || innerHolderId == holderId) {
                res += partnerHolderData[innerHolderId]["dilution"][type];
            }
        }
        return formatPercentage(res);
    }

    getValuation(partnerId, holderId, type) {
        let res = 0;
        const partnerHolderData = this.partnerHolderData[partnerId];
        for (const innerHolderId of Object.keys(partnerHolderData)) {
            if (!holderId || innerHolderId == holderId) {
                res += partnerHolderData[innerHolderId]["valuation"][type];
            }
        }
        return formatMonetary(res, { currencyId: this.partnerData[partnerId]["equity_currency_id"] });
    }

    getRow(partnerId, holderId, type, totalLabel = false) {
        const totalSecurities = this.getSecurities(partnerId, holderId, null, type);

        if (!totalSecurities && !totalLabel) {
            return null;
        }

        return [
            {
                partnerId: (!isNaN(holderId) && holderId),
                label: totalLabel || (!isNaN(holderId) && this.partnerData[holderId]["display_name"]) || _t("Unassigned"),
                onClick: holderId && !isNaN(holderId) ? (() => this.openRecord("res.partner", holderId)) : null,
            },
            ...this.partnerClassesIds[partnerId].map(classId => ({
                label: this.getSecurities(partnerId, holderId, classId, type) || "",
                onClick: () => this.openTransactions(partnerId, holderId, classId, type, Boolean(totalLabel)),
            })),
            { label: totalSecurities, onClick: () => this.openTransactions(partnerId, holderId, null, type, Boolean(totalLabel)) },
            { label: this.getOwnership(partnerId, holderId, type) },
            { label: this.getVotingRights(partnerId, holderId, type) },
            { label: this.getDilution(partnerId, holderId, type) },
            { label: this.getValuation(partnerId, holderId, type) },
        ];
    }
}

registry.category("actions").add("equity.CapTable", CapTable);
