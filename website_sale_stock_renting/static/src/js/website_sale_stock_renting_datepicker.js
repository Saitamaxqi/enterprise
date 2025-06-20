import WebsiteSaleDaterangePicker from '@website_sale_renting/js/website_sale_renting_daterangepicker';

WebsiteSaleDaterangePicker.include({
    events: Object.assign({}, WebsiteSaleDaterangePicker.prototype.events, {
        'change_product_id': '_onChangeProductId',
    }),

    /**
     * Override to get the renting product stock availabilities
     *
     * @override
     */
    async start() {
        await this._super(...arguments);
        await this._updateRentingProductAvailabilities();
    },

    // ------------------------------------------
    // Handlers
    // ------------------------------------------
    /**
     * Handle product changed to update the availabilities
     *
     * @param {Event} _event
     * @param {object} params
     */
    _onChangeProductId(_event, params) {
        if (this.productId !== params.product_id) {
            this.productId = params.product_id;
            this._updateRentingProductAvailabilities();
        }
    },

    async _fetchProductAvailabilities(productId, minDate, maxDate) {
        const result = await this._super(...arguments);
        this.preparationTime = result.preparation_time;
        return result;
    },

    // ------------------------------------------
    // Utils
    // ------------------------------------------

    _triggerRentingConstraintsChanged(vals) {
        if ('rentingAvailabilities' in vals) {
            vals.preparationTime = this.preparationTime;
        }
        this._super(vals);
    },
});
