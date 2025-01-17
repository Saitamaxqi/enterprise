import VariantMixin from "@website_sale/js/sale_variant_mixin";
import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({

    /**
     * Override of `_updateRootProduct` to add the subscription plan id to the rootProduct for
     * subscription products.
     *
     * @override
     * @private
     * @param {HTMLFormElement} form - The form in which the product is.
     *
     * @returns {void}
     */
    _updateRootProduct(form) {
        this._super(...arguments);
        const selected_plan =
            form.querySelector('.product_price .plan_select')?.value
            ?? form.querySelector('#add_to_cart')?.dataset.subscriptionPlanId;
        if (selected_plan) {
            const allow_one_time_sale = form.querySelector('.allow_one_time_sale')?.checked;
            const plan_id = allow_one_time_sale ? null : parseInt(selected_plan);
            Object.assign(this.rootProduct, {
                plan_id: plan_id,
                allow_one_time_sale: allow_one_time_sale,
            });
        }
    },

    /**
     * @override
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickAdd(ev) {
        const form = ev.currentTarget.closest('form');
        const planSelects = form.querySelectorAll('.plan_select');
        for (const select of planSelects) {
            for (const option of select.options) {
                option.disabled = !option.selected;
            }
        }
        this._handleAddSubscriptionProduct(form);
        return this._super(...arguments);
    },

    _handleAddSubscriptionProduct(form) {
        const regularDeliveryCheckbox = form.querySelector('#regular_delivery');
        const oneTimeSaleCheckbox = form.querySelector('#allow_one_time_sale');

        const regularDeliverySection = form.querySelector('.regular-delivery');
        const oneTimeSaleSection = form.querySelector('.one-time-sale');

        const isRegularChecked = regularDeliveryCheckbox?.checked;
        const isOneTimeChecked = oneTimeSaleCheckbox?.checked;

        if (regularDeliverySection) {
            regularDeliverySection.style.display = isRegularChecked ? '' : 'none';
        }

        if (oneTimeSaleSection) {
            oneTimeSaleSection.style.display = (isOneTimeChecked && !isRegularChecked) ? '' : 'none';
        }
    },

    /**
     * Update the renting text when the combination change.
     * @override
     */
    _onChangeCombination: function (){
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationSubscription.apply(this, arguments);
    },
});
