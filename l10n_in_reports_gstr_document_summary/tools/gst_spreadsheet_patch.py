from odoo.addons.l10n_in_reports.tools.gstr1_spreadsheet_generator import GSTR1SpreadsheetGenerator
from ..models.gstr_document_summary import DOCUMENT_TYPE_LIST

_original_prepare_sheet_values = GSTR1SpreadsheetGenerator._prepare_sheet_values


def patched_prepare_sheet_values(self, workbook, cell_formats):
    _original_prepare_sheet_values(self, workbook, cell_formats)
    _prepare_doc_issue_sheet(self, self.gstr1_json.get('doc_issue', {}), workbook, cell_formats)


def _prepare_doc_issue_sheet(self, doc_issue_json, workbook, cell_formats):
    primary_header_row = 2
    secondary_header_row = 4
    totals_val_row = 3
    row_count = 5
    worksheet = workbook.add_worksheet('docs')
    worksheet.write('A1', 'Summary of documents issued during the tax period (13)', cell_formats.get('primary_header'))
    primary_headers = [
        {'val': 'Total Documents Issued', 'column': 'D'},
        {'val': 'Total Cancelled', 'column': 'E'},
        {'val': 'Total Net Issued', 'column': 'F'},
    ]
    secondary_headers = [
        {'val': 'Nature of Document', 'column': 'A'},
        {'val': 'Sr. No. From', 'column': 'B'},
        {'val': 'Sr. No. To', 'column': 'C'},
        {'val': 'Total Issued', 'column': 'D'},
        {'val': 'Cancelled', 'column': 'E'},
        {'val': 'Net Issued', 'column': 'F'},
    ]
    totals_row_data = {
        'total_issued': {'val': 0, 'column': 'D'},
        'cancelled': {'val': 0, 'column': 'E'},
        'net_issued': {'val': 0, 'column': 'F'},
    }
    self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row, cell_formats.get('primary_header'))
    self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row, cell_formats.get('secondary_header'))
    worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
    worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
    worksheet.set_column('A:A', 50)
    worksheet.set_column('B:F', 25)
    document_type_selection = dict(DOCUMENT_TYPE_LIST)
    for document in doc_issue_json.get("doc_det", []):
        doc_num = str(document.get("doc_num"))
        for doc in document.get("docs", []):
            row_data = [
                {'val': document_type_selection.get(doc_num, f'Document {doc_num}'), 'column': 'A'},
                {'val': doc.get('from', '0'), 'column': 'B'},
                {'val': doc.get('to', '0'), 'column': 'C'},
                {'val': doc.get('totnum', 0), 'column': 'D'},
                {'val': doc.get('cancel', 0), 'column': 'E'},
                {'val': doc.get('net_issue', 0), 'column': 'F'},
            ]
            self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
            totals_row_data['total_issued']['val'] += doc.get('totnum', 0)
            totals_row_data['cancelled']['val'] += doc.get('cancel', 0)
            totals_row_data['net_issued']['val'] += doc.get('net_issue', 0)
            row_count += 1
    self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))


GSTR1SpreadsheetGenerator._prepare_sheet_values = patched_prepare_sheet_values
