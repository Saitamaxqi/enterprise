from . import models
from . import controllers


def _documents_hr_post_init(env):
    env['res.company'].search([('documents_hr_folder', '=', False)]).documents_hr_folder = env.ref(
        'documents_hr.document_hr_folder')
    env['res.company'].search([])._generate_employee_documents_folders()
    env['hr.employee'].search([('hr_employee_folder_id', '=', False)])._generate_employee_documents_subfolders()
