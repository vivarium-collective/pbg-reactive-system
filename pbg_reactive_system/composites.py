"""MAPK signalling cycle as a Bigraphical Reactive System.

The biology
-----------
The MAP-kinase cascade is the canonical signal-transduction relay
in mammalian cells. We model just its last catalytic step:

    free MEK + free ERK   →   MEK·pERK   →   free MEK + free pERK

* **MEK1** (MAP2K1) is a 43 kDa serine/threonine kinase that sits
  in the cytoplasm and dual-phosphorylates ERK on its activation
  loop (Thr-Glu-Tyr motif).  PDB **3EQH** (Ohren et al. 2004).
* **ERK2** (MAPK1) has the classic bilobal kinase fold.  PDB
  **1ERK** (Zhang et al. 1994, inactive form).  After dual
  phosphorylation it adopts the active conformation **2ERK**
  (Canagarajah et al. 1997).  In our cycle ERK is treated strictly
  as MEK's substrate — its own kinase activity is downstream.
* **NPC** (nuclear pore complex) is the gateway to the nucleus
  for phospho-ERK; we draw it with the canonical eight-fold
  symmetry (Lin & Hoelz 2019).
* Crucially MEK is *active-site limited*: it has one catalytic
  cleft, so it can be in complex with at most one ERK at a time.

Mapping the biology onto a bigraph (Milner 2009)
------------------------------------------------
A bigraph has two graphs sharing a common node set: a **place
graph** for spatial nesting, and a **link graph** for
connectivity.  We use one node per molecule / compartment, with a
``_type`` label.

Place graph: ``Cell ⊃ Compartments ⊃ {NPC, MEK, ERK, pERK}``.
Link graph: a single shared edge between MEK's catalytic port and
the substrate's docking port whenever they're in complex.

Reaction rules (Gillespie SSA, propensity = ``rate × |matches|``):

* ``phosphorylate``      (k = 2.0)
* ``dissociate``         (k = 0.5)
* ``dephosphorylate``    (k = 0.4)
* ``translocate_erk_in`` (k = 1.0)
* ``translocate_erk_out``(k = 1.0)
* ``translocate_perk_in``(k = 2.0)
* ``translocate_perk_out``(k = 0.1)

See ``references/brs_mapk.md`` in this repo for citations.
"""
from bigraph_schema.schema import Site
from bigraph_schema.assembly import ReactionRule, LinkVar, Absent

from .types import register_mapk_types


def _erk(name):
    """Free ERK substrate: an ``ERK``-control node carrying its
    individual identity in the ``name`` field. No ``outputs``
    means no docking bond — i.e. unbound."""
    return {'_type': 'ERK', 'name': name}


# ── Reaction rules ──────────────────────────────────────────────────


def rule_phosphorylate():
    """Free MEK + free ERK in the same compartment form the
    Michaelis complex.

    Biology:
        Pre:   MEK (free, no substrate in active site)
             + ERK (free, unphosphorylated)
        Post:  MEK·pERK   (covalently transferred phosphate, drawn
                          here as a shared link-graph edge)
    """
    return ReactionRule(
        redex={
            'compartment': {
                '_type': 'Compartment',
                'enzyme': {
                    '_type': 'MEK',
                    'outputs': Absent()},
                'substrate': {
                    '_type': 'ERK',
                    'name': Site(),
                    'outputs': Absent()},
                'bystanders': Site()}},
        reactum={
            'compartment': {
                '_type': 'Compartment',
                'enzyme': {
                    '_type': 'MEK',
                    'outputs': {'enzyme_port': LinkVar('bond')}},
                'substrate': {
                    '_type': 'pERK',
                    'name': Site(),
                    'outputs': {'substrate_port': LinkVar('bond')}},
                'bystanders': Site()}},
        instantiation={'bystanders': 'bystanders', 'name': 'name'},
        rate=2.0,
        label='phosphorylate')


def rule_dissociate():
    """The MEK·pERK complex dissociates inside its compartment.

    Biology:
        Pre:   MEK·pERK
        Post:  free MEK + free pERK
    """
    return ReactionRule(
        redex={
            'compartment': {
                '_type': 'Compartment',
                'enzyme': {
                    '_type': 'MEK',
                    'outputs': {'enzyme_port': LinkVar('bond')}},
                'substrate': {
                    '_type': 'pERK',
                    'name': Site(),
                    'outputs': {'substrate_port': LinkVar('bond')}},
                'bystanders': Site()}},
        reactum={
            'compartment': {
                '_type': 'Compartment',
                'enzyme': {'_type': 'MEK'},
                'substrate': {'_type': 'pERK', 'name': Site()},
                'bystanders': Site()}},
        instantiation={'bystanders': 'bystanders', 'name': 'name'},
        rate=0.5,
        label='dissociate')


