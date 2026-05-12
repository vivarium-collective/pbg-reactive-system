"""Generate the MAPK BRS demo report.

Runs the MAPK composite to completion, calls the legacy
``plot_brs_mapk`` to produce PNG figures + the smooth animation
GIF + markdown explainer, and assembles everything into a single
self-contained ``demo/report.html``.

The report inlines every image as a base64 data URI so the HTML
is portable: you can email it, drop it on GitHub Pages, or open
it offline.
"""
import base64
import json
import os
import time
import webbrowser

from process_bigraph import (
    Composite, allocate_core, gather_emitter_results)

from pbg_reactive_system import (
    get_brs_mapk_doc, register_mapk_types)
from pbg_reactive_system.mapk_plots import plot_brs_mapk


HERE = os.path.dirname(os.path.abspath(__file__))


def run_simulation(total_time=120.0, interval=1.0, seed=42):
    """Run the MAPK BRS for ``total_time`` ticks and return
    ``(results, initial_state, elapsed_seconds)``."""
    core = allocate_core()
    register_mapk_types(core)
    doc = get_brs_mapk_doc(core=core, config={
        'interval': interval,
        'mode': 'gillespie',
        'seed': seed,
    })
    initial_state = doc['state']['cell']
    sim = Composite(
        {'state': doc['state'], 'composition': doc['schema']},
        core=core)
    t0 = time.perf_counter()
    sim.run(total_time)
    elapsed = time.perf_counter() - t0
    results = gather_emitter_results(sim)
    series = next(iter(results.values()))
    return series, initial_state, elapsed


def _data_uri(path, mime):
    with open(path, 'rb') as f:
        b = base64.b64encode(f.read()).decode()
    return f'data:{mime};base64,{b}'


def _maybe_data_uri(path, mime):
    return _data_uri(path, mime) if os.path.exists(path) else None


def render_report(filename, out_dir, results, elapsed,
                  initial_state, total_time, n_emits, output_html):
    """Assemble ``report.html`` from the figures dropped into
    ``out_dir`` by ``plot_brs_mapk``."""
    bigraph_uri = _maybe_data_uri(
        os.path.join(out_dir, f'{filename}_viz.png'), 'image/png')
    timeseries_uri = _maybe_data_uri(
        os.path.join(out_dir, f'{filename}_timeseries.png'), 'image/png')
    snapshots_uri = _maybe_data_uri(
        os.path.join(out_dir, f'{filename}_snapshots.png'), 'image/png')
    trace_uri = _maybe_data_uri(
        os.path.join(out_dir, f'{filename}_trace.png'), 'image/png')
    animation_uri = _maybe_data_uri(
        os.path.join(out_dir, f'{filename}_animation.gif'), 'image/gif')

    overview_path = os.path.join(out_dir, f'{filename}_overview.md')
    overview_md = ''
    if os.path.exists(overview_path):
        with open(overview_path) as f:
            overview_md = f.read()

    state_path = os.path.join(out_dir, f'{filename}_state.json')
    state_json = ''
    if os.path.exists(state_path):
        with open(state_path) as f:
            state_json = f.read()

    def section(title, body, anchor=None):
        anchor_attr = f' id="{anchor}"' if anchor else ''
        return (
            f'<section class="panel"{anchor_attr}>'
            f'<h2>{title}</h2>{body}</section>')

    def img(uri, alt):
        if not uri:
            return f'<p class="missing">[{alt} not produced]</p>'
        return f'<img src="{uri}" alt="{alt}">'

    nav = (
        '<nav class="nav">'
        '<a href="#overview">Overview</a>'
        '<a href="#bigraph">Initial bigraph</a>'
        '<a href="#timeseries">Time series</a>'
        '<a href="#snapshots">Snapshots</a>'
        '<a href="#animation">Animation</a>'
        '<a href="#rules">Rule catalog</a>'
        '<a href="#state">State JSON</a>'
        '</nav>')

    metrics = (
        '<div class="metrics">'
        f'<div class="metric"><span class="label">Simulated ticks</span>'
        f'<span class="value">{total_time:g}</span></div>'
        f'<div class="metric"><span class="label">Emitted snapshots</span>'
        f'<span class="value">{n_emits}</span></div>'
        f'<div class="metric"><span class="label">Wall-clock runtime</span>'
        f'<span class="value">{elapsed:.2f}s</span></div>'
        f'<div class="metric"><span class="label">Mode</span>'
        f'<span class="value">Gillespie SSA</span></div>'
        '</div>')

    overview_html = section(
        'Overview',
        '<div class="markdown overview-grid">'
        + _markdown_to_html(overview_md)
        + '</div>',
        anchor='overview')

    bigraph_html = section(
        'Initial bigraph (place + link graph)',
        img(bigraph_uri, 'initial bigraph'),
        anchor='bigraph')

    timeseries_html = section(
        'Substrate populations through time',
        img(timeseries_uri, 'time series')
        + '<p class="caption">Per-compartment substrate counts under '
        'Gillespie SSA, with rule-firing ticks above the curves.</p>',
        anchor='timeseries')

    snapshots_html = section(
        'Structural snapshots',
        img(snapshots_uri, 'snapshots')
        + '<p class="caption">Cell cartoons at evenly spaced points '
        'in the run — MEK in the cytoplasm, ERK / pERK distributed '
        'across compartments, MEK·pERK bonds drawn as paired '
        'green parallel lines.</p>',
        anchor='snapshots')

    animation_html = section(
        'Smooth animation',
        img(animation_uri, 'animation')
        + '<p class="caption">Cubic ease-in-out interpolation between '
        'snapshots; the title carries the rule that fires during '
        'each transition.</p>',
        anchor='animation')

    rules_html = section(
        'Rule catalog — redex → reactum + state before → after',
        img(trace_uri, 'rule trace')
        + '<p class="caption">Each row shows one rule from '
        '<code>mapk_rules()</code>: left half is the redex / reactum '
        'pattern itself (bigraph-viz), right half is a real before / '
        'after state from the run.</p>',
        anchor='rules')

    state_html = section(
        'Initial composite state',
        '<details><summary>Click to expand the JSON tree</summary>'
        f'<pre class="json">{_escape(state_json)}</pre></details>',
        anchor='state')

    html = HTML_TEMPLATE.format(
        nav=nav,
        metrics=metrics,
        overview=overview_html,
        bigraph=bigraph_html,
        timeseries=timeseries_html,
        snapshots=snapshots_html,
        animation=animation_html,
        rules=rules_html,
        state=state_html,
    )

    with open(output_html, 'w') as f:
        f.write(html)


