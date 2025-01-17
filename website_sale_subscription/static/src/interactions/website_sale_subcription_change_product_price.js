import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsiteSaleSubscriptionChangeProductPrice extends Interaction {
    static selector = ".on_change_plan_table";
    dynamicContent = {
        ".plan_select": { "t-on-change": this._onPlanChange },
    };

    async _onPlanChange(e) {
        e.preventDefault();
        const selectedOption = e.target.selectedOptions[0];
        const { product, tablePrice: price, discountedPrice } = selectedOption.dataset;

        document.querySelector("#product_price").innerText = price;
        if (product) {
            const discountInfoElems = document.querySelectorAll(".discount_info");
            const discountPriceElem = document.querySelector("#discount_price");

            if (discountedPrice) {
                discountPriceElem.innerText = discountedPrice;
                discountInfoElems.forEach(elem => elem.classList.remove("d-none"));
            } else {
                discountInfoElems.forEach(elem => elem.classList.add("d-none"));
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_sale_subscription.change_product_price", WebsiteSaleSubscriptionChangeProductPrice);
