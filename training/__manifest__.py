{
    "name": "Internal Training",
    "version": "1.0",
    "depends": ["base","hr","mail","approval_workflow_engine"],
    "data": [
         "security/training_groups.xml",
        "security/ir.model.access.csv",
        "security/training_registration_security.xml",
        "security/training_my_courses_security.xml",
        "data/training_approval_workflow.xml",
        "report/training_registration_templates.xml",
        "report/training_registration_reports.xml",
        "views/training_courses_views.xml",
        "views/training_locations_views.xml",
        "views/training_rooms_views.xml",
        "views/training_teachers_views.xml",
        "views/training_registration_views.xml",
        "views/training_my_courses_views.xml",
        "views/training_menus.xml",
    ],
    "application": True
}