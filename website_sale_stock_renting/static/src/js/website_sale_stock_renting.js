import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'change input[type="hidden"][name="product_id"]': "_onVariantChanged",
    }),

    /**
     * Override of `_updateRootProduct` to trigger a change_product_id event on the daterange
     * pickers.
     *
     * @override
     * @private
     * @param {HTMLFormElement} form - The form in which the product is.
     *
     * @returns {void}
     */
    _updateRootProduct(form) {
        this._super(...arguments);
        const dateRangeRenting = this.el.querySelector('.o_website_sale_daterange_picker');
        dateRangeRenting?.dispatchEvent(new CustomEvent(
            'change_product_id', { detail: { productId: this.rootProduct.productId }}
        ));
    },

    /**
     * Override to trigger a change_product_id event for variant availabilities check.
     *
     * @override
     */
    _onVariantChanged() {
        const productIdElement = this.el.querySelector('input[type="hidden"][name="product_id"]');
        const dateRangeRenting = this.el.querySelector('.o_website_sale_daterange_picker');
        if (dateRangeRenting && productIdElement) {
            dateRangeRenting.dispatchEvent(new CustomEvent(
                'change_product_id', { detail: { productId: parseInt(productIdElement.value) }}
            ));
        }
    },

    /**
     * Override to update the renting stock availabilities.
     *
     * @override
     */
    _onRentingConstraintsChanged(event) {
        this._super.apply(this, arguments);
        const info = event.detail;
        if (info.rentingAvailabilities) {
            this.rentingAvailabilities = info.rentingAvailabilities;
        }
        if (info.preparationTime !== undefined) {
            this.preparationTime = info.preparationTime;
        }
    },
});
