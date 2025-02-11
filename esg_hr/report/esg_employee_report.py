from odoo import fields, models, tools


class EsgEmployeeReport(models.Model):
    _name = "esg.employee.report"
    _description = "ESG Employee Report"
    _auto = False

    def _get_gender_selection(self):
        return self.env["hr.employee"]._fields["gender"]._description_selection(self.env)

    count = fields.Integer(readonly=True)
    gender = fields.Selection(selection=_get_gender_selection, readonly=True, groups="hr.group_hr_user")
    company_id = fields.Many2one("res.company", readonly=True)
    department_id = fields.Many2one("hr.department", readonly=True)
    is_team_leader = fields.Boolean(readonly=True, groups="hr.group_hr_user")
    is_full_time = fields.Boolean(readonly=True, groups="hr.group_hr_user")
    leadership_level = fields.Integer(readonly=True, groups="hr.group_hr_user")
    country_id = fields.Many2one("res.country", readonly=True)

    def _select(self):
        return """
            e.id,
            e.gender,
            e.company_id,
            e.department_id,
            e.work_location_id,
            1 AS count,
            CASE
                WHEN COUNT(ee.id) > 0 THEN TRUE
                ELSE FALSE
            END AS is_team_leader,
            CASE
                WHEN rc.full_time_required_hours IS NULL
                    OR rc.hours_per_week = rc.full_time_required_hours
                THEN TRUE
                ELSE FALSE
            END as is_full_time,
            MAX(ll.level) AS leadership_level,
            comprp.country_id
        """

    def _from(self):
        return f"""
            hr_employee e
                LEFT JOIN hr_employee ee ON ee.parent_id = e.id
                LEFT JOIN resource_calendar rc ON e.resource_calendar_id = rc.id
                LEFT JOIN ({self._leadership_level_subquery()}) ll ON e.id = ll.employee_id
                LEFT JOIN res_company rcomp ON e.company_id = rcomp.id
                LEFT JOIN res_partner comprp ON rcomp.partner_id = comprp.id
        """

    def _where(self):
        return """
            e.active = TRUE
        """

    def _group_by(self):
        return """
            e.id,
            e.gender,
            e.company_id,
            e.department_id,
            e.work_location_id,
            rc.full_time_required_hours,
            rc.hours_per_week,
            ll.level,
            comprp.country_id
        """

    def _leadership_level_subquery(self):
        return """
            WITH RECURSIVE leadership_level AS (
                SELECT
                    e.id AS employee_id,
                    0 AS level,
                    ARRAY[e.id] AS visited_nodes  -- Track the path to detect cycles
                FROM hr_employee e

                UNION ALL

                SELECT
                    e.parent_id AS employee_id,  -- Move up to the manager
                    lh.level + 1,
                    lh.visited_nodes || e.parent_id  -- Add the new node to visited list
                FROM hr_employee e
                JOIN leadership_level lh ON e.id = lh.employee_id
                WHERE e.parent_id IS NOT NULL
                AND NOT e.parent_id = ANY(lh.visited_nodes)  -- Prevent cycles
            )
            SELECT
                employee_id,
                MAX(level) AS level
            FROM leadership_level
            GROUP BY employee_id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                  SELECT {self._select()}
                    FROM {self._from()}
                   WHERE {self._where()}
                GROUP BY {self._group_by()}
            )
        """)
