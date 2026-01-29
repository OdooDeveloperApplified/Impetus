from odoo import api, fields, models
import logging
import math

_logger = logging.getLogger(__name__)

class CrmTemplate(models.Model):
    _inherit = 'crm.lead'

   