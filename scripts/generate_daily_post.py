from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"
JST = dt.timezone(dt.timedelta(hours=9))

NAHA = {"name": "那覇", "lat": 26.2124, "lon": 127.6792}
JMA_NAHA_TIDE_URL = "https://www.data.jma.go.jp/kaiyou/db/tide/suisan/suisan.php?stn=NH"


def fetch_json(base_url: str, params: dict[str, str | int | float]) -> dict:
    url = f"{base_url}?{urlencode(params)}"
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fmt_date(date_value: dt.date) -> str:
    return f"{date_value.year}/{date_value.month}/{date_value.day}"


def nearest_hour_index(times: list[str], target: dt.datetime) -> int:
    parsed = [dt.datetime.fromisoformat(value).replace(tzinfo=JST) for value in times]
    return min(range(len(parsed)), key=lambda index: abs(parsed[index] - target))


def get_weather() -> dict[str, str | float]:
    now = dt.datetime.now(JST)
    target = now.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=3)

    weather = fetch_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": NAHA["lat"],
            "longitude": NAHA["lon"],
            "hourly": "temperature_2m,wind_speed_10m,precipitation",
            "forecast_days": 1,
            "timezone": "Asia/Tokyo",
            "wind_speed_unit": "ms",
        },
    )
    marine = fetch_json(
        "https://marine-api.open-meteo.com/v1/marine",
        {
            "latitude": NAHA["lat"],
            "longitude": NAHA["lon"],
            "hourly": "wave_height",
            "forecast_days": 1,
            "timezone": "Asia/Tokyo",
            "cell_selection": "sea",
        },
    )

    weather_idx = nearest_hour_index(weather["hourly"]["time"], target)
    marine_idx = nearest_hour_index(marine["hourly"]["time"], target)

    wind = float(weather["hourly"]["wind_speed_10m"][weather_idx])
    rain = float(weather["hourly"]["precipitation"][weather_idx])
    temp = float(weather["hourly"]["temperature_2m"][weather_idx])
    wave = float(marine["hourly"]["wave_height"][marine_idx])

    return {
        "weather": weather_label(rain, wind),
        "wind_label": wind_label(wind),
        "wave_label": wave_label(wave),
        "wind": wind,
        "rain": rain,
        "temp": temp,
        "wave": wave,
    }


def weather_label(rain: float, wind: float) -> str:
    if rain >= 5 or wind >= 15:
        return "暴風雨"
    if rain >= 1:
        return "雨"
    return "くもり/晴れ"


def wind_label(wind: float) -> str:
    if wind >= 15:
        return "非常に強い風"
    if wind >= 9:
        return "強い風"
    if wind >= 5:
        return "やや強い風"
    return "弱い風"


def wave_label(wave: float) -> str:
    if wave >= 4:
        return f"{wave:.1f}m、大しけ"
    if wave >= 2.5:
        return f"{wave:.1f}m、しけ"
    if wave >= 1.5:
        return f"{wave:.1f}m、高め"
    return f"{wave:.1f}m"


