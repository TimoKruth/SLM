#!/usr/bin/python3
"""Read-only, atomic live overview for the existing local PowerWatch collector."""
import argparse
from contextlib import closing
import datetime as dt
import html
import hashlib
import importlib.machinery
import importlib.util
import json
import math
from pathlib import Path
import resource
import re
import shlex
import sqlite3
import time

DEFAULT_HOME = Path.home() / 'Library/Application Support/PowerWatch'


def load_powerwatch(home):
    loader = importlib.machinery.SourceFileLoader('powerwatch_reader', str(home/'powerwatch'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.APP_HOME = home
    module.DB_PATH = home/'data/powerwatch.sqlite3'
    return module


def process_name(command):
    """Display application/executable names without command-line arguments."""
    app = re.search(r'/([^/]+\.app)/', command or '')
    if app: return app.group(1)
    try: parts = shlex.split(command or '')
    except ValueError: return 'unbekannt'
    return Path(parts[0]).name if parts else 'unbekannt'


def chart(rows, key, title, color, maximum_value=100, invert=False):
    """Keep peaks and missing intervals visible; SVG needs no chart library or server."""
    if not rows:
        return ''
    start, end = rows[0]['ts'], max(rows[-1]['ts'], rows[0]['ts']+1)
    segments, current, previous = [], [], None
    for row in rows:
        value = row[key]
        if value is None or (previous is not None and row['ts']-previous > 45):
            if current: segments.append(current)
            current = []
        previous = row['ts']
        if value is None: continue
        value = 100-value if invert else value
        x = 40+(row['ts']-start)/(end-start)*860
        y = 155-min(1,max(0,value/maximum_value))*125
        current.append(f'{x:.1f},{y:.1f}')
    if current: segments.append(current)
    lines = ''.join(f'<polyline points="{" ".join(s)}" fill="none" stroke="{color}" stroke-width="1.5"/>' for s in segments)
    left = dt.datetime.fromtimestamp(start).astimezone().strftime('%d.%m. %H:%M')
    right = dt.datetime.fromtimestamp(end).astimezone().strftime('%d.%m. %H:%M')
    return f'''<section class="chart"><h3>{html.escape(title)}</h3>
<svg viewBox="0 0 920 190" role="img" aria-label="{html.escape(title)}">
<line x1="40" y1="155" x2="900" y2="155" class="grid"/><line x1="40" y1="30" x2="900" y2="30" class="grid"/>
<text x="3" y="35">{maximum_value:g}</text><text x="20" y="158">0</text>{lines}
<text x="40" y="180">{left}</text><text x="900" y="180" text-anchor="end">{right}</text>
</svg></section>'''


def live_document(document, latest, refresh=60):
    sample_ms = int(latest['ts']*1000)
    stamp = dt.datetime.fromtimestamp(latest['ts']).astimezone().strftime('%d.%m.%Y %H:%M:%S')
    cpu = 'n/a' if latest.get('cpu_idle') is None else f"{100-latest['cpu_idle']:.1f} %"
    gpu = 'n/a' if latest.get('gpu_device') is None else f"{latest['gpu_device']:.0f} %"
    panel = f'''<section class="table"><h2>Live-Systemübersicht</h2>
<p id="freshness">Letzte Messung: {stamp}</p>
<p><strong>Aktuell: CPU {cpu} · GPU {gpu}</strong></p>
<p>Sammler: alle 15 Sekunden · Ansicht: alle {refresh} Sekunden · Verlauf: 30 Tage lokal.
CPU stammt aus dem jeweiligen top-Messfenster; GPU ist eine systemweite Treiberanzeige.
„RAM frei“ meint physisch unbenutzten Speicher, nicht den gesamten noch verfügbaren Speicher inklusive freigebbarer Caches.
Lücken über 45 Sekunden werden in den Kurven unterbrochen.</p></section>
<script>
function freshness() {{
 const seconds=Math.max(0,Math.floor((Date.now()-{sample_ms})/1000));
 const node=document.getElementById('freshness');
 node.textContent='Letzte Messung: {stamp} · vor '+seconds+' s'+(seconds>90?' · ANSICHT ODER SAMMLER VERALTET':'');
 node.style.color=seconds>90?'#ff7a59':'#8b949e';
}}
freshness();setInterval(freshness,1000);
</script>'''
    document = document.replace('<meta charset="utf-8">', f'<meta charset="utf-8"><meta http-equiv="refresh" content="{refresh}">')
    document = document.replace('<div class="cards">',panel+'<div class="cards">',1)
    return document


def render(home, output, hours=6):
    started = time.perf_counter()
    powerwatch = load_powerwatch(home)
    powerwatch.svg_chart = chart
    powerwatch.basename_command = process_name
    output.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(powerwatch.DB_PATH.as_uri()+'?mode=ro', uri=True, timeout=1)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        # Bound expensive report queries without obstructing the WAL writer.
        db.set_progress_handler(lambda: int(time.perf_counter()-started>15), 10000)
        payload = powerwatch.report_payload(db, hours)
    if not payload: raise ValueError('No samples in requested period')
    latest = dict(payload['rows'][-1])
    temp = output/'latest.tmp.html'
    try:
        powerwatch.write_html_report(payload, temp)
        document = live_document(temp.read_text(), latest)
        memory_rows = [dict(r, used_gib=r['mem_used']/1024**3 if r['mem_used'] is not None else None, compressed_gib=r['mem_compressed']/1024**3 if r['mem_compressed'] is not None else None) for r in payload['rows']]
        memory_charts = chart(memory_rows, 'used_gib', 'RAM belegt inkl. Caches (GiB)', '#2d8cff', payload['hardware']['memory']/1024**3 or 64)
        memory_charts += chart(memory_rows, 'compressed_gib', 'RAM komprimiert (GiB)', '#f59e0b', payload['hardware']['memory']/1024**3 or 64)
        io_panel = '<section class="table"><h2>Weitere Ressourcen</h2><p>Netzwerk im Zeitraum: empfangen '+powerwatch.format_bytes(payload.get('net_in'))+' · gesendet '+powerwatch.format_bytes(payload.get('net_out'))+'</p><p>Letzte Swap-Zähler des Sammlers: In '+str(latest.get('swapins', 'n/a'))+' · Out '+str(latest.get('swapouts', 'n/a'))+' (Zählerwerte, keine Byteangabe).</p></section>'
        document = document.replace('<section class="table"><h2>Größte beobachtete Verursacher</h2>', memory_charts+io_panel+'<section class="table"><h2>Größte beobachtete Verursacher</h2>')
        temp.write_text(document)
        temp.chmod(0o600)
        temp.replace(output/'latest.html')
    finally:
        temp.unlink(missing_ok=True)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    summary = dict(status='ok', generated_at=dt.datetime.now().astimezone().isoformat(),
        latest_sample_at=latest['iso'], latest_sample_age_seconds=time.time()-latest['ts'],
        hours=hours, sample_count=len(payload['rows']), collection_interval_seconds=15,
        cpu_avg_percent=payload['cpu_avg'], gpu_avg_percent=payload['gpu_avg'],
        report_wall_seconds=time.perf_counter()-started,
        report_cpu_seconds=usage.ru_utime+usage.ru_stime+children.ru_utime+children.ru_stime,
        report_peak_rss_bytes=usage.ru_maxrss,
        database=str(powerwatch.DB_PATH), database_modified_by_reporter=False,
        sampler_sha256=hashlib.sha256((home/'powerwatch').read_bytes()).hexdigest() if (home/'powerwatch').exists() else None)
    tmp = output/'status.tmp.json';tmp.write_text(json.dumps(summary,indent=2)+'\n');tmp.replace(output/'status.json')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home',type=Path,default=DEFAULT_HOME)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--hours',type=float,default=6)
    a=p.parse_args()
    if not math.isfinite(a.hours) or not 0<a.hours<=24:p.error('Hours must be > 0 and <= 24')
    try:
        result=render(a.home.expanduser().resolve(),a.output.expanduser().resolve(),a.hours)
    except Exception as exc:
        a.output.mkdir(parents=True,exist_ok=True)
        error=dict(status='error',generated_at=dt.datetime.now().astimezone().isoformat(),error=str(exc))
        tmp=a.output/'status.tmp.json';tmp.write_text(json.dumps(error,indent=2)+'\n');tmp.replace(a.output/'status.json')
        raise
    print(json.dumps(result))

if __name__=='__main__':main()
