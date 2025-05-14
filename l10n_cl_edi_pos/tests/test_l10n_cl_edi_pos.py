# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.l10n_cl_edi.tests.common import TestL10nClEdiCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nClEdiPos(TestL10nClEdiCommon, TestPointOfSaleHttpCommon):
    def test_cl_receipt_header_content(self):
        self.partner_test = self.env['res.partner'].create({
            'name': 'AA Test Partner',
            'is_company': 1,
            'city': 'Pudahuel',
            'country_id': self.env.ref('base.cl').id,
            'street': 'Puerto Test 102',
            'phone': '+562 0000 0000',
            'website': 'http://www.partner_sii.cl',
            'company_id': self.company_data['company'].id,
            'l10n_cl_dte_email': 'partner@sii.cl',
            'l10n_latam_identification_type_id': self.env.ref('l10n_cl.it_RUT').id,
            'l10n_cl_sii_taxpayer_type': '1',
            'l10n_cl_activity_description': 'activity_test',
            'vat': '76086428-5',
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_receipt_header_content', login="accountman")