def rule_dephosphorylate():
    """A nuclear MAP-kinase phosphatase removes the phosphate from
    a free pERK in the nucleus, returning it to ERK."""
    return ReactionRule(
        redex={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'inner': {
                    '_type': 'Compartment',
                    'kind': {'_type': 'Nucleus'},
                    'substrate': {
                        '_type': 'pERK',
                        'name': Site(),
                        'outputs': Absent()},
                    'inner_rest': Site()},
                'outer_rest': Site()},
        },
        reactum={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'inner': {
                    '_type': 'Compartment',
                    'kind': {'_type': 'Nucleus'},
                    'substrate': {'_type': 'ERK', 'name': Site()},
                    'inner_rest': Site()},
                'outer_rest': Site()},
        },
        instantiation={
            'outer_rest': 'outer_rest',
            'inner_rest': 'inner_rest',
            'name': 'name'},
        rate=0.4,
        label='dephosphorylate')


def rule_translocate_erk_in():
    """A free unphosphorylated ERK descends from cytoplasm into a
    child compartment (nucleus or ER lumen)."""
    return ReactionRule(
        redex={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'substrate': {
                    '_type': 'ERK',
                    'name': Site()},
                'inner': {
                    '_type': 'Compartment',
                    'inner_rest': Site()},
                'outer_rest': Site()},
        },
        reactum={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'inner': {
                    '_type': 'Compartment',
                    'inner_rest': Site(),
                    'substrate': {'_type': 'ERK', 'name': Site()}},
                'outer_rest': Site()},
        },
        instantiation={
            'outer_rest': 'outer_rest',
            'inner_rest': 'inner_rest',
            'name': 'name'},
        rate=1.0,
        label='translocate_erk_in')


def rule_translocate_erk_out():
    """A free unphosphorylated ERK ascends from a child compartment
    back into cytoplasm."""
    return ReactionRule(
        redex={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'inner': {
                    '_type': 'Compartment',
                    'substrate': {
                        '_type': 'ERK',
                        'name': Site()},
                    'inner_rest': Site()},
                'outer_rest': Site()},
        },
        reactum={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'inner': {
                    '_type': 'Compartment',
                    'inner_rest': Site()},
                'substrate': {'_type': 'ERK', 'name': Site()},
                'outer_rest': Site()},
        },
        instantiation={
            'outer_rest': 'outer_rest',
            'inner_rest': 'inner_rest',
            'name': 'name'},
        rate=1.0,
        label='translocate_erk_out')


def rule_translocate_perk_in():
    """Active nuclear import of free phospho-ERK."""
    return ReactionRule(
        redex={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'substrate': {
                    '_type': 'pERK',
                    'name': Site(),
                    'outputs': Absent()},
                'inner': {
                    '_type': 'Compartment',
                    'kind': {'_type': 'Nucleus'},
                    'inner_rest': Site()},
                'outer_rest': Site()},
        },
        reactum={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'inner': {
                    '_type': 'Compartment',
                    'kind': {'_type': 'Nucleus'},
                    'inner_rest': Site(),
                    'substrate': {'_type': 'pERK', 'name': Site()}},
                'outer_rest': Site()},
        },
        instantiation={
            'outer_rest': 'outer_rest',
            'inner_rest': 'inner_rest',
            'name': 'name'},
        rate=2.0,
        label='translocate_perk_in')


def rule_translocate_perk_out():
    """Slow nuclear export / leak of free phospho-ERK."""
    return ReactionRule(
        redex={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'inner': {
                    '_type': 'Compartment',
                    'kind': {'_type': 'Nucleus'},
                    'substrate': {
                        '_type': 'pERK',
                        'name': Site(),
                        'outputs': Absent()},
                    'inner_rest': Site()},
                'outer_rest': Site()},
        },
        reactum={
            'outer': {
                '_type': 'Compartment',
                'kind': {'_type': 'Cytoplasm'},
                'inner': {
                    '_type': 'Compartment',
                    'kind': {'_type': 'Nucleus'},
                    'inner_rest': Site()},
                'substrate': {'_type': 'pERK', 'name': Site()},
                'outer_rest': Site()},
        },
        instantiation={
            'outer_rest': 'outer_rest',
            'inner_rest': 'inner_rest',
            'name': 'name'},
        rate=0.1,
        label='translocate_perk_out')