def rating(weather: dict[str, str | float]) -> int:
    score = 5
    score -= int(float(weather["wind"]) // 4)
    score -= int(float(weather["wave"]) // 1.2)
    score -= int(float(weather["rain"]) // 2)
    return max(1, min(5, score))


def warning_text(weather: dict[str, str | float]) -> str:
    wave = float(weather["wave"])
    wind = float(weather["wind"])
    if wave >= 1.5 or wind >= 9:
        return "今日は海況悪化のため釣行は見合わせ推奨。外海、堤防、磯、テトラ帯は非常に危険。"
    return "安全第一で、風裏と足場の良い場所を選んで短時間釣行がおすすめ。"


def fishing_times(weather: dict[str, str | float]) -> tuple[str, str]:
    if float(weather["wave"]) >= 1.5 or float(weather["wind"]) >= 9:
        return "海況回復後", "安全確認後"
    return "5:30〜7:30", "17:00〜19:00"


def get_tide() -> dict[str, str]:
    today = dt.datetime.now(JST).date()
    try:
        jma_tide = get_jma_naha_tide(today)
        if jma_tide:
            return jma_tide
    except Exception as error:
        print(f"JMA tide fetch failed, fallback to marine estimate: {error}")

    data = fetch_json(
        "https://marine-api.open-meteo.com/v1/marine",
        {
            "latitude": NAHA["lat"],
            "longitude": NAHA["lon"],
            "hourly": "sea_level_height_msl",
            "forecast_days": 1,
            "timezone": "Asia/Tokyo",
            "cell_selection": "sea",
        },
    )
    times = data.get("hourly", {}).get("time", [])
    levels = data.get("hourly", {}).get("sea_level_height_msl", [])
    highs: list[str] = []
    lows: list[str] = []
    high_indexes: list[int] = []
    low_indexes: list[int] = []

    for index in range(1, len(levels) - 1):
        prev_level = levels[index - 1]
        level = levels[index]
        next_level = levels[index + 1]
        if prev_level is None or level is None or next_level is None:
            continue
        time_text = format_hour(times[index])
        if prev_level < level >= next_level and far_enough(index, high_indexes):
            highs.append(time_text)
            high_indexes.append(index)
        elif prev_level > level <= next_level and far_enough(index, low_indexes):
            lows.append(time_text)
            low_indexes.append(index)

    return {
        "tide": tide_cycle_name(today),
        "high_tide": " / ".join(highs[:2]) or "取得なし",
        "low_tide": " / ".join(lows[:2]) or "取得なし",
    }


def get_jma_naha_tide(target_date: dt.date) -> dict[str, str] | None:
    with urlopen(JMA_NAHA_TIDE_URL, timeout=30) as response:
        text = response.read().decode("utf-8")

    pattern = rf"<tr[^>]*>\s*<td[^>]*>\s*{target_date:%Y/%m/%d}\(.+?\)\s*</td>(.*?)</tr>"
    match = re.search(pattern, text, re.S)
    if not match:
        return None

    cells = re.findall(r"<td[^>]*>\s*([^<]+?)\s*</td>", match.group(1))
    tide_pairs = [cells[index:index + 2] for index in range(1, len(cells), 2)]
    highs = [pair[0].strip() for pair in tide_pairs[:4] if len(pair) == 2 and pair[0].strip() != "*"]
    lows = [pair[0].strip() for pair in tide_pairs[4:8] if len(pair) == 2 and pair[0].strip() != "*"]
    if not highs and not lows:
        return None

    return {
        "tide": tide_cycle_name(target_date),
        "high_tide": " / ".join(highs) or "取得なし",
        "low_tide": " / ".join(lows) or "取得なし",
    }


def tide_cycle_name(date_value: dt.date) -> str:
    age = moon_age(date_value)
    if age < 1.5 or age >= 28.5:
        return "大潮"
    if age < 6.5:
        return "中潮"
    if age < 9.5:
        return "小潮"
    if age < 10.5:
        return "長潮"
    if age < 11.5:
        return "若潮"
    if age < 13.5:
        return "中潮"
    if age < 17.5:
        return "大潮"
    if age < 21.5:
        return "中潮"
    if age < 24.5:
        return "小潮"
    if age < 25.5:
        return "長潮"
    if age < 26.5:
        return "若潮"
    return "中潮"


def moon_age(date_value: dt.date) -> float:
    known_new_moon = dt.datetime(2000, 1, 6, 18, 14, tzinfo=dt.timezone.utc)
    target_noon_jst = dt.datetime.combine(date_value, dt.time(12, 0), tzinfo=JST)
    days = (target_noon_jst.astimezone(dt.timezone.utc) - known_new_moon).total_seconds() / 86400
    return days % 29.530588853


def format_hour(value: str) -> str:
    parsed = dt.datetime.fromisoformat(value)
    return f"{parsed.hour}:{parsed.minute:02d}"


def far_enough(index: int, indexes: list[int], min_gap: int = 3) -> bool:
    return all(abs(index - existing) >= min_gap for existing in indexes)


def catch_lines() -> list[str]:
    raw = os.getenv(
        "CATCH_MANUAL_SUMMARY",
        "うるま市・与勝周辺：タマン好調|読谷周辺：タマン50cmクラス|港内：ミーバイ、チヌ、ハタ類",
    )
    return [line.strip() for line in raw.split("|") if line.strip()]


def build_x_text(date_text: str, weather: dict[str, str | float], tide: dict[str, str], catches: list[str], warning: str, morning: str, evening: str) -> str:
    catches_text = "\n".join(f"📍{line}" for line in catches)
    return f"""🎣沖縄釣果ダイジェスト（{date_text}）

🌊【潮見】
{tide["tide"]}
満潮：{tide["high_tide"]}
干潮：{tide["low_tide"]}

🌤【海況】
天気：{weather["weather"]}
風：{weather["wind_label"]}
波：{weather["wave_label"]}

🎣【直近釣果】
{catches_text}

🎯【今日の狙い目】
✅タマン
✅ミーバイ
✅チヌ
✅ハタ類

⏰おすすめ時間
朝：{morning}
夕：{evening}

⚠️{warning}

皆さんは今日はどこで釣りますか？
釣果情報や海況をリプで教えてください🎣

#沖縄釣り #沖縄釣果 #タマン #ミーバイ #チヌ #沖縄ルアー #釣り好きと繋がりたい"""


def build_markdown() -> str:
    today = dt.datetime.now(JST).date()
    date_slug = today.isoformat()
    date_text = fmt_date(today)
    weather = get_weather()
    tide = get_tide()
    catches = catch_lines()
    warning = warning_text(weather)
    morning, evening = fishing_times(weather)
    fish = "タマン,ミーバイ,チヌ,ハタ類"
    x_text = build_x_text(date_text, weather, tide, catches, warning, morning, evening)

    catches_md = "\n".join(f"- {line}" for line in catches)
    return f"""---
title: 沖縄釣果ダイジェスト｜{date_text}
date: {date_slug}
display_date: {date_text}
weather: {weather["weather"]}
wind: {weather["wind_label"]}
wave: {weather["wave_label"]}
tide: {tide["tide"]}
high_tide: {tide["high_tide"]}
low_tide: {tide["low_tide"]}
rating: {rating(weather)}
areas: 北部,中部,南部
fish: {fish}
catch: {"|".join(catches)}
morning_time: {morning}
evening_time: {evening}
warning: {warning}
eyecatch: assets/okinawa-fishing-info.png
---

## 今日の結論

{warning}

## 今日の海況

- 天気：{weather["weather"]}
- 風：{weather["wind_label"]}（{float(weather["wind"]):.1f}m/s）
- 波：{weather["wave_label"]}
- 雨：{float(weather["rain"]):.1f}mm
- 気温：{float(weather["temp"]):.0f}℃

## 潮見

- 潮：{tide["tide"]}
- 満潮：{tide["high_tide"]}
- 干潮：{tide["low_tide"]}

## 釣果情報

{catches_md}

## 今週のトレンド

海況回復後は、タマン、ミーバイ、チヌ、ハタ類を中心にチェック。港内や風裏では安全確認を優先しながら短時間で状況を見ましょう。

## X投稿用テキスト

```
{x_text}
```

## 注意事項

- 最新の気象情報を確認してください
- 高波やうねりがある日は外海に近づかないでください
- 船釣りや渡船は欠航情報を確認してください
- 初心者は荒天時の釣行を避けてください
"""


def main() -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(JST).date()
    path = POSTS_DIR / f"{today.isoformat()}.md"
    path.write_text(build_markdown(), encoding="utf-8")
    print(f"Generated {path}")


if __name__ == "__main__":
    main()
