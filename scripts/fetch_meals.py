import json
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = 'https://gpjago.goegu.kr/gpjago/ad/fm/foodmenu/selectFoodMenuView.do?mi=2772'
OUT = Path('data/meals.json')

# The school site renders the current weekly table server-side.
# We intentionally keep parsing conservative so a small markup change does not
# silently create incorrect meals.
r = requests.get(URL, timeout=30, headers={'User-Agent': 'Mozilla/5.0 GPJA-Meal-Service'})
r.raise_for_status()
soup = BeautifulSoup(r.text, 'html.parser')

text = soup.get_text('\n', strip=True)
# Extract date-like values and menu cells. The parser is a fallback-friendly
# baseline; if the source markup changes, the workflow fails rather than
# publishing guessed data.
dates = re.findall(r'2026-\d{2}-\d{2}', text)
unique_dates = []
for d in dates:
    if d not in unique_dates:
        unique_dates.append(d)

# Find the meal table. The exact class/id can vary with the school CMS.
table = None
for candidate in soup.find_all('table'):
    if '주간식단안내' in candidate.get_text(' ', strip=True) or '식단' in candidate.get_text(' ', strip=True):
        table = candidate
        break

if table is None:
    raise RuntimeError('Meal table not found on school page')

rows = table.find_all('tr')
headers = []
for cell in rows[0].find_all(['th','td']):
    headers.append(cell.get_text(' ', strip=True))

meals = {}
# Parse cells containing YYYY-MM-DD, then use the following cell as its menu.
for row in rows:
    cells = [c.get_text(' ', strip=True) for c in row.find_all(['th','td'])]
    for i, cell in enumerate(cells):
        if re.fullmatch(r'2026-\d{2}-\d{2}', cell):
            key = cell
            menu_text = cells[i + 1] if i + 1 < len(cells) else ''
            if menu_text and menu_text != '식단 데이터가 없습니다.':
                menu = [x.strip() for x in re.split(r'\s*(?:<br>|\n|/|·)\s*', menu_text) if x.strip()]
                meals[key] = {'menu': menu}

# Preserve existing data if the page currently has no meals (e.g. vacation),
# so a temporary empty school page does not erase the site's last known data.
existing = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {'meals': {}}
if not meals:
    meals = existing.get('meals', {})

payload = {
    'school': '군포중앙고등학교',
    'source': URL,
    'updatedAt': date.today().isoformat(),
    'meals': meals,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Updated {len(meals)} meal dates')
