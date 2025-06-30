# -*- coding: utf-8 -*-

from . import models
from . import wizard

def post_init_hook(cr, registry=None):
    """Hook que se ejecuta después de la instalación del módulo."""
    try:
        from .data.post_install import post_init_hook as _post_init_hook
        _post_init_hook(cr, registry)
    except Exception as e:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.error(f"Error en post_init_hook de hr_vacation_payout: {str(e)}")
