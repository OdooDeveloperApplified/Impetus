from odoo import api, fields, models
import logging
import math

_logger = logging.getLogger(__name__)

class CrmTemplate(models.Model):
    _inherit = 'crm.lead'

    custom_salesperson = fields.Many2one('hr.employee', string='Salesperson (Employee)', required=True, tracking=True)  