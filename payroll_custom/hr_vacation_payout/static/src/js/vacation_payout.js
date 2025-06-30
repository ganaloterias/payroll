/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

// Patch para mejorar la vista de lista
patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        this.addVacationPayoutClasses();
    },

    addVacationPayoutClasses() {
        if (this.props.list.resModel === 'hr.vacation.payout') {
            this.props.list.className += ' o_hr_vacation_payout';
        }
    },

    getRowClass(record) {
        let classes = super.getRowClass(record);
        if (this.props.list.resModel === 'hr.vacation.payout') {
            classes += ` o_vacation_state_${record.data.state}`;
        }
        return classes;
    }
});

// Componente para mostrar estadísticas rápidas
class VacationPayoutStats extends owl.Component {
    setup() {
        super.setup();
        this.stats = this.props.stats;
    }
}

VacationPayoutStats.template = 'hr_vacation_payout.VacationPayoutStats';
VacationPayoutStats.props = {
    stats: { type: Object, optional: true }
};

// Componente para el dashboard
class VacationPayoutDashboard extends owl.Component {
    setup() {
        super.setup();
        this.loadStats();
    }

    async loadStats() {
        const stats = await this.orm.call(
            'hr.vacation.payout',
            'get_dashboard_stats',
            []
        );
        this.stats = stats;
        this.render();
    }
}

VacationPayoutDashboard.template = 'hr_vacation_payout.VacationPayoutDashboard';
VacationPayoutDashboard.components = { VacationPayoutStats };

// Registrar componentes
registry.category("components").add("VacationPayoutStats", VacationPayoutStats);
registry.category("components").add("VacationPayoutDashboard", VacationPayoutDashboard);

// Mejoras para el wizard
class VacationPayoutWizard extends owl.Component {
    setup() {
        super.setup();
        this.state = owl.useState({
            loading: false,
            error: null
        });
    }

    async createPayout() {
        this.state.loading = true;
        this.state.error = null;
        
        try {
            const result = await this.orm.call(
                'hr.vacation.payout.wizard',
                'action_create_payout',
                [this.props.record.resId]
            );
            
            if (result) {
                this.env.services.action.doAction(result);
            }
        } catch (error) {
            this.state.error = error.message;
        } finally {
            this.state.loading = false;
        }
    }
}

VacationPayoutWizard.template = 'hr_vacation_payout.VacationPayoutWizard';

// Registrar el wizard
registry.category("components").add("VacationPayoutWizard", VacationPayoutWizard);

// Mejoras para el calendario
class VacationCalendar extends owl.Component {
    setup() {
        super.setup();
        this.addVacationCalendarStyles();
    }

    addVacationCalendarStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .o_calendar_event.o_vacation_event {
                background-color: #28a745 !important;
                border-color: #1e7e34 !important;
            }
            .o_calendar_event.o_vacation_paid {
                background-color: #17a2b8 !important;
                border-color: #117a8b !important;
            }
        `;
        document.head.appendChild(style);
    }
}

VacationCalendar.template = 'hr_vacation_payout.VacationCalendar';

// Registrar el calendario
registry.category("components").add("VacationCalendar", VacationCalendar);

// Utilidades para el módulo
export const VacationPayoutUtils = {
    formatCurrency(amount, currency) {
        return new Intl.NumberFormat('es-VE', {
            style: 'currency',
            currency: currency || 'VES'
        }).format(amount);
    },

    formatDate(date) {
        return new Intl.DateTimeFormat('es-VE', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        }).format(new Date(date));
    },

    getStateColor(state) {
        const colors = {
            'draft': '#ffc107',
            'validated': '#17a2b8',
            'done': '#28a745',
            'rejected': '#dc3545'
        };
        return colors[state] || '#6c757d';
    },

    getStateLabel(state) {
        const labels = {
            'draft': 'Borrador',
            'validated': 'Validado',
            'done': 'Pagado',
            'rejected': 'Rechazado'
        };
        return labels[state] || state;
    }
};

// Exportar para uso global
window.VacationPayoutUtils = VacationPayoutUtils; 