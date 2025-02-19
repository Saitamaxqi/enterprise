import { getModifier, ViewCompiler } from "@web/views/view_compiler";
import { append, createElement } from "@web/core/utils/xml";


export class PayRunCompiler extends ViewCompiler {
    setup() {
        /** @type {Record<string, Element[]>} */
        this.compilers.push(
            {selector: "div[name='button_box']", fn: this.compileButtonBox},
        );
    }

    getVisibleExpr(child, params) {
        const invisible = getModifier(child, "invisible");
        if (!params.compileInvisibleNodes && (invisible === "True" || invisible === "1")) {
            return false;
        }
        if (!invisible || invisible === "False" || invisible === "0") {
            return "true";
        } else if (invisible === "True" || invisible === "1") {
            return "false";
        } else {
            return `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                invisible
            )},__comp__.props.record.evalContextWithVirtualIds)`;
        }
    }

    //-----------------------------------------------------------------------------
    // Compilers
    //-----------------------------------------------------------------------------

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileButtonBox(el, params) {
        if (!el.children.length) {
            return this.compileGenericNode(el, params);
        }

        el.classList.remove("oe_button_box");
        const buttonBox = createElement("PayRunButtonBox");
        buttonBox.setAttribute("t-if", "!__comp__.env.inDialog");
        let slotId = 0;
        for (const child of el.children) {
            // Action buttons
            if (child.tagName === "action" || child.children.tagName === "action") {
                for (const action of child.children) {
                    const isVisibleExpr = this.getVisibleExpr(action, params);
                    const mainSlot = createElement("t", {
                        "t-set-slot": `slot_${slotId++}`,
                        isVisible: isVisibleExpr,
                        isSmartButton: "false",
                    });
                    if (["button", "field"].includes(action.tagName) || action.children.tagName === "button") {
                        action.classList.add(
                            "border-0",
                            "flex-grow-1",
                            "oe_stat_button"
                        );
                    }
                    append(mainSlot, this.compileNode(action, params, false));
                    append(buttonBox, mainSlot);
                }
            } else {
                // Smart Buttons
                const isVisibleExpr = this.getVisibleExpr(child, params);
                const mainSlot = createElement("t", {
                    "t-set-slot": `slot_${slotId++}`,
                    isVisible: isVisibleExpr,
                    isSmartButton: "true",
                });
                if (child.tagName === "button" || child.children.tagName === "button") {
                    child.classList.add(
                        "oe_stat_button",
                        "btn",
                        "btn-outline-secondary",
                        "border-0",
                        "flex-grow-1",
                    );
                }
                if (child.tagName === "field") {
                    child.classList.add("d-inline-block", "mb-0", "z-0");
                }
                append(mainSlot, this.compileNode(child, params, false));
                append(buttonBox, mainSlot);
            }
        }
        return buttonBox.children.length ? buttonBox : "";
    }
}
