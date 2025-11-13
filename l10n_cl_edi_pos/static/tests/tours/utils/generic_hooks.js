import { patch } from "@web/core/utils/patch";
import { GenericHooks } from "@point_of_sale/../tests/pos/tours/utils/generic_hooks";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as TextInputPopup from "@point_of_sale/../tests/generic_helpers/text_input_popup_util";

patch(GenericHooks, {
    afterValidateHook(...args) {
        const params = new URLSearchParams(document.location.search);
        const company_name = params.get("company_name");
        if (company_name == "Company BR") {
            return [TextInputPopup.inputText("043123456"), Dialog.confirm()];
        } else {
            return super.afterValidateHook(...args);
        }
    },
});
