#!/usr/bin/env python3
"""Regenerate references/endpoints.md from the partner backend sources, and optionally probe them.

    python3 .claude/skills/front-end-development/scripts/inventory_endpoints.py
    python3 .claude/skills/front-end-development/scripts/inventory_endpoints.py --probe http://localhost:5000
    python3 .claude/skills/front-end-development/scripts/inventory_endpoints.py --probe-nodeports 192.168.49.2

The backend code is the source of truth: routes, methods, query parameters, JSON body keys and
top-level response keys are read statically (Python ast) from each Flask app.py. Nothing is executed.
--probe sends a GET to every parameter-free GET endpoint through the app's /api/<tool> proxy;
--probe-nodeports does the same straight against the cluster NodePorts.
"""
import argparse
import ast
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]                       # IAM-IQ/
OUT = HERE.parent / 'references' / 'endpoints.md'

# Partner backends, copied into this repo without their UIs (backends/README.md).
REFMAP = REPO / 'backends' / 'refmap'
IMAFUSA = REPO / 'backends' / 'imafusa'

# tool ids (as in docs/frontend-spec.md §5/§6) → backend source, NodePort, container port, partner UI to read
BACKENDS = [
    (['refmap-climate'], REFMAP / 'backend/climate_impact/app.py', 30001, 4001, 'src/components/ClimateImpact.vue'),
    (['refmap-wind'], REFMAP / 'backend/wind_assessment/app.py', 30002, 4002, 'src/components/WindAssessment.vue'),
    (['refmap-noise'], REFMAP / 'backend/noise_assessment/app.py', 30003, 4003, 'src/components/NoiseAssessment.vue'),
    (['refmap-trajectories'], REFMAP / 'backend/optimized_trajectories/app.py', 30004, 4004, 'src/components/OptimizedTrajectories.vue'),
    (['refmap-emissions'], REFMAP / 'backend/emissions/app.py', 30005, 4005, 'src/components/Emissions.vue'),
    (['refmap-pollution'], REFMAP / 'backend/atmospheric_pollution/app.py', 30006, 4006, 'src/components/AtmosphericPollution.vue'),
    (['imafusa-air-quality'], IMAFUSA / 'backend/Air_Quality_Metrics/app.py', 30011, 3001, 'src/pages/tools/air-quality-metrics.vue'),
    (['imafusa-noise'], IMAFUSA / 'backend/IAM_Noise_Assesment/app.py', 30012, 3002, 'src/pages/tools/noise-assessment.vue'),
    (['imafusa-safety'], IMAFUSA / 'backend/IAM_Safety/app.py', 30013, 3003, 'src/pages/tools/safety-assessment.vue'),
    (['imafusa-visual'], IMAFUSA / 'backend/IAM_Visual_Pollution/app.py', 30014, 3004, 'src/pages/tools/visual-pollution.vue'),
    (['imafusa-social'], IMAFUSA / 'backend/IAM_Social_Acceptance/app.py', 30015, 3005, 'src/pages/tools/social-acceptance.vue'),
    (['imafusa-affordability'], IMAFUSA / 'backend/Price_Affordability/app.py', 30016, 3006, 'src/pages/tools/price-affordability.vue'),
    (['imafusa-travel-time', 'imafusa-pjr'], IMAFUSA / 'backend/Accessibility/app.py', 30017, 3007,
     'src/pages/tools/accessibility_travel_time.vue, src/pages/tools/accessibility_pjr.vue'),
]


def const(node):
    return node.value if isinstance(node, ast.Constant) else None


def route_decorators(fn):
    """Yield (path, methods) for every @x.route/@x.get/@x.post decorator."""
    for dec in fn.decorator_list:
        if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
            continue
        kind = dec.func.attr
        if kind not in ('route', 'get', 'post') or not dec.args or const(dec.args[0]) is None:
            continue
        methods = ['GET'] if kind != 'post' else ['POST']
        for kw in dec.keywords:
            if kw.arg == 'methods' and isinstance(kw.value, (ast.List, ast.Tuple)):
                methods = [const(e) for e in kw.value.elts if const(e)]
        yield const(dec.args[0]), methods


def is_request_attr(node, *attrs):
    return (isinstance(node, ast.Attribute) and node.attr in attrs
            and isinstance(node.value, ast.Name) and node.value.id == 'request')


def analyse(fn):
    """Query params, JSON body keys and top-level response keys used by one handler."""
    query, body, resp, files = {}, set(), set(), False
    json_vars = set()
    for node in ast.walk(fn):
        # data = request.get_json() / request.json
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = node.value
            if (isinstance(v, ast.Call) and is_request_attr(v.func, 'get_json')) or is_request_attr(v, 'json') or (
                    isinstance(v, ast.BoolOp) and any(isinstance(x, ast.Call) and is_request_attr(x.func, 'get_json') for x in v.values)):
                json_vars.add(node.targets[0].id)
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner, meth = node.func.value, node.func.attr
            # request.args.get('x', default) / getlist('x')
            if is_request_attr(owner, 'args') and meth in ('get', 'getlist') and node.args:
                name = const(node.args[0])
                if name is None:
                    query.setdefault('(dynamic name)', 'see source')
                    continue
                default = const(node.args[1]) if len(node.args) > 1 else None
                for kw in node.keywords:
                    if kw.arg == 'default':
                        default = const(kw.value)
                note = 'list (repeat ?x=…&x=…)' if meth == 'getlist' else (f'default {default!r}' if default is not None else '')
                query[name] = note
            # data.get('x')  where data came from request.get_json()
            if isinstance(owner, ast.Name) and owner.id in json_vars and meth == 'get' and node.args and const(node.args[0]):
                body.add(const(node.args[0]))
            # jsonify({...})
            if isinstance(node.func, ast.Attribute) is False:
                pass
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == 'jsonify' and node.args and isinstance(node.args[0], ast.Dict):
                resp.update(k.value for k in node.args[0].keys if isinstance(k, ast.Constant))
            if node.func.id in ('send_file', 'send_from_directory'):
                files = True
        # data['x']
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in json_vars and const(node.slice):
            body.add(const(node.slice))
    return query, sorted(body), sorted(resp), files


