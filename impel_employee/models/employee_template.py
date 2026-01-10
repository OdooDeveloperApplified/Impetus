from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta

class EmployeeTemplate(models.Model):
    _inherit = "hr.employee"

    # Custom fields added to Employee's form view
    joining_date = fields.Date(string='Date of Joining')
    employee_module = fields.Selection([
        ('module_a', 'Module A'),
        ('module_b', 'Module B'),
        ('module_c', 'Module C'),
        ('module_d', 'Module D'),
        ('module_e', 'Module E'),
    ],string='Modules', domain="[('state', '=', 'installed')]")
    mother_name = fields.Char(string="Mother's Name")
    mother_dob = fields.Date(string="Mother's DOB")
    father_name = fields.Char(string="Father's Name")
    father_dob = fields.Date(string="Father's DOB")
    parent_anniversary = fields.Date(string="Parent's Anniversary")
    number_of_children = fields.Integer(string="Number of Children")
    emp_child_ids = fields.One2many('employee.child.info','employee_id',string='Children Details')
    driving_licence = fields.Char(string="Driving Licence Number")
    adhaar_no = fields.Char(string="Adhaar Number")
    pan_no = fields.Char(string="PAN card Number")
    emp_education = fields.Char(string="Education")
    emp_experience = fields.Char(string="Experience")
    emp_anniversary = fields.Date(string="Wedding Anniversary")
    mediclaim_number = fields.Char(string="Mediclaim Number")
    mediclaim_amount = fields.Float(string="Mediclaim Amount")
    insurance_number = fields.Char(string="Accidental Insurance Number")
    insurance_amount = fields.Float(string="Accidental Insurance Amount")
    termplan_number = fields.Char(string="Term Plan Number")
    termplan_amount = fields.Float(string="Term Plan Amount")
    ayushman_number = fields.Char(string="Ayushmaan Card Number")
    ehram_number = fields.Char(string="E-shram Card Number")
    company_assets = fields.Text(string="Comapny Assets Details")

    @api.constrains('number_of_children', 'emp_child_ids')
    def _check_children_count(self):
        for rec in self:
            if rec.number_of_children != len(rec.emp_child_ids):
                raise ValidationError("Number of children must match the children records added.")
            
    ############ Code for Employee Appraisal Card workflow: starts ############
    appraisal_line_ids = fields.One2many("employee.appraisal.line", "employee_id", string="Appraisals")
    reward_total = fields.Float(compute="_compute_appraisal_totals",)
    penalty_total = fields.Float(compute="_compute_appraisal_totals",)

    def _compute_appraisal_totals(self):
        for emp in self:
            reward = 0.0
            penalty = 0.0
            for line in emp.appraisal_line_ids:
                if line.card_id.is_penalty:
                    penalty += line.amount
                else:
                    reward += line.amount
            emp.reward_total = reward
            emp.penalty_total = penalty
    ############ Code for Employee Appraisal Card workflow: ends ############

class EmployeeEventWizard(models.TransientModel):
    _name = "employee.event.wizard"
    _description = "Employee Birthday / Anniversary Wizard"
    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string="Month", required=True)
    event_type = fields.Selection([
        ('birthday', 'Birthday'),
        ('anniversary', 'Anniversary'),
    ], string="Event Type", required=True)
    
    def action_view_employees(self):
        self.ensure_one()
        month = int(self.month)
        
        if self.event_type == 'birthday':
            # Filter by month only, ignore year
            domain = [('birthday', '!=', False)]  # first ensure date exists
            employees = self.env['hr.employee'].search(domain)
            employees = employees.filtered(lambda e: e.birthday and e.birthday.month == month)
        else:
            domain = [('emp_anniversary', '!=', False)]
            employees = self.env['hr.employee'].search(domain)
            employees = employees.filtered(lambda e: e.emp_anniversary and e.emp_anniversary.month == month)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Employees',
            'res_model': 'hr.employee',
            'view_mode': 'tree',
            'views': [(self.env.ref('impel_employee.view_employee_birthday_anniversary_list').id, 'tree')],
            'domain': [('id', 'in', employees.ids)],
            'target': 'current',
        }


class EmployeeChildInfo(models.Model):
    _name = "employee.child.info"
    _description = "Employee Child Details"

    employee_id = fields.Many2one('hr.employee', string='Employee')
    name = fields.Char(string="Child's Name")
    dob = fields.Date(string="Date of Birth")
    education = fields.Char(string="Education as on 2026")

class EmployeeAppraisalCard(models.Model):
    _name = "employee.appraisal.card"
    _description = "Employee Appraisal Card"

    name = fields.Char(required=True)
    amount = fields.Float(string="Card Value",help="Default amount for this card")
    is_penalty = fields.Boolean(string="Penalty Card",help="Penalty cards allow manual amount entry")
    active = fields.Boolean(default=True)

class EmployeeAppraisalLine(models.Model):
    _name = "employee.appraisal.line"
    _description = "Employee Appraisal Entry"
    _order = "date desc"

    employee_id = fields.Many2one("hr.employee",required=True)
    card_id = fields.Many2one("employee.appraisal.card",required=True)
    date = fields.Date(default=fields.Date.today)
    amount = fields.Float()
    remarks = fields.Text()
    given_by_id = fields.Many2one("res.users", default=lambda self: self.env.user, string="Given By")

    @api.onchange("card_id")
    def _onchange_card_id(self):
        if self.card_id:
            if self.card_id.is_penalty:
                self.amount = 0.0
            else:
                self.amount = self.card_id.amount