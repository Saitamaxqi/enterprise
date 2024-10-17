import json

from odoo.tests.common import HttpCase

from .common import SpreadsheetTestCommon
from odoo.tools import file_open


class SpreadsheetImportCSV(HttpCase, SpreadsheetTestCommon):
    def test_import_csv(self):
        folder = self.env["documents.document"].create({"name": "New folder", "type": "folder"})
        with file_open('documents_spreadsheet/tests/data/test.csv', 'rb') as f:
            document_csv = self.env['documents.document'].create({
                'raw': f.read(),
                'name': 'test.csv',
                'mimetype': 'text/csv',
                'folder_id': folder.id
            })
            spreadsheet_id = document_csv.import_to_spreadsheet()
            spreadsheet = self.env["documents.document"].browse(spreadsheet_id).exists()
            self.assertTrue(spreadsheet)
            self.assertEqual(spreadsheet.name, "test")
            expected_data = {
                "sheets": [
                    {
                        "cells": {
                            "A1": {"content": "1"},
                            "B1": {"content": "Pamella"},
                            "C1": {"content": "Piercy"},
                            "D1": {"content": "ppiercy0@slashdot.org"},
                            "A2": {"content": "2"},
                            "B2": {"content": "Crissie"},
                            "C2": {"content": "Narrie"},
                            "D2": {"content": "cnarrie1@godaddy.com"},
                            "A3": {"content": "3"},
                            "B3": {"content": "Ruby"},
                            "C3": {"content": "Smallcombe"},
                            "D3": {"content": "rsmallcombe2@google.it"},
                        },
                        "comments": {}
                    }
                ]
            }
            self.assertEqual(json.loads(spreadsheet.raw), expected_data)
