"""Render public GitHub stats as repo-owned SVG; standard library only.

Counts primary languages per owned, public, non-fork repo (not code bytes,
commits, time spent, or proficiency). No credentials or private data persisted.
Run --offline to rebuild from the committed snapshot without network access.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USERNAME = 'sadad54'
COLORS = ['#bfa7ff', '#87e7ce', '#ffc582', '#f59fc6', '#8bbdff', '#e1df90', '#a1b9c7']


def fetch_repositories():
    repos = []
    for page in range(1, 101):
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'sadad54-profile-stats', 'X-GitHub-Api-Version': '2022-11-28'}
        token = os.environ.get('GH_TOKEN')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        req = Request(f'https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}', headers=headers)
        with urlopen(req, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError('Unexpected GitHub response; retaining previous assets')
        repos.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError('Pagination safety limit reached')
    public = [r for r in repos if not r['private'] and r['owner']['login'].lower() == USERNAME]
    if not public:
        raise ValueError('No public repositories returned; retaining previous assets')
    return sorted([{'name': r['name'], 'language': r['language'], 'fork': r['fork'], 'private': False,
                    'owner': {'login': USERNAME}} for r in public], key=lambda r: r['name'].lower())


def summarize(repos):
    public = [r for r in repos if not r['private'] and r['owner']['login'].lower() == USERNAME]
    counts = Counter(r['language'] for r in public if not r['fork'] and r['language'])
    return len(public), sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def render(snapshot):
    total, langs = summarize(snapshot['repositories'])
    date = escape(snapshot['updated'])
    height = max(390, 135 + len(langs) * 34)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">',
           '<title id="title">Sadad’s public GitHub snapshot</title>',
           f'<desc id="desc">{total} public repositories. {len(langs)} primary languages in non-fork repositories. ' + escape(', '.join(f'{name}: {count}' for name,count in langs)) + f'. Snapshot {date}.</desc>',
           f'<rect width="1200" height="{height}" rx="22" fill="#121522"/>',
           '<text x="36" y="46" fill="#bfa7ff" font-family="Arial,sans-serif" font-size="17" letter-spacing="2">THE BUILD LOG</text>',
           f'<text x="36" y="135" fill="#f4f3ff" font-family="Arial,sans-serif" font-size="74" font-weight="700">{total}</text>',
           '<text x="39" y="168" fill="#bcc3d6" font-family="Arial,sans-serif" font-size="22">public repos</text>',
           f'<text x="260" y="135" fill="#87e7ce" font-family="Arial,sans-serif" font-size="74" font-weight="700">{len(langs)}</text>',
           '<text x="263" y="168" fill="#bcc3d6" font-family="Arial,sans-serif" font-size="22">languages</text>',
           '<text x="39" y="233" fill="#a6adc6" font-family="monospace" font-size="18">AI / WEB / MOBILE / DATA</text>',
           f'<text x="39" y="{height-60}" fill="#9da7bf" font-family="Arial,sans-serif" font-size="16">Updated {date} · daily refresh</text>',
           f'<line x1="505" y1="36" x2="505" y2="{height-36}" stroke="#30374d"/>',
           '<text x="545" y="46" fill="#e5e4f4" font-family="Arial,sans-serif" font-size="21" font-weight="700">LANGUAGE MIX</text>']
    highest = max((c for _,c in langs),default=1)
    for i,(name,count) in enumerate(langs):
        y=85+i*34
        color=COLORS[i%len(COLORS)]
        svg.extend([f'<text x="545" y="{y+16}" font-family="Arial,sans-serif" font-size="18" fill="#d4d9e9">{escape(name)}</text>',
                    f'<rect x="685" y="{y}" width="405" height="21" rx="6" fill="#232a3e"/>',
                    f'<rect x="685" y="{y}" width="{405*count/highest:.2f}" height="21" rx="6" fill="{color}"/>',
                    f'<text x="1148" y="{y+17}" text-anchor="end" font-family="monospace" font-size="20" fill="#e7eafa">{count}</text>'])
    svg.append(f'<text x="545" y="{height-28}" fill="#9da7bf" font-family="Arial,sans-serif" font-size="16">Repos by primary language · excludes forks</text></svg>')
    table = f'Updated **{snapshot["updated"]}** · **{total} public repositories** · **{len(langs)} primary languages**.\n\n| Primary language | Repositories |\n| :--- | ---: |\n'
    table += ''.join(f'| {name} | {count} |\n' for name,count in langs)
    table += '\nLanguage counts exclude forks and repos with no detected language. These are repository counts, not code volume or proficiency scores.\n'
    return ''.join(svg), table


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--offline',action='store_true')
    args=parser.parse_args()
    snapshot_path=ROOT/'assets/github-stats.json'
    snapshot=json.loads(snapshot_path.read_text()) if args.offline else {'updated':datetime.now(timezone.utc).date().isoformat(),'repositories':fetch_repositories()}
    svg,table=render(snapshot)
    readme_path=ROOT/'README.md'
    readme=readme_path.read_text()
    readme,n=re.subn(r'<!-- STATS:START -->.*?<!-- STATS:END -->','<!-- STATS:START -->\n'+table+'<!-- STATS:END -->',readme,flags=re.S)
    if n!=1:
        raise ValueError('README must contain exactly one stats block')
    (ROOT/'assets/github-stats.svg').write_text(svg)
    snapshot_path.write_text(json.dumps(snapshot,indent=2)+'\n')
    readme_path.write_text(readme)
    print(f'Rendered {summarize(snapshot["repositories"])[0]} public repositories')


if __name__=='__main__':
    main()
