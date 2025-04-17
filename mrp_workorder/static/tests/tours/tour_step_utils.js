/* @odoo-module */

export const stepUtils = {
    addWorkcenterToDisplay(workcenterName) {
        return [
            {
                trigger: `.o_mrp_workcenter_dialog .btn:contains(${workcenterName}):not(.active)`,
                run: "click",
            },
            { trigger: `.o_mrp_workcenter_dialog .btn:contains(${workcenterName}).active` },
        ];
    },
    enterPIN(code) {
        const steps = [];
        for (const c of code) {
            steps.push({
                trigger: `.popup-numpad button:contains(${c})`,
                run: "click",
            });
        }
        steps.push({
            trigger: `.popup-input:contains('${"".padEnd(code.length, "•")}')`,
        });
        steps.push({
            trigger: "footer .btn-primary",
            run: "click",
        });
        return steps;
    },
    openEmployeesList() {
        return [
            { trigger: "button.o_edit_operators", run: "click" },
            { trigger: ".modal-body .o_mrp_operatos_dialog" },
        ];
    },
};
