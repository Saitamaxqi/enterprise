# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import wizard


def _account_reports_post_init(env):
    env.ref('account_reports.ir_cron_generate_account_return')._trigger()
