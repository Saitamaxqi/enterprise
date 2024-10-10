# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrActionsAct_Window(models.Model):
    _inherit = ['studio.mixin', 'ir.actions.act_window']


class IrActionsAct_WindowView(models.Model):
    _inherit = ['studio.mixin', 'ir.actions.act_window.view']
