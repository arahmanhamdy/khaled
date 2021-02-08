import datetime
from odoo import api, fields, models

from odoo.exceptions import UserError


class MonthlyCost(models.Model):
    _name = "monthly.cost"

    def _get_months(self):
        return [(str(i), str(i)) for i in range(1, 13)]

    def _get_years(self):
        return [(str(i), str(i)) for i in range(2020, 2051)]

    def get_default_month(self):
        today = datetime.datetime.today()
        return str(today.month)

    def get_default_year(self):
        today = datetime.datetime.today()
        print(today.year)
        return str(today.year)

    month = fields.Selection(_get_months, default=get_default_month, string="الشهر")
    year = fields.Selection(_get_years, default=get_default_year, string="السنة")
    electricity_bill = fields.Float(string="فاتورة الكهرباء")
    number_of_workers = fields.Integer(string="عدد العمالة الشهرية")
    monthly_wage_ids = fields.One2many("monthly.workers.wage", "month_id", string="مرتبات العمالة الشهرية")

    @api.onchange("number_of_workers")
    def _onchange_number_of_workers(self):
        workers = []
        for i in range(1, int(self.number_of_workers) + 1):
            workers.append([0, 0, {"name": f"عامل {i}"}])
        self.monthly_wage_ids = [[5, 0, 0]]
        self.monthly_wage_ids = workers

    @api.constrains("month", "year")
    def check_month_year(self):
        if self.search([("month", '=', self.month), ("year", '=', self.year), ("id", '!=', self.id)]):
            raise UserError("لقد قمت بإدخال مصاريف هذا الشهر من قبل")


class MonthlyWorkersWage(models.Model):
    _name = "monthly.workers.wage"

    name = fields.Char(string="عامل")
    month_id = fields.Many2one("monthly.cost")
    wage = fields.Integer(string="المرتب")