def _escape(s):
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;'))


def _markdown_to_html(md):
    """A tiny markdown-ish renderer: headings, bold, inline code,
    paragraphs, list items.  Good enough for the explainer; avoids
    a runtime dependency on a markdown library."""
    import re
    lines = md.split('\n')
    out = []
    in_list = False
    for line in lines:
        line = line.rstrip()
        if not line:
            if in_list:
                out.append('</ul>')
                in_list = False
            out.append('')
            continue
        if line.startswith('### '):
            if in_list:
                out.append('</ul>')
                in_list = False
            out.append(f'<h3>{_inline(line[4:])}</h3>')
            continue
        if line.startswith('## '):
            if in_list:
                out.append('</ul>')
                in_list = False
            out.append(f'<h2>{_inline(line[3:])}</h2>')
            continue
        if line.lstrip().startswith('- '):
            if not in_list:
                out.append('<ul>')
                in_list = True
            out.append(f'<li>{_inline(line.lstrip()[2:])}</li>')
            continue
        if in_list:
            out.append('</ul>')
            in_list = False
        out.append(f'<p>{_inline(line)}</p>')
    if in_list:
        out.append('</ul>')
    return '\n'.join(out)


def _inline(s):
    import re
    s = _escape(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    return s


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>pbg-reactive-system — MAPK BRS demo</title>
<style>
  :root {{
    --bg: #fafbfc;
    --panel: #ffffff;
    --border: #e6e8eb;
    --text: #1a1d22;
    --muted: #5f6b7a;
    --accent: #1b9e77;
    --accent-soft: #e8f4f0;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                 Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.55;
  }}
  header {{
    background: linear-gradient(135deg, #1b9e77 0%, #117a59 100%);
    color: white;
    padding: 32px 48px 28px;
  }}
  header h1 {{
    margin: 0 0 6px 0;
    font-size: 28px;
    letter-spacing: -0.5px;
  }}
  header p.lead {{
    margin: 0;
    opacity: 0.9;
    font-size: 15px;
  }}
  .nav {{
    position: sticky;
    top: 0;
    background: rgba(255,255,255,0.97);
    border-bottom: 1px solid var(--border);
    padding: 10px 48px;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    z-index: 10;
    backdrop-filter: blur(4px);
  }}
  .nav a {{
    color: var(--muted);
    text-decoration: none;
    font-size: 13px;
    padding: 4px 10px;
    border-radius: 4px;
  }}
  .nav a:hover {{
    color: var(--accent);
    background: var(--accent-soft);
  }}
  main {{
    max-width: 1100px;
    margin: 24px auto 80px;
    padding: 0 24px;
  }}
  .metrics {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }}
  .metric {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .metric .label {{
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }}
  .metric .value {{
    font-size: 22px;
    font-weight: 600;
    color: var(--text);
  }}
  .panel {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 24px 28px;
    margin-bottom: 20px;
  }}
  .panel h2 {{
    margin: 0 0 16px 0;
    font-size: 18px;
    color: var(--accent);
  }}
  .panel img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
  }}
  .caption {{
    color: var(--muted);
    font-size: 13.5px;
    margin: 12px 4px 0;
  }}
  .markdown h2 {{
    font-size: 16px;
    margin: 12px 0 4px;
    color: var(--accent);
  }}
  .markdown h3 {{
    font-size: 13.5px;
    margin: 10px 0 2px;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .markdown p {{
    margin: 4px 0;
    font-size: 14px;
  }}
  .markdown ul {{
    margin: 4px 0 6px 14px;
    padding: 0;
    font-size: 14px;
  }}
  .markdown li {{
    margin: 2px 0;
  }}
  /* Overview spans the full content width; on wider screens, lay
     the four small subsections out in two columns so the panel
     fills the white space without long lines. */
  .overview-grid {{
    column-count: 2;
    column-gap: 36px;
  }}
  .overview-grid h3 {{
    break-after: avoid;
  }}
  .overview-grid > * {{
    break-inside: avoid;
  }}
  @media (max-width: 720px) {{
    .overview-grid {{ column-count: 1; }}
  }}
  code {{
    font-family: "SF Mono", Menlo, Consolas, monospace;
    background: #f1f3f5;
    color: #1a1d22;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.92em;
  }}
  .missing {{
    color: var(--muted);
    font-style: italic;
  }}
  pre.json {{
    background: #1e2228;
    color: #d6deeb;
    padding: 14px 18px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 12px;
    line-height: 1.45;
  }}
  details summary {{
    cursor: pointer;
    color: var(--accent);
    margin-bottom: 8px;
  }}
  footer {{
    text-align: center;
    padding: 24px;
    color: var(--muted);
    font-size: 13px;
  }}
</style>
</head>
<body>
<header>
  <h1>pbg-reactive-system — MAPK signalling as a Bigraphical Reactive System</h1>
  <p class="lead">MEK phosphorylates ERK in the cytoplasm; phospho-ERK
  translocates into the nucleus; nuclear phosphatases close the
  cycle. Modelled as a Milner-style bigraph with seven rewrite rules
  under Gillespie SSA.</p>
</header>
{nav}
<main>
  {metrics}
  {overview}
  {bigraph}
  {timeseries}
  {snapshots}
  {animation}
  {rules}
  {state}
</main>
<footer>
  Generated by <code>pbg-reactive-system/demo/demo_report.py</code>.
  Built on <a href="https://github.com/vivarium-collective/process-bigraph">process-bigraph</a>,
  <a href="https://github.com/vivarium-collective/bigraph-schema">bigraph-schema</a>, and
  <a href="https://github.com/vivarium-collective/bigraph-viz">bigraph-viz</a>.
</footer>
</body>
</html>"""


def main():
    out_dir = os.path.join(HERE, '_artifacts')
    os.makedirs(out_dir, exist_ok=True)

    total_time = 120.0
    interval = 1.0
    seed = 42
    filename = 'brs_mapk'

    print(f'Running MAPK BRS for {total_time:g} ticks '
          f'(Gillespie, seed={seed})...')
    results, initial_state, elapsed = run_simulation(
        total_time=total_time, interval=interval, seed=seed)
    print(f'  -> {len(results)} emitted snapshots in {elapsed:.2f}s')

    print('Generating plots / animation / explainer...')
    plot_brs_mapk(
        results,
        state=initial_state,
        config={
            'filename': filename,
            'out_dir': out_dir,
            'n_snapshots': 6,
        })

    output_html = os.path.join(HERE, 'report.html')
    print(f'Assembling {output_html}...')
    render_report(
        filename=filename,
        out_dir=out_dir,
        results=results,
        elapsed=elapsed,
        initial_state=initial_state,
        total_time=total_time,
        n_emits=len(results),
        output_html=output_html)

    print(f'Done. Opening {output_html} in your browser.')
    webbrowser.open('file://' + os.path.abspath(output_html))


if __name__ == '__main__':
    main()
