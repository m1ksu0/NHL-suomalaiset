"""Hakee suomalaisten NHL-pelaajien tiedot NHL:n (epävirallisesta) rajapinnasta
ja kirjoittaa ne tiedostoon data.json.

Sisältö:
  - kausitilastot (kenttäpelaajat ja maalivahdit, kansallisuus FIN)
  - kahden edellisen pelipäivän ottelut, tulokset ja suomalaisten ottelukohtaiset luvut
  - seuraavan 7 päivän ottelut, jotka alkavat Suomen aikaa klo 18-23, ja joukkueiden suomalaiset

Ajo: python fetch_data.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

WEB_API = "https://api-web.nhle.com/v1"
STATS_API = "https://api.nhle.com/stats/rest/en"
HELSINKI = ZoneInfo("Europe/Helsinki")
OUT_FILE = Path(__file__).with_name("data.json")

RESULT_DAYS = 2                      # montako edellistä pelipäivää näytetään
UPCOMING_DAYS = 7                    # montako päivää eteenpäin katsotaan
WINDOW_START = dtime(18, 0)          # Suomen aikaa, mukana
WINDOW_END = dtime(23, 0)            # Suomen aikaa, mukana
FINISHED_STATES = {"FINAL", "OFF"}
HEADERS = {"User-Agent": "nhl-suomalaiset (henkilokohtainen projekti)"}


# --------------------------------------------------------------------------- HTTP

def get_json(url: str, params: dict | None = None, retries: int = 3) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Haku epäonnistui: {url} ({last_error})")


# --------------------------------------------------------------------------- apufunktiot

def season_id(today: date) -> int:
    """Kausi-id: syys-joulukuussa alkava vuosi, muuten edellinen. 2026-11-06 -> 20262027."""
    start_year = today.year if today.month >= 8 else today.year - 1
    return start_year * 10000 + start_year + 1


def parse_utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def in_time_window(start_utc: datetime) -> bool:
    """Alkaako ottelu Suomen aikaa välillä WINDOW_START - WINDOW_END (molemmat mukana)?"""
    t = start_utc.astimezone(HELSINKI).time().replace(second=0, microsecond=0)
    return WINDOW_START <= t <= WINDOW_END


def outcome_label(last_period_type: str | None) -> str:
    return {"OT": "JA", "SO": "VL"}.get(last_period_type or "", "")


def team_info(team: dict) -> dict:
    return {
        "abbrev": team.get("abbrev", "?"),
        "name": (team.get("commonName") or {}).get("default", ""),
        "score": team.get("score"),
    }


# --------------------------------------------------------------------------- tilastot

def fetch_finnish_stats(season: int) -> tuple[list[dict], list[dict]]:
    params = {
        "limit": -1,
        "cayenneExp": f'seasonId={season} and gameTypeId=2 and nationalityCode="FIN"',
    }
    skaters = get_json(f"{STATS_API}/skater/summary", {**params, "sort": "points"})["data"]
    goalies = get_json(f"{STATS_API}/goalie/summary", params)["data"]
    skaters = [
        {
            "id": s["playerId"], "name": s["skaterFullName"], "team": s["teamAbbrevs"],
            "pos": s["positionCode"], "gp": s["gamesPlayed"], "g": s["goals"],
            "a": s["assists"], "p": s["points"], "pm": s["plusMinus"],
            "pim": s["penaltyMinutes"], "sog": s["shots"],
            "toi": round((s.get("timeOnIcePerGame") or 0) / 60, 1),
        }
        for s in skaters
    ]
    goalies = [
        {
            "id": g["playerId"], "name": g["goalieFullName"], "team": g["teamAbbrevs"],
            "gp": g["gamesPlayed"], "gs": g.get("gamesStarted"), "w": g["wins"],
            "l": g["losses"], "otl": g.get("otLosses"), "svpct": g["savePct"],
            "gaa": g["goalsAgainstAverage"],
        }
        for g in goalies
    ]
    skaters.sort(key=lambda r: (-r["p"], -r["g"], r["gp"]))
    goalies.sort(key=lambda r: -r["gp"])
    return skaters, goalies


# --------------------------------------------------------------------------- kalenteri

def fetch_schedule(start: date, end: date) -> dict[str, list[dict]]:
    """Palauttaa {pelipäivä: [ottelut]} väliltä start-end (NHL:n pelipäivät)."""
    games: dict[str, list[dict]] = {}
    seen: set[int] = set()
    cursor = start
    while cursor <= end:
        data = get_json(f"{WEB_API}/schedule/{cursor.isoformat()}")
        for day in data.get("gameWeek", []):
            for g in day.get("games", []):
                if g["id"] in seen:
                    continue
                seen.add(g["id"])
                games.setdefault(day["date"], []).append(g)
        nxt = data.get("nextStartDate")
        if not nxt:
            break
        new_cursor = date.fromisoformat(nxt)
        if new_cursor <= cursor:
            break
        cursor = new_cursor
    return games


# --------------------------------------------------------------------------- suomalaiset

def fetch_finnish_rosters(team_abbrevs: set[str]) -> dict[str, list[dict]]:
    """Joukkueittain nykyiset suomalaissyntyiset pelaajat (birthCountry == FIN)."""
    by_team: dict[str, list[dict]] = {}
    for abbrev in sorted(team_abbrevs):
        try:
            roster = get_json(f"{WEB_API}/roster/{abbrev}/current")
        except RuntimeError as exc:
            print(f"VAROITUS: kokoonpano puuttuu ({abbrev}): {exc}", file=sys.stderr)
            continue
        players = []
        for group in ("forwards", "defensemen", "goalies"):
            for p in roster.get(group, []):
                if p.get("birthCountry") == "FIN":
                    players.append({
                        "id": p["id"],
                        "name": f'{p["firstName"]["default"]} {p["lastName"]["default"]}',
                        "pos": p.get("positionCode", ""),
                    })
        by_team[abbrev] = players
    return by_team


def finnish_lines(box: dict, finnish_ids: set[int], names: dict[int, str]) -> dict:
    """Poimii boxscoresta suomalaisten ottelukohtaiset luvut."""
    skaters, goalies = [], []
    stats = box.get("playerByGameStats", {})
    for side in ("awayTeam", "homeTeam"):
        team = box.get(side, {}).get("abbrev", "?")
        team_stats = stats.get(side, {})
        for p in team_stats.get("forwards", []) + team_stats.get("defense", []):
            if p["playerId"] not in finnish_ids:
                continue
            skaters.append({
                "name": names.get(p["playerId"], p["name"]["default"]),
                "team": team, "pos": p.get("position", ""),
                "g": p.get("goals", 0), "a": p.get("assists", 0), "p": p.get("points", 0),
                "pm": p.get("plusMinus", 0), "toi": p.get("toi", ""),
            })
        for p in team_stats.get("goalies", []):
            if p["playerId"] not in finnish_ids:
                continue
            if not p.get("toi") or p.get("toi") == "00:00":
                continue  # ei pelannut
            goalies.append({
                "name": names.get(p["playerId"], p["name"]["default"]),
                "team": team, "saves": p.get("saves"), "shots": p.get("shotsAgainst"),
                "ga": p.get("goalsAgainst"), "svpct": p.get("savePctg"),
                "decision": p.get("decision", ""), "toi": p.get("toi", ""),
            })
    skaters.sort(key=lambda r: (-r["p"], -r["g"], r["name"]))
    return {"skaters": skaters, "goalies": goalies}


# --------------------------------------------------------------------------- pääohjelma

def main() -> int:
    now_utc = datetime.now(timezone.utc)
    today_fi = now_utc.astimezone(HELSINKI).date()
    season = season_id(today_fi)
    print(f"Päivä (Suomi): {today_fi}, kausi {season}")

    skaters, goalies = fetch_finnish_stats(season)
    print(f"Suomalaisia: {len(skaters)} kenttäpelaajaa, {len(goalies)} maalivahtia")

    first_result_day = today_fi - timedelta(days=RESULT_DAYS)
    last_day = today_fi + timedelta(days=UPCOMING_DAYS)
    schedule = fetch_schedule(first_result_day, last_day)

    result_dates = {(today_fi - timedelta(days=i)).isoformat() for i in range(1, RESULT_DAYS + 1)}
    result_games = {d: gs for d, gs in schedule.items() if d in result_dates}

    upcoming = []
    last_fi_date = today_fi + timedelta(days=UPCOMING_DAYS - 1)
    for day_games in schedule.values():
        for g in day_games:
            if g.get("gameState") in FINISHED_STATES or g.get("gameState") == "LIVE":
                continue
            start = parse_utc(g["startTimeUTC"])
            start_fi = start.astimezone(HELSINKI)
            if start < now_utc or start_fi.date() > last_fi_date:
                continue
            if not in_time_window(start):
                continue
            upcoming.append((start, g))
    upcoming.sort(key=lambda x: x[0])

    teams = {t for gs in result_games.values() for g in gs for t in (g["awayTeam"]["abbrev"], g["homeTeam"]["abbrev"])}
    teams |= {t for _, g in upcoming for t in (g["awayTeam"]["abbrev"], g["homeTeam"]["abbrev"])}
    rosters = fetch_finnish_rosters(teams)

    names = {p["id"]: p["name"] for players in rosters.values() for p in players}
    names.update({s["id"]: s["name"] for s in skaters})
    names.update({g["id"]: g["name"] for g in goalies})
    finnish_ids = set(names)

    results = []
    for day in sorted(result_games, reverse=True):
        day_games = []
        for g in sorted(result_games[day], key=lambda x: x["startTimeUTC"]):
            if g.get("gameState") not in FINISHED_STATES:
                continue
            entry = {
                "id": g["id"],
                "start_fi": parse_utc(g["startTimeUTC"]).astimezone(HELSINKI).strftime("%H:%M"),
                "away": team_info(g["awayTeam"]), "home": team_info(g["homeTeam"]),
                "outcome": outcome_label((g.get("gameOutcome") or {}).get("lastPeriodType")),
                "finns": {"skaters": [], "goalies": []},
            }
            try:
                box = get_json(f"{WEB_API}/gamecenter/{g['id']}/boxscore")
                entry["finns"] = finnish_lines(box, finnish_ids, names)
            except RuntimeError as exc:
                print(f"VAROITUS: boxscore puuttuu ({g['id']}): {exc}", file=sys.stderr)
                entry["box_missing"] = True
            day_games.append(entry)
        results.append({"date": day, "games": day_games})

    upcoming_out = []
    for start, g in upcoming:
        away, home = g["awayTeam"]["abbrev"], g["homeTeam"]["abbrev"]
        start_fi = start.astimezone(HELSINKI)
        upcoming_out.append({
            "id": g["id"],
            "date_fi": start_fi.date().isoformat(),
            "time_fi": start_fi.strftime("%H:%M"),
            "away": team_info(g["awayTeam"]), "home": team_info(g["homeTeam"]),
            "finns": [
                {**p, "team": team}
                for team in (away, home) for p in rosters.get(team, [])
            ],
        })

    data = {
        "generated_at": now_utc.isoformat(timespec="seconds"),
        "season": season,
        "skaters": skaters,
        "goalies": goalies,
        "results": results,
        "upcoming": upcoming_out,
    }
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    n_games = sum(len(d["games"]) for d in results)
    print(f"Kirjoitettu {OUT_FILE.name}: {n_games} tulosta, {len(upcoming_out)} tulevaa ottelua")
    return 0


if __name__ == "__main__":
    sys.exit(main())
