"""pbg-reactive-system: a process-bigraph wrapper for
Milner-style Bigraphical Reactive Systems, with a worked MAPK
signalling example."""

from .processes import BigraphicalReactiveSystem
from .types import (
    MAPK_SORTS, MAPK_CONTROLS, MAPK_TYPE_SCHEMAS,
    register_mapk_types, register_types,
)
from .composites import (
    mapk_rules, initial_mapk_state, get_brs_mapk_doc,
    list_substrates, count_substrates_per_compartment,
    # Per-rule constructors
    rule_phosphorylate, rule_dissociate, rule_dephosphorylate,
    rule_translocate_erk_in, rule_translocate_erk_out,
    rule_translocate_perk_in, rule_translocate_perk_out,
    # Backward-compat aliases
    building_rules, initial_building_state, get_brs_building_doc,
)

__all__ = [
    'BigraphicalReactiveSystem',
    'MAPK_SORTS', 'MAPK_CONTROLS', 'MAPK_TYPE_SCHEMAS',
    'register_mapk_types', 'register_types',
    'mapk_rules', 'initial_mapk_state', 'get_brs_mapk_doc',
    'list_substrates', 'count_substrates_per_compartment',
    'rule_phosphorylate', 'rule_dissociate', 'rule_dephosphorylate',
    'rule_translocate_erk_in', 'rule_translocate_erk_out',
    'rule_translocate_perk_in', 'rule_translocate_perk_out',
    'building_rules', 'initial_building_state', 'get_brs_building_doc',
]
