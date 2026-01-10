from odoo import fields, models, api

class ContactsTemplate(models.Model):
    _inherit = "res.partner"

    # Custom fields added to Contacts form view
    point_of_contact = fields.Char(string='Contact Person')
    group_name_ids = fields.Many2one('group.name', string='Group Name')
    credit_days = fields.Integer(string='Credit Days')
    credit_limit = fields.Monetary(
        string='Credit Limit',
        currency_field='currency_id'
    )
    whatsapp_no = fields.Char(string='Whatsapp Number')
    station = fields.Char(string='Station')
    demo = fields.Char(string='State (e-way bill)')
    pin = fields.Char(string='Pin')
    aadhaar_no = fields.Char(string='Aadhaar Number')
   
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    contact_dob = fields.Date(string='Date of Birth')
    contact_anniversary = fields.Date(string='Anniversary Date')
   
class GroupName(models.Model):
    _name = 'group.name'
    _description = 'Create Group Names'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name")


    