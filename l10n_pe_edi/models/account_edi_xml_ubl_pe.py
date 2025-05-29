import re

from odoo import models
from odoo.tools.misc import partition

# These codes correspond to the tax affectation reasons used in Peru for
# issuing free invoices according to SUNAT regulations. Invoices with these
# codes are considered "gratuitas" (free), meaning that no payment is expected
# for the goods or services provided, typically in cases like promotions,
# donations, or samples.
FREE_AFFECTATION_REASONS = ['11', '12', '13', '14', '15', '16', '21', '31', '32', '33', '34', '35', '36']


class AccountEdiXmlUbl_Pe(models.AbstractModel):
    _name = 'account.edi.xml.ubl_pe'
    _inherit = ['account.edi.xml.ubl_21']
    _description = 'PE UBL 2.1'

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_pe.xml"

    def _get_partner_party_identification_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_party_identification_vals_list(partner)
        vals.append({
            'id_attrs': {
                'schemeID': partner.l10n_latam_identification_type_id.l10n_pe_vat_code,
            },
            'id': partner.vat,
        })
        return vals

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_address_vals(partner)
        vals.update({
            'id': partner.l10n_pe_district.code,
            'address_type_code': partner.company_id.l10n_pe_edi_address_type_code,
        })
        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        # OVERRIDES account.edi.xml.ubl_21
        spot = invoice._l10n_pe_edi_get_spot()
        if not spot:
            return []

        vals = {
            'id': spot['id'],
            'payment_means_code': spot['payment_means_code'],
            'payee_financial_account_vals': {
                'id': spot['payee_financial_account'],
            },
        }
        return [vals]

    def _get_invoice_payment_terms_vals_list(self, invoice):
        # OVERRIDES account.edi.xml.ubl_21
        spot = invoice._l10n_pe_edi_get_spot()
        if spot:
            spot_amount = spot['amount'] if invoice.currency_id == invoice.company_id.currency_id else spot['spot_amount']
        invoice_date_due_vals_list = []
        first_time = True
        for rec_line in invoice.line_ids.filtered(lambda l: l.account_type == 'asset_receivable'):
            amount = rec_line.amount_currency
            if spot and first_time:
                amount -= spot_amount
            first_time = False
            invoice_date_due_vals_list.append({
                'currency_name': rec_line.currency_id.name,
                'currency_dp': rec_line.currency_id.decimal_places,
                'amount': amount,
                'date_maturity': rec_line.date_maturity,
            })
        if not spot:
            total_after_spot = abs(invoice.amount_total)
        else:
            total_after_spot = abs(invoice.amount_total) - spot_amount
        payment_means_id = invoice._l10n_pe_edi_get_payment_means()
        vals = []
        if spot:
            vals.append({
                'id': spot['id'],
                'currency_name': 'PEN',
                'currency_dp': 2,
                'payment_means_id': spot['payment_means_id'],
                'payment_percent': spot['payment_percent'],
                'amount': spot['amount'],
            })
        if invoice.move_type not in ('out_refund', 'in_refund'):
            if payment_means_id == 'Contado':
                vals.append({
                    'id': 'FormaPago',
                    'payment_means_id': payment_means_id,
                })
            else:
                vals.append({
                    'id': 'FormaPago',
                    'currency_name': invoice.currency_id.name,
                    'currency_dp': invoice.currency_id.decimal_places,
                    'payment_means_id': payment_means_id,
                    'amount': total_after_spot,
                })
                for i, due_vals in enumerate(invoice_date_due_vals_list):
                    vals.append({
                        'id': 'FormaPago',
                        'currency_name': due_vals['currency_name'],
                        'currency_dp': due_vals['currency_dp'],
                        'payment_means_id': 'Cuota' + '{0:03d}'.format(i + 1),
                        'amount': due_vals['amount'],
                        'payment_due_date': due_vals['date_maturity'],
                    })

        return vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        def grouping_key_generator(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'l10n_pe_edi_code': tax.tax_group_id.l10n_pe_edi_code,
                'l10n_pe_edi_international_code': tax.l10n_pe_edi_international_code,
                'l10n_pe_edi_tax_code': tax.l10n_pe_edi_tax_code,
            }

        tax_details_grouped = invoice._prepare_edi_tax_details(grouping_key_generator=grouping_key_generator)
        isc_tax_amount = abs(sum([
            line.amount_currency
            for line in invoice.line_ids.filtered(lambda l: l.tax_line_id.tax_group_id.l10n_pe_edi_code == 'ISC')
        ]))
        vals[0]['tax_amount'] = 0.00 if invoice.l10n_pe_edi_legend == '1002' else vals[0]['tax_amount']
        vals[0]['tax_subtotal_vals'] = []

        for grouping_vals in tax_details_grouped['tax_details'].values():
            if grouping_vals['tax_amount_currency'] < 0 and invoice.l10n_pe_edi_legend == '1002':
                continue
            vals[0]['tax_subtotal_vals'].append({
                'currency': invoice.currency_id,
                'currency_dp': invoice.currency_id.decimal_places,
                'taxable_amount': (
                    grouping_vals['base_amount_currency']
                    - (isc_tax_amount if grouping_vals['l10n_pe_edi_code'] != 'ISC' else 0)
                ),
                'tax_amount': grouping_vals['tax_amount_currency'] or 0.0,
                'tax_category_vals': {
                    'tax_scheme_vals': {
                        'id': grouping_vals['l10n_pe_edi_tax_code'],
                        'name': grouping_vals['l10n_pe_edi_code'],
                        'tax_type_code': grouping_vals['l10n_pe_edi_international_code'],
                    },
                },
            })

        return vals

    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        # OVERRIDES account.edi.xml.ubl_21
        vals = {
            'currency': line.currency_id,
            'currency_dp': line.currency_id.decimal_places,
            'tax_amount': 0.00 if line.l10n_pe_edi_affectation_reason in FREE_AFFECTATION_REASONS else line.price_total - line.price_subtotal,
            'tax_subtotal_vals': [],
        }

        for tax_detail_vals in taxes_vals['tax_details'].values():
            tax = tax_detail_vals['taxes_data'][0]['tax']
            if tax_detail_vals['tax_amount_currency'] < 0 and line.move_id.l10n_pe_edi_legend == '1002':
                continue

            vals['tax_subtotal_vals'].append({
                'currency': line.currency_id,
                'currency_dp': line.currency_id.decimal_places,
                'taxable_amount': tax_detail_vals['base_amount_currency'] if tax.tax_group_id.l10n_pe_edi_code != 'ICBPER' else None,
                'tax_amount': tax_detail_vals['tax_amount_currency'] or 0.0,
                'base_unit_measure_attrs': {
                    'unitCode': 'NIU' if line._get_downpayment_lines() else line.product_uom_id.l10n_pe_edi_measure_unit_code,
                },
                'base_unit_measure': int(line.quantity) if tax.tax_group_id.l10n_pe_edi_code == 'ICBPER' else None,
                'tax_category_vals': {
                    'percent': tax.amount if tax.amount_type == 'percent' else None,
                    'tax_exemption_reason_code': (
                        line.l10n_pe_edi_affectation_reason
                        if tax.tax_group_id.l10n_pe_edi_code not in ('ISC', 'ICBPER') and line.l10n_pe_edi_affectation_reason
                        else None
                    ),
                    'tier_range': tax.l10n_pe_edi_isc_type if tax.tax_group_id.l10n_pe_edi_code == 'ISC' and tax.l10n_pe_edi_isc_type else None,
                    'tax_scheme_vals': {
                        'id': tax.l10n_pe_edi_tax_code,
                        'name': tax.tax_group_id.l10n_pe_edi_code,
                        'tax_type_code': tax.l10n_pe_edi_international_code,
                    },
                },
            })
        return [vals]

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        if vals['description']:
            vals['description'] = vals['description'][:250]
        vals['commodity_classification_vals'] = [{'item_classification_code': line.product_id.unspsc_code_id.code}]
        vals['classified_tax_category_vals'] = None

        return vals

    def _get_document_allowance_charge_vals_list(self, invoice, taxes_vals=None):
        # EXTENDS account.edi.xml.ubl_21
        res = super()._get_document_allowance_charge_vals_list(invoice)
        total_discount = 0.0
        for line in invoice.invoice_line_ids.filtered(lambda line: line.price_subtotal < 0):
            res.append({
                'charge_indicator': 'false',
                'allowance_charge_reason_code': '02',
                'amount': abs(line.price_subtotal),
                'currency_dp': 2,
                'currency_name': invoice.currency_id.name,
            })
            total_discount += abs(line.price_subtotal)

        # The base amount must be the total pre-discount of the invoice.
        for val in res:
            if val['charge_indicator'] == 'false' and val['allowance_charge_reason_code'] == '02':
                val['base_amount'] = taxes_vals['base_amount_currency'] + total_discount
                val['multiplier_factor'] = self.format_float(val['amount'] / val['base_amount'], 5)
        return res

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list=None):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_invoice_line_allowance_vals_list(line, tax_values_list)
        discount_allowance, others = partition(lambda value: value.get('allowance_charge_reason_code') != 'AEO', vals)
        if discount_allowance:
            line_data = line._prepare_edi_vals_to_export()
            discount = discount_allowance[0]
            discount.update({
                'allowance_charge_reason_code': '00',
                'base_amount': line_data['price_subtotal_before_discount'],
                'multiplier_factor': self.format_float(line.discount / 100.00, 5),
            })
            return [discount] + others
        return vals

    def _get_invoice_line_price_vals(self, line):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_invoice_line_price_vals(line)
        if line.l10n_pe_edi_affectation_reason in FREE_AFFECTATION_REASONS:
            vals['price_amount'] = 0.0
        return vals

    def _get_invoice_line_vals(self, line, taxes_vals, idx=None):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_invoice_line_vals(line, taxes_vals, idx)
        line_vals = line._prepare_edi_vals_to_export()
        vals['line_quantity_attrs']['unitCode'] = 'NIU' if line._get_downpayment_lines() else line.product_uom_id.l10n_pe_edi_measure_unit_code
        vals['pricing_reference_vals'] = {
            'alternative_condition_price_vals': [{
                'currency': line.currency_id,
                'price_amount': (line_vals['price_subtotal_unit']
                    if line.l10n_pe_edi_affectation_reason in FREE_AFFECTATION_REASONS
                    else line_vals['price_total_unit']),
                'price_amount_dp': self.env['decimal.precision'].precision_get('Product Price'),
                'price_type_code': '02' if line.currency_id.is_zero(line_vals['price_subtotal_before_discount']) or line.l10n_pe_edi_affectation_reason in FREE_AFFECTATION_REASONS else '01'
            }]
        }
        return vals

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_invoice_monetary_total_vals(invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount)
        vals['payable_amount'] += vals['prepaid_amount']
        if invoice.l10n_pe_edi_legend == '1002':
            vals['line_extension_amount'] = 0.0
            vals['tax_inclusive_amount'] = 0.0
            vals['payable_amount'] = 0.0
        vals['prepaid_amount'] = 0.0
        # Only certain types of allowances in PE require the AllowanceTotalAmount key added here.
        # However, none of them are supported in Odoo currently and as such we should just clear them.
        if vals['allowance_total_amount']:
            vals['allowance_total_amount'] = 0.0
        return vals

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._export_invoice_vals(invoice)

        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.commercial_partner_id

        vals['vals'].update({
            'customization_id': '2.0',
            'id': invoice.name.replace(' ', ''),
            'signature_vals': [{
                'id': 'IDSignKG',
                'signatory_party_vals': {
                    'party_id': invoice.company_id.vat,
                    'party_name': invoice.company_id.name.upper(),
                },
                'digital_signature_attachment_vals': {
                    'external_reference_uri': '#SignVX',
                },
            }],
        })

        vals['vals']['accounting_supplier_party_vals'].update({
            'customer_assigned_account_id': supplier.vat,
        })
        vals['vals']['accounting_supplier_party_vals']['party_vals']['party_legal_entity_vals'][0]['registration_address_vals'].update({
            'address_type_code': invoice.company_id.l10n_pe_edi_address_type_code,
        })

        vals['vals']['accounting_customer_party_vals'].update({
            'additional_account_id': (
                customer.l10n_latam_identification_type_id
                and customer.l10n_latam_identification_type_id.l10n_pe_vat_code
            ),
        })

        if vals['vals']['order_reference']:
            vals['vals']['order_reference'] = vals['vals']['order_reference'][:20]

        # Invoice specific changes
        if vals['document_type'] == 'invoice':
            vals['vals'].update({
                'document_type_code': invoice.l10n_latam_document_type_id.code,
                'document_type_code_attrs': {
                    'listID': invoice.l10n_pe_edi_operation_type,
                    'listAgencyName': 'PE:SUNAT',
                    'listName': 'Tipo de Documento',
                    'listURI': 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01',
                },
            })
            if invoice.l10n_pe_edi_legend_value:
                vals['vals']['note_vals'].append({
                    'note': invoice.l10n_pe_edi_legend_value,
                    'note_attrs': {'languageLocaleID': invoice.l10n_pe_edi_legend},
                })
            vals['vals']['note_vals'].append({
                'note': invoice._l10n_pe_edi_amount_to_text(),
                'note_attrs': {'languageLocaleID': '1000'},
            })
            if invoice.l10n_pe_edi_operation_type == '1001':
                vals['vals']['note_vals'].append({
                    'note': 'Leyenda: Operacion sujeta a detraccion',
                    'note_attrs': {'languageLocaleID': '2006'},
                })

        # Credit Note specific changes
        if vals['document_type'] == 'credit_note':
            if invoice.l10n_latam_document_type_id.code == '07':
                vals['vals'].update({
                    'discrepancy_response_vals': [{
                        'response_code': invoice.l10n_pe_edi_refund_reason,
                        'description': invoice.ref
                    }]
                })
            if invoice.reversed_entry_id:
                vals['vals'].update({
                    'billing_reference_vals': {
                        'id': invoice.reversed_entry_id.name.replace(' ', ''),
                        'document_type_code': invoice.reversed_entry_id.l10n_latam_document_type_id.code,
                    },
                })

        # Debit Note specific changes
        if vals['document_type'] == 'debit_note':
            if invoice.l10n_latam_document_type_id.code == '08':
                vals['vals'].update({
                    'discrepancy_response_vals': [{
                        'response_code': invoice.l10n_pe_edi_charge_reason,
                        'description': invoice.ref
                    }]
                })
            if invoice.debit_origin_id:
                vals['vals'].update({
                    'billing_reference_vals': {
                        'id': invoice.debit_origin_id.name.replace(' ', ''),
                        'document_type_code': invoice.debit_origin_id.l10n_latam_document_type_id.code,
                    },
                })

        # Remove negative discount lines as they are handled via the global discounts allowances on
        # the document level.
        final_line_vals = []
        for line_vals in vals['vals']['line_vals']:
            if line_vals['price_vals']['price_amount'] >= 0:
                final_line_vals.append(line_vals)
        vals['vals']['line_vals'] = final_line_vals

        return vals

    def _get_note_vals_list(self, invoice):
        # In PE localization, as many special characters are not supported in Note node,
        # they are replaced by an empty space.
        vals = super()._get_note_vals_list(invoice)
        for note_vals in vals:
            note_vals['note'] = re.sub(r'[\s]+', ' ', note_vals['note']).strip()[:200]
        return vals