def mapk_rules():
    """All seven rules together — the MAPK BRS we simulate."""
    return [
        rule_phosphorylate(),
        rule_dissociate(),
        rule_dephosphorylate(),
        rule_translocate_erk_in(),
        rule_translocate_erk_out(),
        rule_translocate_perk_in(),
        rule_translocate_perk_out(),
    ]


# ── Initial-state builder ──────────────────────────────────────────


def initial_mapk_state(seed=0):
    """Nested-compartment cell with MEK in the cytoplasm and an
    assortment of ERK / pERK copies seeded to drive the cycle.

    Place graph (nested):

        Cell
        └── cytoplasm    (MEK, erk1, erk2, erk0)
            ├── nucleus  (empty initially; pERK accumulates here)
            └── er_lumen (erk3)
    """
    return {
        '_type': 'Cell',
        'cytoplasm': {
            '_type': 'Compartment',
            'kind': {'_type': 'Cytoplasm'},
            'mek':  {'_type': 'MEK'},
            'erk0': {'_type': 'pERK', 'name': 'erk0'},
            'erk1': _erk('erk1'),
            'erk2': _erk('erk2'),
            'nucleus': {
                '_type': 'Compartment',
                'kind': {'_type': 'Nucleus'},
            },
            'er_lumen': {
                '_type': 'Compartment',
                'kind': {'_type': 'ERLumen'},
                'erk3': _erk('erk3'),
            },
        },
    }


# =====================================================================
# Helpers for analysis (substrate counts, structure traversal)
# =====================================================================


def list_substrates(state):
    """Return ``[(name, compartment, control, bound)]`` for every
    ERK / pERK node in the cell."""
    out = []

    def walk(node, comp_name=None):
        if not isinstance(node, dict):
            return
        ctrl = node.get('_type', '')
        if ctrl in ('ERK', 'pERK'):
            name = node.get('name', '?')
            outs = node.get('outputs')
            bound = isinstance(outs, dict) and bool(outs)
            out.append((name, comp_name, ctrl, bound))
            return
        for k, v in node.items():
            if isinstance(v, dict):
                next_comp = (
                    k if v.get('_type') == 'Compartment' else comp_name)
                walk(v, comp_name=next_comp)

    walk(state)
    return out


def count_substrates_per_compartment(state):
    """``{compartment_name: (free_count, bound_count, perk_count)}``."""
    counts = {}
    for name, comp, ctrl, bound in list_substrates(state):
        if comp is None:
            continue
        free, perk_free, bound_count = counts.get(comp, (0, 0, 0))
        if ctrl == 'ERK':
            free += 1
        elif ctrl == 'pERK' and bound:
            bound_count += 1
        elif ctrl == 'pERK':
            perk_free += 1
        counts[comp] = (free, perk_free, bound_count)
    return counts


# =====================================================================
# Composite document builder
# =====================================================================


def get_brs_mapk_doc(core=None, config=None):
    """Build a process-bigraph document for the MAPK BRS example.

    The document wires a single ``BigraphicalReactiveSystem``
    Process against a typed ``cell`` store. Each tick advances
    simulation time by ``interval`` and fires zero or more rule
    matches (under Gillespie SSA). An explicit emitter is included
    so the run produces a time series.

    If ``core`` is provided, the MAPK bigraph signature is also
    registered onto it as schema types — making the controls
    first-class typesystem citizens that can later carry methods.
    """
    from process_bigraph.emitter import emitter_from_wires
    config = config or {}
    if core is not None:
        register_mapk_types(core)
    return {
        'schema': {'cell': 'tree[node]'},
        'state': {
            'cell': initial_mapk_state(),
            'brs': {
                '_type': 'process',
                'address': (
                    'local:!pbg_reactive_system.processes'
                    '.BigraphicalReactiveSystem'),
                'config': {
                    'rules': mapk_rules(),
                    'mode': config.get('mode', 'gillespie'),
                    'seed': config.get('seed', 42),
                    'max_per_tick': config.get('max_per_tick', 10**6),
                },
                'inputs': {'state': ['cell']},
                'outputs': {'state': ['cell']},
                'interval': config.get('interval', 1.0),
            },
            'emitter': emitter_from_wires(
                {'global_time': ['global_time'], 'cell': ['cell']}),
        }}


# =====================================================================
# Backward-compatibility aliases
# =====================================================================

building_rules = mapk_rules
initial_building_state = initial_mapk_state
get_brs_building_doc = get_brs_mapk_doc
