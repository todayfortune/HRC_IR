from __future__ import annotations

import json
import re
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests


HANA_RATE_URL = "https://biz.kebhana.com/foex/rate/wcfxd740_201i_01.do"
SEOUL = ZoneInfo("Asia/Seoul")
WINDOW_START = "15:30:00"
WINDOW_END = "15:32:59"


class HanaRateError(RuntimeError):
    pass


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("th", "td") and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("th", "td") and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def parse_hana_usd_html(html: str, reference_date: str) -> dict[str, Any]:
    parser = _TableParser()
    parser.feed(html)
    required = ("고시회차", "고시일자", "고시시간", "매매기준율")
    rate_table: list[list[str]] | None = None
    header: list[str] = []
    for table in parser.tables:
        if not table:
            continue
        compact_header = [_compact(cell) for cell in table[0]]
        if all(field in compact_header for field in required):
            rate_table = table
            header = compact_header
            break
    if rate_table is None:
        raise HanaRateError("하나은행 응답에서 환율 표 헤더를 찾지 못했습니다.")

    indexes = {field: header.index(field) for field in required}
    candidates: list[dict[str, Any]] = []
    for cells in rate_table[1:]:
        if len(cells) <= max(indexes.values()):
            continue
        announced_date = cells[indexes["고시일자"]]
        announced_time = cells[indexes["고시시간"]]
        if announced_date != reference_date or not (WINDOW_START <= announced_time <= WINDOW_END):
            continue
        try:
            candidates.append({
                "value": float(cells[indexes["매매기준율"]].replace(",", "")),
                "source": "하나은행",
                "rateType": "매매기준율",
                "referenceDate": announced_date,
                "announcementNumber": int(cells[indexes["고시회차"]]),
                "announcementTime": announced_time,
            })
        except (TypeError, ValueError) as exc:
            raise HanaRateError("하나은행 환율 행의 숫자 형식이 올바르지 않습니다.") from exc
    if not candidates:
        raise HanaRateError(f"{reference_date} {WINDOW_START}~{WINDOW_END} 고시가 없습니다.")
    return min(candidates, key=lambda row: (row["announcementTime"], row["announcementNumber"]))


def fetch_hana_usd_rate(reference_date: date, timeout: float = 30.0) -> dict[str, Any]:
    date_text = reference_date.isoformat()
    response = requests.post(
        HANA_RATE_URL,
        data={
            "inqDt": reference_date.strftime("%Y%m%d"),
            "curCd": "USD",
            "inqDvCd": "1",
            "pbldTm": "000000",
            "tmpDt": date_text,
        },
        headers={"User-Agent": "HRC-IR/1.0", "X-Requested-With": "XMLHttpRequest"},
        timeout=timeout,
    )
    response.raise_for_status()
    result = parse_hana_usd_html(response.text, date_text)
    result["updatedAt"] = datetime.now(SEOUL).isoformat(timespec="seconds")
    return result


def save_exchange_snapshot(result: dict[str, Any], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