def inventory():
    tools = []
    for ids, src, nodeport, port, ui in BACKENDS:
        entry = {'ids': ids, 'src': src, 'nodeport': nodeport, 'port': port, 'ui': ui, 'routes': [], 'missing': not src.exists()}
        if src.exists():
            tree = ast.parse(src.read_text(), filename=str(src))
            for fn in ast.walk(tree):
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for path, methods in route_decorators(fn):
                        q, b, r, f = analyse(fn)
                        entry['routes'].append({'path': path, 'methods': methods, 'fn': fn.name, 'line': fn.lineno,
                                                'query': q, 'body': b, 'resp': r, 'file': f})
            entry['routes'].sort(key=lambda r: r['line'])
        tools.append(entry)
    return tools


def rel(p):
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def render(tools):
    L = ['# Backend endpoints (generated)', '',
         '<!-- GENERATED by scripts/inventory_endpoints.py from the partner backend sources. Do not edit; rerun the script. -->', '',
         'Read statically from each backend\'s `app.py`. **Browser URL** = `/api/<tool-id>` + route, through the app proxy '
         '(`app/proxy-routes.json`). Response keys are only listed where the handler returns a literal `jsonify({...})`; '
         'otherwise open the source line or probe the endpoint. For the order of calls and how results are drawn, read the '
         'partner UI file listed for each tool: that is the behaviour to reproduce.', '',
         '| Tool id(s) | NodePort → container | Backend source | Partner UI (original partner repo, not copied) |', '|---|---|---|---|']
    for t in tools:
        L.append(f"| {', '.join(f'`{i}`' for i in t['ids'])} | {t['nodeport']} → {t['port']} | `{rel(t['src'])}`"
                 f"{' ⚠️ missing' if t['missing'] else ''} | `{t['ui']}` |")
    for t in tools:
        L += ['', f"## {' / '.join(t['ids'])}", '',
              f"Proxy prefix `/api/{t['ids'][0]}`" + (f" (also `/api/{t['ids'][1]}`, same backend)" if len(t['ids']) > 1 else '')
              + f" → `$K8S_HOST:{t['nodeport']}` · source `{rel(t['src'])}`", '']
        if not t['routes']:
            L.append('_No routes found._')
            continue
        L += ['| Method | Route | Query params | JSON body | Response | Handler |', '|---|---|---|---|---|---|']
        for r in t['routes']:
            q = '<br>'.join(f'`{k}`' + (f' ({v})' if v else '') for k, v in r['query'].items()) or '–'
            b = ', '.join(f'`{k}`' for k in r['body']) or '–'
            resp = 'file / image' if r['file'] else (', '.join(f'`{k}`' for k in r['resp']) or 'see source')
            L.append(f"| {'/'.join(r['methods'])} | `{r['path']}` | {q} | {b} | {resp} | `{r['fn']}` line {r['line']} |")
    return '\n'.join(L) + '\n'


def probe(tools, base, via_proxy):
    ok = bad = 0
    for t in tools:
        for r in t['routes']:
            if 'GET' not in r['methods'] or r['query'] or '<' in r['path']:
                continue
            url = (f"{base.rstrip('/')}/api/{t['ids'][0]}{r['path']}" if via_proxy
                   else f"http://{base}:{t['nodeport']}{r['path']}")
            try:
                with urllib.request.urlopen(url, timeout=15) as res:
                    code, head = res.status, res.read(160)
            except urllib.error.HTTPError as e:
                code, head = e.code, e.read(160)
            except Exception as e:                                  # connection refused, timeout …
                code, head = 'ERR', str(e).encode()
            good = isinstance(code, int) and 200 <= code < 300
            ok, bad = ok + good, bad + (not good)
            print(f"{'ok ' if good else 'BAD'} {code} {url}  {head[:100].decode(errors='replace')!r}")
    print(f'\n{ok} ok, {bad} not ok (only parameter-free GET routes are probed)')
    return bad == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--probe', metavar='APP_URL', help='probe through the app proxy, e.g. http://localhost:5000')
    ap.add_argument('--probe-nodeports', metavar='HOST', help='probe the NodePorts directly, e.g. 192.168.49.2')
    ap.add_argument('--json', action='store_true', help='print the inventory as JSON instead of writing endpoints.md')
    a = ap.parse_args()
    tools = inventory()
    if a.json:
        print(json.dumps(tools, default=str, indent=2))
        return 0
    if a.probe or a.probe_nodeports:
        return 0 if probe(tools, a.probe or a.probe_nodeports, via_proxy=bool(a.probe)) else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(tools))
    n = sum(len(t['routes']) for t in tools)
    print(f'wrote {OUT} ({n} routes in {len(tools)} backends; missing sources: '
          f"{[rel(t['src']) for t in tools if t['missing']] or 'none'})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
