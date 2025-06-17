import WebsiteSaleDaterangePicker from '@website_sale_renting/js/website_sale_renting_daterangepicker';

WebsiteSaleDaterangePicker.include({
    async start() {
        await this._super(...arguments);
        await this._updateRentingProductAvailabilities();
    },
});
