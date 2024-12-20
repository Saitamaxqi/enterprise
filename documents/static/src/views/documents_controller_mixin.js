import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { useSubEnv } from "@odoo/owl";

export const DocumentsControllerMixin = (component) =>
    class extends component {
        setup() {
            super.setup(...arguments);
            this.searchBarToggler = useSearchBarToggler();
            useSubEnv({
                searchBarToggler: this.searchBarToggler,
            });
        }

        get modelParams() {
            const modelParams = super.modelParams;
            modelParams.multiEdit = true;
            return modelParams;
        }
    };
