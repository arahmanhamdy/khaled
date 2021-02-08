from odoo import api, fields, models


class MachineDaily(models.Model):
    _name = "machine.daily"

    name = fields.Date(default=fields.Date.today, required=True, string="التاريخ")
    shifts_number = fields.Selection([("0", "0"), ("1", "1"),
                                      ("2", "2"), ("3", "3"), ("4", "4")], required=True,
                                     string="عدد الورادي")
    hours_per_shift = fields.Selection([("6", "6"), ("8", "8"), ("12", "12")], default="8", required=True,
                                       string="عدد ساعات الوردية")
    daily_workers = fields.Integer(required=True, string="عدد عمال اليومية")
    machine_shift_ids = fields.One2many("machine.shift", "daily_id", string="توزيعة المكن")
    worker_daily_cost_ids = fields.One2many("worker.daily.cost", "daily_id", string="يوميات")
    machine_extra_cost_ids = fields.One2many("machine.extra.daily.cost", "daily_id")
    production_ids = fields.One2many("machine.production.daily", "daily_id")
    extra_cost = fields.Boolean(string="تكاليف إضافية ؟")

    @api.onchange("daily_workers")
    def _onchange_daily_workers(self):
        workers = []
        for i in range(1, int(self.daily_workers) + 1):
            workers.append([0, 0, {"name": f"عامل {i}"}])
        self.worker_daily_cost_ids = [[5, 0, 0]]
        self.worker_daily_cost_ids = workers

    @api.onchange("machine_shift_ids")
    def _onchange_machine_shift_ids(self):
        machine_lines = []
        all_machines = self.env["machine.machine"].search([])
        for machine in all_machines:
            machine_lines.append([0, 0, {"machine": machine.id}])
        self.machine_shift_ids = [[5, 0, 0]]
        self.machine_shift_ids = machine_lines
        self.production_ids = [[5, 0, 0]]
        self.production_ids = machine_lines


class MachineShift(models.Model):
    _name = "machine.shift"

    machine = fields.Many2one("machine.machine", required=True, string="المكنة")
    shifts_number = fields.Selection([("0", "0"), ("1", "1"),
                                      ("2", "2"), ("3", "3"), ("4", "4")], required=True,
                                     string="عدد الورادي")
    daily_id = fields.Many2one("machine.daily")


class WorkerDailyCost(models.Model):
    _name = "worker.daily.cost"

    name = fields.Char(required=True, string="العامل")
    cost = fields.Integer(required=True, string="اليومية")
    daily_id = fields.Many2one("machine.daily")


class ExtraCost(models.Model):
    _name = "machine.extra.daily.cost"

    machine = fields.Many2one("machine.machine", required=True, string="المكنة")
    cost = fields.Integer(required=True, string="التكلفة")
    description = fields.Char(string="بيان")
    daily_id = fields.Many2one("machine.daily")


class MachineProduction(models.Model):
    _name = "machine.production.daily"

    machine = fields.Many2one("machine.machine", required=True, string="المكنة")
    amount = fields.Float(string="الكمية بالكيلو")
    production_type = fields.Many2one("production.type", string="النوع")
    fee_per_kg = fields.Float(string="المصنعية لكل كيلو")
    daily_id = fields.Many2one("machine.daily")
    total = fields.Float(compute="calc_total", string="الإيراد")

    @api.depends("fee_per_kg", "amount")
    def calc_total(self):
        for rec in self:
            rec.total = rec.fee_per_kg * rec.amount


class ProductionType(models.Model):
    _name = "production.type"

    name = fields.Char(string="النوع")


class Machine(models.Model):
    _name = "machine.machine"

    name = fields.Char(required=True, string="الاسم")
    description = fields.Char(string="الوصف")
    rent = fields.Integer(string="الإيجار")
    production = fields.Float(string="الانتاج")

