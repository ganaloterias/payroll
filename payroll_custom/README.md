# Suite de Módulos de Nómina Personalizada

Esta carpeta contiene una suite completa de módulos personalizados para la gestión de nómina en Odoo 18, específicamente diseñados para cumplir con las regulaciones venezolanas y optimizar los procesos de recursos humanos.

## Módulos Incluidos

### 1. **hr_contract_custom** - Contratos Multimoneda
- Soporte avanzado para contratos con múltiples monedas
- Gestión de líneas de salario por moneda
- Selección automática de salario según moneda de nómina
- Histórico de cambios salariales
- Integración completa con nómina

### 2. **hr_loan_management** - Gestión de Préstamos a Empleados
- Gestión completa de préstamos (crear, aprobar, procesar, completar)
- Generación automática de cuotas mensuales
- Integración automática con nómina para descuentos
- Estados de flujo controlados
- Límite de 10 cuotas máximo por préstamo

### 3. **hr_payroll_custom** - Mejoras Personalizadas de Nómina
- Generación masiva de archivos TXT para nómina
- Extensiones de datos bancarios para Venezuela
- Gestión de dependientes de empleados
- Cálculos optimizados de días trabajados
- Integración con múltiples módulos HR

### 4. **hr_vacation_payout** - Pago de Vacaciones Venezuela
- Cálculo automático según LOTTT
- Gestión de bono vacacional
- Generación automática de ausencias
- Integración completa con nómina
- Validaciones según ley venezolana

### 5. **hr_venezuelan_liquidation** - Liquidaciones Venezuela
- Cálculo automático según LOTTT
- Gestión de prestaciones sociales
- Cálculo de preaviso según antigüedad
- Integración con nómina
- Estados de flujo controlados

### 6. **hr_security** - Gestión de Seguridad de RRHH
- Control granular de acceso por módulo
- Grupos de seguridad específicos
- Reglas de acceso personalizadas
- Auditoría de acceso y cambios
- Protección de datos sensibles

### 7. **payroll_management** - Gestión Avanzada de Nómina
- Configuración centralizada de módulos
- Gestión de parámetros de validación
- Control de límites y restricciones
- Configuración de reportes
- Integración con contabilidad

## Instalación

1. Copiar todos los módulos a la carpeta `addons` de Odoo
2. Actualizar la lista de aplicaciones en Odoo
3. Instalar los módulos en el siguiente orden:
   - hr_contract_custom
   - hr_loan_management
   - hr_vacation_payout
   - hr_venezuelan_liquidation
   - hr_security
   - hr_payroll_custom
   - payroll_management

## Dependencias

- Odoo 18.0
- Módulos base: hr, payroll, hr_contract, hr_holidays
- Módulos adicionales según integración requerida

## Características Principales

- **Cumplimiento Legal**: Todos los módulos están diseñados para cumplir con la LOTTT venezolana
- **Integración Completa**: Los módulos trabajan en conjunto para una gestión integral
- **Interfaz Moderna**: Vistas optimizadas con Kanban, gráficos y reportes
- **Validaciones Robustas**: Control de datos y validaciones automáticas
- **Auditoría Completa**: Seguimiento de cambios y actividades
- **Rendimiento Optimizado**: Cálculos eficientes y arquitectura escalable

## Soporte

Para soporte técnico o consultas sobre la implementación, contactar al equipo de desarrollo.

## Licencia

Todos los módulos están bajo licencia LGPL-3. 