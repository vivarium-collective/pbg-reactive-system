"""Engine-level tests for BigraphicalReactiveSystem.

Tests the rule-firing engine directly with a tiny hand-built bigraph
and a one-rule reaction system, so failures isolate engine behavior
from the larger MAPK composite.
"""
import pytest

from bigraph_schema.assembly import ReactionRule
from bigraph_schema.schema import Site
from process_bigraph import allocate_core

from pbg_reactive_system import BigraphicalReactiveSystem


@pytest.fixture
def core():
    """A core with the toy sorts used by the engine tests registered.

    The bigraph matcher needs each ``_type`` it walks over to be a
    registered schema type so it descends recursively.
    """
    c = allocate_core()
    c.register_types({
        'World': {'_inherit': 'node'},
        'Bag':   {'_inherit': 'node'},
        'Red':   {'_inherit': 'node'},
        'Blue':  {'_inherit': 'node'},
        'A':     {'_inherit': 'node'},
        'B':     {'_inherit': 'node'},
        'X':     {'_inherit': 'node'},
    })
    return c


def _color_flip_rule(label='flip'):
    """Toy rule: a ``Red`` token inside a ``Bag`` flips to ``Blue``."""
    return ReactionRule(
        redex={'bag': {
            '_type': 'Bag',
            'tok': {'_type': 'Red'},
            'rest': Site()}},
        reactum={'bag': {
            '_type': 'Bag',
            'tok': {'_type': 'Blue'},
            'rest': Site()}},
        instantiation={'rest': 'rest'},
        rate=1.0,
        label=label)


def _toy_state(n_red=3, n_blue=0):
    bag = {'_type': 'Bag'}
    for i in range(n_red):
        bag[f'r{i}'] = {'_type': 'Red'}
    for i in range(n_blue):
        bag[f'b{i}'] = {'_type': 'Blue'}
    return {'_type': 'World', 'bag': bag}


def _bag(state):
    """Extract the Bag subtree out of the top-level World wrapper."""
    return state['bag']


def _token_type_counts(bag):
    """Count how many Red / Blue tokens are in the Bag."""
    types = [
        v.get('_type') for v in bag.values()
        if isinstance(v, dict) and v.get('_type') in ('Red', 'Blue')]
    return {'Red': types.count('Red'), 'Blue': types.count('Blue')}


def test_engine_deterministic_one_firing_per_tick(core):
    rules = [_color_flip_rule()]
    proc = BigraphicalReactiveSystem(
        config={'rules': rules, 'mode': 'deterministic',
                'max_per_tick': 1},
        core=core)
    state = _toy_state(n_red=3)
    out = proc.update({'state': state}, interval=1.0)
    assert 'state' in out
    counts = _token_type_counts(_bag(out['state']))
    # Exactly one Red → Blue
    assert counts == {'Red': 2, 'Blue': 1}


def test_engine_deterministic_max_per_tick_drains_all(core):
    rules = [_color_flip_rule()]
    proc = BigraphicalReactiveSystem(
        config={'rules': rules, 'mode': 'deterministic',
                'max_per_tick': 10},
        core=core)
    state = _toy_state(n_red=3)
    out = proc.update({'state': state}, interval=1.0)
    counts = _token_type_counts(_bag(out['state']))
    # All three flipped
    assert counts == {'Red': 0, 'Blue': 3}


def test_engine_returns_empty_when_no_match(core):
    rules = [_color_flip_rule()]
    proc = BigraphicalReactiveSystem(
        config={'rules': rules, 'mode': 'deterministic'},
        core=core)
    out = proc.update({'state': _toy_state(n_red=0, n_blue=3)}, interval=1.0)
    # No matches → no state update returned.
    assert out == {}


def test_engine_gillespie_progresses_and_logs(core):
    rules = [_color_flip_rule()]
    proc = BigraphicalReactiveSystem(
        config={'rules': rules, 'mode': 'gillespie',
                'seed': 0},
        core=core)
    state = _toy_state(n_red=5)
    out = proc.update({'state': state}, interval=10.0)
    # Plenty of time + nonzero propensity → must have fired at least once.
    assert 'state' in out
    assert len(proc.fired_log) >= 1
    # All firings labeled with our rule
    assert all(label == 'flip' for _, label, _ in proc.fired_log)


def test_engine_stochastic_picks_by_rate(core):
    """Two rules with very different rates: high-rate rule should be
    picked overwhelmingly in stochastic mode."""
    high = ReactionRule(
        redex={'bag': {
            '_type': 'Bag',
            'tok': {'_type': 'A'},
            'rest': Site()}},
        reactum={'bag': {
            '_type': 'Bag',
            'tok': {'_type': 'X'},
            'rest': Site()}},
        instantiation={'rest': 'rest'},
        rate=1000.0, label='high')
    low = ReactionRule(
        redex={'bag': {
            '_type': 'Bag',
            'tok': {'_type': 'B'},
            'rest': Site()}},
        reactum={'bag': {
            '_type': 'Bag',
            'tok': {'_type': 'X'},
            'rest': Site()}},
        instantiation={'rest': 'rest'},
        rate=0.001, label='low')
    state = {
        '_type': 'World',
        'bag': {'_type': 'Bag',
                'a': {'_type': 'A'},
                'b': {'_type': 'B'}},
    }
    proc = BigraphicalReactiveSystem(
        config={'rules': [high, low], 'mode': 'stochastic',
                'seed': 1},
        core=core)
    # Single-firing tick; with 1000:0.001 odds the high-rate rule wins.
    out = proc.update({'state': state}, interval=1.0)
    bag = _bag(out['state'])
    types_seen = {
        v.get('_type') for v in bag.values() if isinstance(v, dict)}
    assert 'X' in types_seen
