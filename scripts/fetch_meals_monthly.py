import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = 'https://gpjago.goegu.kr/gpjago/ad/fm/foodmenu/selectFoodMenuView.do?mi=2772'
OUT = Path('data/meals.json')
DATE_RE = re.compile(r'20\d{2}-\d{2}-\d{2}')
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 GPJA-Meal-Service/1.0'})


def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = next((t for t in soup.find_all('table') if '주간식단안내' in t.get_text(' ', strip=True)), None)
    if table is None:
        return {}
    rows = table.find_all('tr')
    date_row = None
    dates = []
    for i, row in enumerate(rows):
        cells = row.find_all(['th', 'td'])
        found = [(j, c.get_text(' ', strip=True)) for j, c in enumerate(cells) if DATE_RE.fullmatch(c.get_text(' ', strip=True))]
        if len(found) >= 2:
            date_row, dates = i, found
            break
    if date_row is None:
        return {}

    result = {}
    for row in rows[date_row + 1:]:
        cells = row.find_all(['th', 'td'])
        if '식단 데이터가 없습니다' in row.get_text(' ', strip=True):
            continue
        row_result = {}
        for col, key in dates:
            if col >= len(cells):
                continue
            text = cells[col].get_text('\n', strip=True)
            lines = []
            for line in text.split('\n'):
                line = re.sub(r'상세보기', '', line).strip()
                if not line or re.fullmatch(r'\d+(?:\.\d+)?\s*kcal', line, re.I):
                    continue
                lines.append(line)
            if lines:
                item = {'menu': lines}
                kcal = re.search(r'(\d+(?:\.\d+)?)\s*kcal', text, re.I)
                if kcal:
                    item['kcal'] = float(kcal.group(1))
                row_result[key] = item
        if row_result:
            result.update(row_result)
            break
    return result


def find_next(html, current):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all(['a', 'button', 'input']):
        text = ' '.join([tag.get_text(' ', strip=True), tag.get('value', ''), tag.get('title', ''), tag.get('aria-label', ''), tag.get('onclick', '')])
        if '다음' not in text:
            continue
        href = tag.get('href') or tag.get('data-url') or tag.get('data-href')
        if href and not href.startswith('javascript') and href != '#':
            return urljoin(current, href)
        m = re.search(r"(?:location\.href|window\.location)\s*=\s*['\"]([^'\"]+)", tag.get('onclick', ''))
        if m:
            return urljoin(current, m.group(1))
    return None

existing = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {'meals': {}}
meals = dict(existing.get('meals', {}))
url = URL
seen = set()
for _ in range(6):
    if url in seen:
        break
    seen.add(url)
    response = session.get(url, timeout=30)
    response.raise_for_status()
    meals.update(parse_page(response.text))
    nxt = find_next(response.text, url)
    if not nxt:
        break
    url = nxt

if not meals:
    raise RuntimeError('No meal data found')

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({'school': '군포중앙고등학교', 'source': URL, 'updatedAt': date.today().isoformat(), 'meals': meals}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Updated {len(meals)} meal dates')
