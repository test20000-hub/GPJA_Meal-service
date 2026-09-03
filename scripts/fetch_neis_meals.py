import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

API_KEY = os.environ["NEIS_API_KEY"]
BASE = "https://open.neis.go.kr/hub"
SCHOOL_PAGE = "https://gpjago.goegu.kr/gpjago/ad/fm/foodmenu/selectFoodMenuView.do?mi=2772"
SCHOOL_NAME = "군포중앙고등학교"
OFFICE_CODE = "J10"
SCHOOL_CODE = "7531272"
MEAL_CODE = "2"
OUT = Path("data/meals.json")
HEADERS = {"User-Agent": "Mozilla/5.0 GPJA-Meal-Service"}


def get_json(endpoint, params):
    response = requests.get(f"{BASE}/{endpoint}", params={"KEY": API_KEY, "Type": "json", **params}, timeout=30)
    response.raise_for_status()
    data = response.json()
    if "RESULT" in data:
        result = data["RESULT"]
        raise RuntimeError(f"NEIS {result.get('CODE')}: {result.get('MESSAGE')}")
    return data


def fetch_neis(start, end):
    data = get_json("mealServiceDietInfo", {
        "pIndex": 1, "pSize": 1000,
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_FROM_YMD": start.strftime("%Y%m%d"),
        "MLSV_TO_YMD": end.strftime("%Y%m%d"),
    })
    rows = data.get("mealServiceDietInfo", [])
    meals = {}
    if len(rows) < 2:
        return meals
    for row in rows[1].get("row", []):
        if row.get("MMEAL_SC_CODE") != MEAL_CODE:
            continue
        key = row["MLSV_YMD"]
        menu = [x.strip() for x in re.split(r"<br\s*/?>", row.get("DDISH_NM", "")) if x.strip()]
        value = {"menu": menu, "source": "NEIS"}
        if row.get("CAL_INFO"):
            try:
                value["kcal"] = float(row["CAL_INFO"].replace(" Kcal", "").strip())
            except ValueError:
                pass
        meals[f"{key[:4]}-{key[4:6]}-{key[6:8]}"] = value
    return meals


def fetch_school_week():
    response = requests.get(SCHOOL_PAGE, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        date_cells = []
        lunch_cells = []
        for row in rows:
            cells = row.find_all(["th", "td"])
            row_text = " ".join(cell.get_text(" ", strip=True) for cell in cells)
            dates = []
            for cell in cells:
                match = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", cell.get_text(" ", strip=True))
                if match:
                    dates.append(datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date())
            if len(dates) >= 5:
                date_cells = dates
            if "중식" in row_text and len(cells) >= 6:
                lunch_cells = cells[1:]
        if date_cells and lunch_cells:
            meals = {}
            for day, cell in zip(date_cells, lunch_cells):
                if day.weekday() >= 5:
                    continue
                text = cell.get_text("\n", strip=True)
                kcal_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*Kcal", text, re.I)
                kcal = float(kcal_match.group(1)) if kcal_match else None
                if kcal_match:
                    text = text[kcal_match.end():]
                lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines() if x.strip()]
                lines = [x for x in lines if x not in {"상세보기"}]
                if lines:
                    value = {"menu": lines, "source": "SCHOOL"}
                    if kcal is not None:
                        value["kcal"] = kcal
                    meals[day.isoformat()] = value
            return meals
    return {}


def main():
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    end = today + timedelta(days=30)

    # NEIS is authoritative for today and future dates.
    meals = fetch_neis(today, end)

    # The school site supplies earlier weekdays from the current week, which
    # NEIS may no longer return. Never let school-page data overwrite NEIS.
    try:
        school_meals = fetch_school_week()
        for key, value in school_meals.items():
            if today > datetime.fromisoformat(key).date() and datetime.fromisoformat(key).date().weekday() < 5:
                meals.setdefault(key, value)
        print(f"School page: added {sum(1 for k in school_meals if k in meals and k < today.isoformat())} prior weekday meals")
    except Exception as exc:
        print(f"Warning: school-page fallback failed: {exc}")

    meals = {k: v for k, v in meals.items() if today <= datetime.fromisoformat(k).date() <= end or (datetime.fromisoformat(k).date() < today and datetime.fromisoformat(k).date() >= today - timedelta(days=7))}
    meals = {k: v for k, v in meals.items() if datetime.fromisoformat(k).weekday() < 5}
    if not meals:
        raise RuntimeError("NEIS와 학교 급식표에서 급식 데이터가 0건 반환되었습니다.")

    payload = {
        "school": SCHOOL_NAME,
        "educationOffice": "경기도교육청",
        "source": SCHOOL_PAGE,
        "provider": "NEIS + 학교 공식 급식표",
        "updatedAt": today.isoformat(),
        "range": {"from": min(meals), "to": end.isoformat(), "weekdaysOnly": True},
        "meals": meals,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(meals)} weekday lunch dates ({min(meals)} ~ {end})")


if __name__ == "__main__":
    main()
