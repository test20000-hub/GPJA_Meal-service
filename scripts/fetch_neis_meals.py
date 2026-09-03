import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_KEY = os.environ["NEIS_API_KEY"]
BASE = "https://open.neis.go.kr/hub"
SCHOOL_NAME = "군포중앙고등학교"
OFFICE_CODE = "J10"
SCHOOL_CODE = "7531272"
MEAL_CODE = "2"
OUT = Path("data/meals.json")


def get_json(endpoint, params):
    response = requests.get(f"{BASE}/{endpoint}", params={"KEY": API_KEY, "Type": "json", **params}, timeout=30)
    response.raise_for_status()
    data = response.json()
    if "RESULT" in data:
        result = data["RESULT"]
        raise RuntimeError(f"NEIS {result.get('CODE')}: {result.get('MESSAGE')}")
    return data


def fetch_meals(start, end):
    data = get_json("mealServiceDietInfo", {
        "pIndex": 1,
        "pSize": 1000,
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_FROM_YMD": start.strftime("%Y%m%d"),
        "MLSV_TO_YMD": end.strftime("%Y%m%d"),
    })
    rows = data.get("mealServiceDietInfo", [])
    if len(rows) < 2:
        return {}

    meals = {}
    for row in rows[1].get("row", []):
        if row.get("MMEAL_SC_CODE") != MEAL_CODE:
            continue
        key = row["MLSV_YMD"]
        menu_text = row.get("DDISH_NM", "")
        menu = [x.strip() for x in menu_text.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n").split("\n") if x.strip()]
        value = {"menu": menu}
        if row.get("CAL_INFO"):
            try:
                value["kcal"] = float(row["CAL_INFO"].replace(" Kcal", "").strip())
            except ValueError:
                pass
        meals[f"{key[:4]}-{key[4:6]}-{key[6:8]}"] = value
    return meals


def main():
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    end = today + timedelta(days=30)
    meals = fetch_meals(today, end)
    meals = {k: v for k, v in meals.items() if datetime.fromisoformat(k).weekday() < 5}
    if not meals:
        raise RuntimeError("NEIS에서 급식 데이터가 0건 반환되었습니다.")

    payload = {
        "school": SCHOOL_NAME,
        "educationOffice": "경기도교육청",
        "source": "https://open.neis.go.kr/portal/mainPage.do",
        "provider": "NEIS",
        "updatedAt": today.isoformat(),
        "range": {"from": today.isoformat(), "to": end.isoformat(), "weekdaysOnly": True},
        "meals": meals,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"NEIS: generated {len(meals)} weekday lunch dates ({today} ~ {end})")


if __name__ == "__main__":
    main()
