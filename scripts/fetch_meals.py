import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = 'https://gpjago.goegu.kr/gpjago/ad/fm/foodmenu/selectFoodMenuView.do?mi=2772'
OUT = Path('data/meals.json')
HEADERS = {'User-Agent': 'Mozilla/5.0 GPJA-Meal-Service'}
WEEKDAYS = {'월', '화', '수', '목', '금'}
DATE_RE = re.compile(r'(\d{1,2})/(\d{1,2})\(([월화수목금토일])\)')


def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text('\n', strip=True)
    matches = list(DATE_RE.finditer(text))
    meals = {}

    for i, match in enumerate(matches):
        if match.group(3) not in WEEKDAYS:
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].split('주간 학급별 시간표', 1)[0]
        block = re.sub(r'\s+', ' ', block).strip()
        if not block or '식단 데이터가 없습니다' in block:
            continue

        kcal_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*Kcal', block, re.I)
        kcal = float(kcal_match.group(1)) if kcal_match else None
        if kcal_match:
            block = block[kcal_match.end():].strip()
        block = re.sub(r'^점심\s*', '', block)

        # The school page normally exposes each menu item on a separate line.
        # When the CMS collapses them, use repeated known menu boundaries as a
        # fallback while avoiding aggressive guessing.
        parts = [p.strip() for p in re.split(r'\s{2,}|(?=\([^)]*\)\s*[가-힣])', block) if p.strip()]
        if len(parts) < 2:
            parts = [p.strip() for p in re.split(r'\s*·\s*', block) if p.strip()]
        if not parts:
            continue

        year = date.today().year
        month, day = int(match.group(1)), int(match.group(2))
        if date.today().month == 12 and month == 1:
            year += 1
        key = date(year, month, day).isoformat()
        meals[key] = {'menu': parts}
        if kcal is not None:
            meals[key]['kcal'] = kcal

    return meals, soup


def find_next_url(soup, current_url):
    for tag in soup.find_all(['a', 'button', 'input']):
        label = tag.get_text(' ', strip=True) if tag.name != 'input' else tag.get('value', '')
        if '다음' not in label:
            continue
        href = tag.get('href')
        if href and not href.lower().startswith('javascript:'):
            return urljoin(current_url, href)
        onclick = tag.get('onclick', '')
        match = re.search(r"(?:location(?:\.href)?|document\.location)\s*=\s*['\"]([^'\"]+)", onclick)
        if match:
            return urljoin(current_url, match.group(1))
    return None


def fetch_weeks():
    session = requests.Session()
    session.headers.update(HEADERS)
    url = URL
    meals = {}
    seen = set()
    for _ in range(5):
        if not url or url in seen:
            break
        seen.add(url)
        response = session.get(url, timeout=30)
        response.raise_for_status()
        page_meals, soup = parse_page(response.text)
        meals.update(page_meals)
        url = find_next_url(soup, response.url)
    return meals


existing = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {'meals': {}}
try:
    fetched = fetch_weeks()
except Exception as exc:
    print(f'Warning: meal crawl failed: {exc}')
    fetched = {}

meals = dict(existing.get('meals', {}))
meals.update(fetched)
today = date.today()
end = today + timedelta(days=30)
meals = {
    key: value for key, value in meals.items()
    if today <= date.fromisoformat(key) <= end and date.fromisoformat(key).weekday() < 5
}

payload = {
    'school': '군포중앙고등학교',
    'source': URL,
    'updatedAt': today.isoformat(),
    'range': {'from': today.isoformat(), 'to': end.isoformat(), 'weekdaysOnly': True},
    'meals': meals,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Updated {len(meals)} weekday meal dates')
