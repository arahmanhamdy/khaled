import base64
import datetime
import io
from dateutil import relativedelta

import xlsxwriter
from odoo import fields, models
from odoo.exceptions import UserError

MONTHS = {
    "1": "يناير",
    "2": "فبراير",
    "3": "مارس",
    "4": "أبريل",
    "5": "مايو",
    "6": "يونيو",
    "7": "يوليو",
    "8": "أغسطس",
    "9": "سبتمبر",
    "10": "أكتوبر",
    "11": "نوفمبر",
    "12": "ديسمبر",
}

BASE_FORMAT = {'bold': True, 'align': 'center', 'valign': 'vcenter'}


class WizardMonthlyReport(models.TransientModel):
    _name = 'wizard.monthly.report'
    _description = 'Wizard Monthly Report'

    def _get_months(self):
        return [(str(i), str(i)) for i in range(1, 13)]

    def _get_years(self):
        return [(str(i), str(i)) for i in range(2021, 2051)]

    def get_default_month(self):
        today = datetime.datetime.today()
        return str(today.month)

    def get_default_year(self):
        today = datetime.datetime.today()
        return str(today.year)

    month = fields.Selection(_get_months, default=get_default_month, string="الشهر")
    year = fields.Selection(_get_years, default=get_default_year, string="السنة")
    xls_file = fields.Binary(string='تحميل')
    name = fields.Char(string='اسم الملف', size=64)
    state = fields.Selection([('choose', 'choose'),
                              ('download', 'download')], default="choose", string="Status")
    machine_ids = fields.Many2many('machine.machine', string="المكن")

    def print_report_xls(self):
        machines = self.machine_ids or self.env['machine.machine'].search([])
        xls_filename = f' تقرير  {MONTHS[self.month]} - {self.year}.xlsx'
        output_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(output_stream)

        formatters = {
            "header": workbook.add_format({**BASE_FORMAT, 'font_size': 20}),
            "bold_center": workbook.add_format(BASE_FORMAT),
            "gray": workbook.add_format({**BASE_FORMAT, 'bg_color': 'gray'}),
            "green": workbook.add_format({**BASE_FORMAT, 'bg_color': 'green'}),
            "red": workbook.add_format({**BASE_FORMAT, 'bg_color': 'red'}),
            "center": workbook.add_format({'align': 'center', 'valign': 'vcenter'}),
            "date": workbook.add_format({'num_format': 'dd/mm/yyyy', 'valign': 'vcenter'})
        }
        days = self._get_days()
        for machine in machines:
            worksheet = self._create_work_sheet(machine, workbook)
            row = self._write_headers(worksheet, machine, formatters)
            days_total_daily_cost = 0
            days_total_daily_extra_cost = 0
            days_total_production = 0
            days_total_production_amount = 0
            days_total_hours = 0
            days_total_machine_hours = 0
            for day_info in days:
                max_rows = self._get_max_rows(day_info, machine)
                total_hours = self._get_all_machines_hours(day_info)
                days_total_hours += total_hours
                machine_hours = self._get_machine_hours(machine, day_info)
                days_total_machine_hours += machine_hours
                total_workers_cost = self._get_total_workers_cost(day_info)
                machine_workers_cost = round(machine_hours / total_hours * total_workers_cost, 2)
                days_total_daily_cost += machine_workers_cost
                machine_extra_cost = self._get_machine_extra_costs(machine, day_info)
                machine_production = self._get_machine_production(machine, day_info)
                if max_rows > 0:
                    worksheet.merge_range(row, 0, row + max_rows, 0, day_info.name, formatters['date'])
                    worksheet.merge_range(row, 1, row + max_rows, 1, day_info.daily_workers, formatters['center'])
                    worksheet.merge_range(row, 2, row + max_rows, 2, machine_hours, formatters['center'])
                    worksheet.merge_range(row, 3, row + max_rows, 3, total_hours, formatters['center'])
                    worksheet.merge_range(row, 4, row + max_rows, 4, machine_workers_cost, formatters['center'])
                    worksheet.merge_range(row, 5, row + max_rows, 5, total_workers_cost, formatters['center'])
                else:
                    worksheet.write(row, 0, day_info.name, formatters['date'])
                    worksheet.write(row, 1, day_info.daily_workers, formatters['center'])
                    worksheet.write(row, 2, machine_hours, formatters['center'])
                    worksheet.write(row, 3, total_hours, formatters['center'])
                    worksheet.write(row, 4, machine_workers_cost, formatters['center'])
                    worksheet.write(row, 5, total_workers_cost, formatters['center'])
                cost_row = row
                for cost in machine_extra_cost:
                    worksheet.write(cost_row, 6, cost.description, formatters['center'])
                    worksheet.write(cost_row, 7, cost.cost, formatters['center'])
                    days_total_daily_extra_cost += cost.cost
                    cost_row += 1

                production_row = row
                for production in machine_production:
                    worksheet.write(production_row, 8, production.total, formatters['center'])
                    days_total_production += production.total
                    worksheet.write(production_row, 9, production.fee_per_kg, formatters['center'])
                    worksheet.write(production_row, 10, production.production_type.name, formatters['center'])
                    worksheet.write(production_row, 11, production.amount, formatters['center'])
                    days_total_production_amount += production.amount
                    production_row += 1

                if max_rows > 0:
                    row = row + max_rows + 1
                else:
                    row += 1

            worksheet.write(row, 0, "الإجمالى", formatters['gray'])
            worksheet.write(row, 1, "", formatters['gray'])
            worksheet.write(row, 2, days_total_machine_hours, formatters['gray'])
            worksheet.write(row, 3, days_total_hours, formatters['gray'])
            worksheet.write(row, 4, days_total_daily_cost, formatters['gray'])
            worksheet.write(row, 5, "", formatters['gray'])
            worksheet.write(row, 6, "", formatters['gray'])
            worksheet.write(row, 7, days_total_daily_extra_cost, formatters['gray'])
            worksheet.write(row, 8, days_total_production, formatters['gray'])
            worksheet.write(row, 9, "", formatters['gray'])
            worksheet.write(row, 10, "", formatters['gray'])
            worksheet.write(row, 11, "", formatters['gray'])

            monthly_costs = self._get_monthly_costs()
            machine_electricity = (days_total_machine_hours / days_total_hours) * monthly_costs.electricity_bill
            monthly_wages = sum([line.wage for line in monthly_costs.monthly_wage_ids])
            production_percentage = machine.production and (
                        days_total_production_amount / 1000) / machine.production or 0
            machine_wages = production_percentage * monthly_wages
            machine_rent = production_percentage * machine.rent
            row += 2
            worksheet.write(row, 0, "التكاليف الشهرية", formatters['bold_center'])
            worksheet.write(row + 1, 1, "الكهرباء", formatters['bold_center'])
            worksheet.write(row + 1, 2, round(machine_electricity, 2), formatters['bold_center'])
            worksheet.write(row + 2, 1, "الأجور", formatters['bold_center'])
            worksheet.write(row + 2, 2, round(machine_wages, 2), formatters['bold_center'])
            worksheet.write(row + 3, 1, "الإيجار", formatters['bold_center'])
            worksheet.write(row + 3, 2, round(machine_rent, 2), formatters['bold_center'])

            total_monthly_cost = machine_electricity + machine_wages + machine_rent
            total_daily_cost = days_total_daily_extra_cost + days_total_daily_cost
            profit_or_loss = days_total_production - total_monthly_cost - total_daily_cost
            if profit_or_loss > 0:
                word = "المكسب"
                cell_format = formatters['green']
            else:
                word = "الخسارة"
                cell_format = formatters['red']

            worksheet.write(row + 5, 0, word, cell_format)
            worksheet.write(row + 5, 1, round(profit_or_loss, 2), cell_format)

        workbook.close()
        action = self.env.ref('machine.action_wizard_monthly_report').read()[0]
        action['res_id'] = self.id
        self.write({'state': 'download',
                    'name': xls_filename,
                    'xls_file': base64.b64encode(output_stream.getvalue())})
        return action

    def action_go_back(self):
        action = self.env.ref('machine.action_wizard_monthly_report').read()[0]
        action['res_id'] = self.id
        self.write({'state': 'choose'})
        return action

    def _get_days(self):
        first_day = datetime.datetime.strptime(f"{self.year}-{self.month}-1", "%Y-%m-%d").date()
        last_day = first_day + relativedelta.relativedelta(months=1)
        search_domain = [("name", ">=", first_day), ("name", "<", last_day)]
        return self.env['machine.daily'].search(search_domain)

    @staticmethod
    def _create_work_sheet(machine, workbook):
        worksheet = workbook.add_worksheet(machine.name)
        worksheet.right_to_left()
        worksheet.set_column('A:AZ', 25)
        return worksheet

    @staticmethod
    def _get_max_rows(day_info, machine):
        extra_cost_lines = day_info.machine_extra_cost_ids.filtered(lambda r: r.machine == machine)
        production_lines = day_info.production_ids.filtered(lambda r: r.machine == machine)
        return max(len(extra_cost_lines), len(production_lines)) - 1

    def _write_headers(self, worksheet, machine, formatters):
        worksheet.merge_range(0, 0, 0, 8, f' تقرير  شهر {MONTHS[self.month]} لسنة {self.year} لــ {machine.name}',
                              formatters['header'])
        start_row = 2
        worksheet.merge_range(start_row, 0, start_row + 1, 0, "اليوم", formatters['gray'])
        worksheet.merge_range(start_row, 1, start_row + 1, 1, "عدد العمال", formatters['gray'])
        worksheet.merge_range(start_row, 2, start_row + 1, 2, "عدد ساعات تشغيل المكنة", formatters['gray'])
        worksheet.merge_range(start_row, 3, start_row + 1, 3, "عدد ساعات التشغيل لكل المكن", formatters['gray'])
        worksheet.merge_range(start_row, 4, start_row + 1, 4, "تكاليف العمالة اليومية للمكنة", formatters['gray'])
        worksheet.merge_range(start_row, 5, start_row + 1, 5, "تكاليف العمالة اليومية لكل المكن", formatters['gray'])
        worksheet.merge_range(start_row, 6, start_row, 7, "تكاليف أخري", formatters['gray'])
        worksheet.write(start_row + 1, 6, "بيان", formatters['gray'])
        worksheet.write(start_row + 1, 7, "التكلفة", formatters['gray'])
        worksheet.merge_range(start_row, 8, start_row, 11, "الإنتاج", formatters['gray'])
        worksheet.write(start_row + 1, 8, "إيراد", formatters['gray'])
        worksheet.write(start_row + 1, 9, "مصنعية", formatters['gray'])
        worksheet.write(start_row + 1, 10, "نوع", formatters['gray'])
        worksheet.write(start_row + 1, 11, "كمية", formatters['gray'])
        return start_row + 2

    @staticmethod
    def _get_machine_hours(machine, day_info):
        line = day_info.machine_shift_ids.filtered(lambda r: r.machine == machine)
        if not line:
            return 0
        return int(line.shifts_number) * int(day_info.hours_per_shift)

    @staticmethod
    def _get_all_machines_hours(day_info):
        total = 0
        for line in day_info.machine_shift_ids:
            total += (int(line.shifts_number) * int(day_info.hours_per_shift))
        return total

    @staticmethod
    def _get_total_workers_cost(day_info):
        total = 0
        for line in day_info.worker_daily_cost_ids:
            total += line.cost
        return total

    @staticmethod
    def _get_machine_extra_costs(machine, day_info):
        lines = day_info.machine_extra_cost_ids.filtered(lambda r: r.machine == machine)
        return lines

    @staticmethod
    def _get_machine_production(machine, day_info):
        lines = day_info.production_ids.filtered(lambda r: r.machine == machine)
        return lines

    def _get_monthly_costs(self):
        costs = self.env['monthly.cost'].search([('month', '=', self.month), ('year', '=', self.year)])
        if not costs:
            raise UserError("الشهر الذى قمت باختياره لم تقم بإدخال مصاريفه الشهرية")
        return costs
