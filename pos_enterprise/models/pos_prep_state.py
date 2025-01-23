from odoo import fields, models


class PosPreparationState(models.Model):
    _name = 'pos.prep.state'
    _description = 'Pos Preparation State'
    _inherit = ['pos.load.mixin']

    prep_line_id = fields.Many2one('pos.prep.line', string='Preparation Orderline', required=True, ondelete='cascade')
    todo = fields.Boolean("Status of the orderline", help="The status of a command line, todo or not", default=True)
    stage_id = fields.Many2one('pos.prep.stage', ondelete='cascade', index=True)

    def change_state_status(self, todos, prep_display_id):
        pdis_state_todos = []

        for pdis_state in self:
            pdis_state.todo = todos[str(pdis_state.id)]
            pdis_state_todos.append({
                'id': pdis_state.id,
                'todo': pdis_state.todo
            })

        p_dis = self.env['pos.prep.display'].browse(int(prep_display_id))
        p_dis._notify('CHANGE_STATE_STATUS', pdis_state_todos)

        return True

    def change_state_stage(self, stages, prep_display_id):
        pdis_state_stages = []

        for pdis_state in self:
            pdis_state.todo = True
            pdis_state.stage_id = stages[str(pdis_state.id)]
            pdis_state_stages.append({
                'id': pdis_state.id,
                'stage_id': pdis_state.stage_id.id,
                'last_stage_change': pdis_state.write_date
            })

        p_dis = self.env['pos.prep.display'].browse(int(prep_display_id))
        p_dis._notify('CHANGE_STATE_STAGE', pdis_state_stages)

        return True
