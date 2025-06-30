from odoo import models, api
from datetime import datetime

class LiquidationCalculator(models.Model):
    _name = 'hr.liquidation.calculator'
    _description = 'Calculadora de Liquidaciones'

    def calculate_work_period(self, date_start, date_end):
        delta = date_end - date_start
        dias_totales = delta.days + 1
        anos  = dias_totales // 365
        meses = (dias_totales % 365) // 30
        return {'total_days':dias_totales,'years':anos,'months':meses,'daily_factor':30.0}

    def calculate_vacation(self, work_period, salary_daily):
        if work_period['total_days'] >= 365:
            dias_vac = min(15 + work_period['years'],30)
        else:
            dias_vac = 15*(work_period['total_days']/365)
        return {'days':dias_vac,'amount':dias_vac*salary_daily}

    def calculate_vacation_bonus(self, vacation_days, salary_daily):
        return {'days':vacation_days,'amount':vacation_days*salary_daily}

    def calculate_social_benefits(self, work_period, salary_daily):
        anos_frac = work_period['years'] + (1 if work_period['months']>=6 else 0)
        dias_prest_c = anos_frac*30
        monto_prest_c = dias_prest_c*salary_daily
        trimestres = work_period['total_days']//90
        dias_a = trimestres*15
        dias_b = work_period['years']*2
        dias_garantia = dias_a + dias_b
        monto_garantia = dias_garantia*salary_daily
        return {'method_c':{'days':dias_prest_c,'amount':monto_prest_c},
                'guarantee_fund':{'days':dias_garantia,'amount':monto_garantia},
                'final_amount':max(monto_prest_c,monto_garantia)}

    def calculate_notice(self, work_period, salary_daily):
        td = work_period['total_days']
        if td<30: dias_pre=0
        elif td<182: dias_pre=7
        elif td<365: dias_pre=15
        else: dias_pre=30
        return {'days':dias_pre,'amount':dias_pre*salary_daily}

    def calculate_all(self, date_start, date_end, salary):
        wp = self.calculate_work_period(date_start, date_end)
        sd = salary/wp['daily_factor']
        vac   = self.calculate_vacation(wp,sd)
        vb    = self.calculate_vacation_bonus(vac['days'],sd)
        sb    = self.calculate_social_benefits(wp,sd)
        notice= self.calculate_notice(wp,sd)
        total = vac['amount']+vb['amount']+sb['final_amount']+notice['amount']
        return {'work_period':wp,'vacation':vac,'vacation_bonus':vb,'social_benefits':sb,'notice':notice,'total':total}
