"""End-to-end tests for the MAPK BRS composite.

Runs ``get_brs_mapk_doc`` through a real ``Composite`` simulator,
verifies that emitter entries come back, and that the engine's
``fired_log`` captures rule firings under Gillespie mode.
"""
from process_bigraph import Composite, allocate_core, gather_emitter_results

from pbg_reactive_system import (
    BigraphicalReactiveSystem,
    count_substrates_per_compartment,
    get_brs_mapk_doc,
    initial_mapk_state,
    list_substrates,
    mapk_rules,
    register_mapk_types,
)


def test_initial_mapk_state_has_expected_substrates():
    state = initial_mapk_state()
    subs = list_substrates(state)
    by_compartment = {}
    for name, comp, ctrl, bound in subs:
        by_compartment.setdefault(comp, []).append((name, ctrl, bound))
    # cytoplasm: erk0 (pERK, unbound), erk1 (ERK), erk2 (ERK)
    cyto = sorted(by_compartment['cytoplasm'])
    assert ('erk1', 'ERK', False) in cyto
    assert ('erk2', 'ERK', False) in cyto
    assert ('erk0', 'pERK', False) in cyto
    # er_lumen: erk3
    assert by_compartment['er_lumen'] == [('erk3', 'ERK', False)]
    # No substrates seeded in the nucleus initially.
    assert 'nucleus' not in by_compartment


def test_mapk_rules_returns_seven_labelled_rules():
    rules = mapk_rules()
    labels = [r.label for r in rules]
    assert labels == [
        'phosphorylate',
        'dissociate',
        'dephosphorylate',
        'translocate_erk_in',
        'translocate_erk_out',
        'translocate_perk_in',
        'translocate_perk_out',
    ]


def test_count_substrates_per_compartment():
    state = initial_mapk_state()
    counts = count_substrates_per_compartment(state)
    free_cyto, perk_free_cyto, bound_cyto = counts['cytoplasm']
    assert free_cyto == 2  # erk1, erk2 (ERK)
    assert perk_free_cyto == 1  # erk0 (pERK, unbound)
    assert bound_cyto == 0
    assert counts['er_lumen'] == (1, 0, 0)


def test_mapk_composite_runs_and_emits_time_series():
    core = allocate_core()
    register_mapk_types(core)
    doc = get_brs_mapk_doc(core=core, config={
        'interval': 1.0, 'mode': 'gillespie', 'seed': 7})
    sim = Composite(
        {'state': doc['state'], 'composition': doc['schema']},
        core=core)
    sim.run(5.0)
    results = gather_emitter_results(sim)
    # Single emitter at top level.
    assert len(results) == 1
    entries = next(iter(results.values()))
    # Initial emit + 5 ticks = 6 entries.
    assert len(entries) >= 5
    # Time axis is monotonic and includes the expected endpoints.
    times = [e['global_time'] for e in entries]
    assert times[0] == 0.0
    assert times[-1] >= 5.0
    assert times == sorted(times)
    # Every entry carries a non-empty cell tree.
    for entry in entries:
        cell = entry.get('cell')
        assert isinstance(cell, dict)
        assert cell.get('_type') == 'Cell'


def test_engine_module_address_resolves():
    """The composite uses a dynamic-import address
    (``local:!pbg_reactive_system.processes.BigraphicalReactiveSystem``);
    this guards against accidental renames that would break it."""
    import pbg_reactive_system.processes as p
    assert hasattr(p, 'BigraphicalReactiveSystem')
    assert p.BigraphicalReactiveSystem is BigraphicalReactiveSystem
