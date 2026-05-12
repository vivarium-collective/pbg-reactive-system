# pbg-reactive-system

[![demo](https://img.shields.io/badge/▶%20live%20demo-MAPK%20BRS%20report-1b9e77)](https://vivarium-collective.github.io/pbg-reactive-system/)

A `process-bigraph` wrapper for **Milner-style Bigraphical Reactive
Systems**, with a worked **MAPK signalling cycle** as the running
example.

## ▶ Demo

The MAPK BRS demo runs the model under Gillespie SSA, renders cell-
cartoon snapshots, a smooth animation, the rule catalog (redex →
reactum, with real state before / after), and a population time
series.

- **▶ Live:** **<https://vivarium-collective.github.io/pbg-reactive-system/>**
- **In-repo:** [`demo/report.html`](demo/report.html)
- **Regenerate locally:**

  ```bash
  uv pip install -e ".[dev]"
  python demo/demo_report.py
  ```

  The script runs the simulation, writes intermediate PNGs / GIF /
  markdown to `demo/_artifacts/`, assembles a self-contained
  `demo/report.html`, and opens it in your browser.

## What's inside

- A generic Process — `BigraphicalReactiveSystem` — that fires
  Milner-style redex → reactum rewrite rules on a time-stepped
  schedule. Three firing modes: `deterministic`, `stochastic`,
  and Gillespie `gillespie` SSA.
- A worked MAPK example: seven rules
  (`phosphorylate`, `dissociate`, `dephosphorylate`,
  `translocate_erk_in/out`, `translocate_perk_in/out`) over a
  nested cell bigraph (`Cell ⊃ Cytoplasm ⊃ {Nucleus, ERLumen}`),
  with MEK·pERK complexes carried by the link graph.
- Plotting helpers in `pbg_reactive_system.mapk_plots` —
  bilobal-kinase cartoons, eight-fold-symmetric NPC glyphs,
  cubic ease-in-out animation across rule firings.

See [`references/brs_mapk.md`](references/brs_mapk.md) for the
formalism + biology citations.

## Installation

```bash
# From PyPI (once published):
pip install pbg-reactive-system

# With uv:
uv pip install pbg-reactive-system

# For development (editable):
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```

The `[plots]` extra pulls in `matplotlib`, `imageio`, and
`bigraph-viz` so the demo and `plot_brs_mapk` work. Core engine
usage only needs the base dependencies.

## Quick start

```python
from process_bigraph import Composite, allocate_core, gather_emitter_results
from pbg_reactive_system import get_brs_mapk_doc, register_mapk_types

core = allocate_core()
register_mapk_types(core)

doc = get_brs_mapk_doc(
    core=core,
    config={'interval': 1.0, 'mode': 'gillespie', 'seed': 42})

sim = Composite(
    {'state': doc['state'], 'composition': doc['schema']},
    core=core)
sim.run(50.0)

results = gather_emitter_results(sim)
series = next(iter(results.values()))
print(f'got {len(series)} snapshots; t_final={series[-1]["global_time"]}')
```

To drive the engine directly with your own rules:

```python
from bigraph_schema.assembly import ReactionRule
from bigraph_schema.schema import Site
from process_bigraph import allocate_core
from pbg_reactive_system import BigraphicalReactiveSystem

core = allocate_core()
core.register_types({'World': {'_inherit': 'node'},
                     'Bag':   {'_inherit': 'node'},
                     'Red':   {'_inherit': 'node'},
                     'Blue':  {'_inherit': 'node'}})

flip = ReactionRule(
    redex={'bag': {'_type': 'Bag', 'tok': {'_type': 'Red'}, 'rest': Site()}},
    reactum={'bag': {'_type': 'Bag', 'tok': {'_type': 'Blue'}, 'rest': Site()}},
    instantiation={'rest': 'rest'},
    rate=1.0,
    label='flip')

proc = BigraphicalReactiveSystem(
    config={'rules': [flip], 'mode': 'gillespie', 'seed': 0},
    core=core)
state = {'_type': 'World', 'bag': {'_type': 'Bag',
    'r0': {'_type': 'Red'}, 'r1': {'_type': 'Red'}}}
out = proc.update({'state': state}, interval=5.0)
```

## API

| Symbol | What it is |
|---|---|
| `BigraphicalReactiveSystem` | `process_bigraph.Process`; fires rules on each tick. |
| `register_mapk_types(core)` | Register `Cell`, `Compartment`, `MEK`, `ERK`, `pERK`, `NPC`, `Cytoplasm`, `Nucleus`, `ERLumen` sorts onto a core. |
| `mapk_rules()` | The seven MAPK rules as a list of `ReactionRule`s. |
| `initial_mapk_state(seed=0)` | The seeded nested cell bigraph. |
| `get_brs_mapk_doc(core=None, config=None)` | Composite document wiring the BRS Process against the cell store + an emitter. |
| `list_substrates(state)` | `[(name, compartment, control, bound)]` for every ERK / pERK. |
| `count_substrates_per_compartment(state)` | `{comp: (free, perk_free, bound)}` for plotting. |
| `plot_brs_mapk(results, state, config)` | Five-panel summary: bigraph, time series, snapshots, rule catalog, animation. |

The seven rule constructors `rule_phosphorylate`, `rule_dissociate`,
`rule_dephosphorylate`, `rule_translocate_erk_in`,
`rule_translocate_erk_out`, `rule_translocate_perk_in`,
`rule_translocate_perk_out` are also exported individually so you
can swap or extend the set.

## Limitations and assumptions

- The matcher operates on `_type` string equality on registered
  schema types. Value-based predicates (e.g. "match a node whose
  `color` field equals `red`") are not supported by the redex
  language — encode such states as distinct sorts instead
  (`Red` vs `Blue` rather than `Token` with a `color` field).
- Rule application uses the primitives in `bigraph_schema.assembly`
  (`find_matches`, `fire_rule`). Behaviour and semantics inherit
  whatever those primitives provide.
- The MAPK plotting helpers assume the specific cell anatomy
  (cytoplasm with nested nucleus + ER lumen). Adapt or replace
  them for a different bigraph signature.

## Running the tests

```bash
uv pip install -e ".[dev]"
pytest
```

10 unit + integration tests; all offline.

## License

MIT.
