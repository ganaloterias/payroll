# -*- coding: utf-8 -*-

from . import controllers
from . import models

from .data.post_install import _add_rule_to_structures

def post_init_hook(cr, registry=None):
    _add_rule_to_structures(cr, registry)
