"""
Utility functions for loading and parsing JSON data files.
All functions read from settings.DATA_DIR and handle missing files gracefully.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings


def _load_json(path: Path) -> dict | list | None:
    """Read and parse a single JSON file. Returns None if file is missing or invalid."""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def detect_file_type(filename: str) -> str | None:
    """
    Determine the document type from a filename.
    Returns 'report', 'review', 'judgement', or None.
    """
    name = Path(filename).name
    if '_report_' in name:
        return 'report'
    if '_reviews' in name or 'reviews' in name:
        return 'review'
    if 'judgement' in name:
        return 'judgement'
    return None


def _extract_team(filename: str) -> str:
    """
    Pull the team name out of a report filename.
    e.g. '202604181218_report_deepseek.json' -> 'deepseek'
    """
    stem = Path(filename).stem  # strip .json
    parts = stem.split('_report_')
    if len(parts) == 2:
        return parts[1].capitalize()
    return stem


def _extract_date(filename: str) -> str:
    """
    Pull the date from a report filename.
    e.g. '202604181218_report_deepseek.json' -> '20260418'
    """
    match = re.match(r'^(\d{8})', Path(filename).name)
    return match.group(1) if match else ''


def _upside_pct(last_close: float, target: float, side: str) -> float | None:
    """Calculate implied upside % given direction."""
    try:
        if side == 'long':
            return round((target - last_close) / last_close * 100, 1)
        else:
            return round((last_close - target) / last_close * 100, 1)
    except (ZeroDivisionError, TypeError):
        return None


def _source_display(url: str) -> str:
    """Return a short human-readable label for a source URL."""
    try:
        host = urlparse(url).netloc
        return host.replace('www.', '')
    except Exception:
        return url


def get_latest_reports(data_dir: Path = None) -> list[dict]:
    """
    Return a list of all report files found in data_dir, each enriched with:
    - team: str  (extracted from filename)
    - date: str  (YYYYMMDD)
    - picks: the company_picks list, each pick augmented with upside_pct and side_str
    - market_overview: the general_market_overview string
    Sorted by filename (chronological by timestamp in name).
    """
    if data_dir is None:
        data_dir = settings.DATA_DIR

    results = []
    for path in sorted(data_dir.glob('*_report_*.json')):
        data = _load_json(path)
        if data is None:
            continue

        team = _extract_team(path.name)
        date_str = _extract_date(path.name)

        picks = []
        for pick in data.get('company_picks', []):
            pricing = pick.get('pricing_data', {})
            raw_side = pricing.get('side', ['long'])
            side_str = raw_side[0] if isinstance(raw_side, list) else raw_side
            last_close = pricing.get('last_close_price')
            target = pricing.get('target_price')

            picks.append({
                'name': pick.get('company_info', {}).get('name', ''),
                'ticker': pick.get('company_info', {}).get('ticker', ''),
                'side': side_str,
                'last_close': last_close,
                'target_price': target,
                'upside_pct': _upside_pct(last_close, target, side_str),
                'technical_summary': pick.get('analysis_summary', {}).get('technical_summary', ''),
                'fundamental_situation': pick.get('analysis_summary', {}).get('fundamental_situation', ''),
                'detailed_report': pick.get('detailed_report', ''),
                'sources': [
                    {'url': s, 'label': _source_display(s)}
                    for s in pick.get('sources', [])
                ],
            })

        results.append({
            'team': team,
            'date': date_str,
            'market_overview': data.get('general_market_overview', ''),
            'picks': picks,
        })

    return results


def get_latest_review(data_dir: Path = None) -> dict | None:
    """
    Return the parsed review file content, or None if not found.
    Adds a formatted date string.
    """
    if data_dir is None:
        data_dir = settings.DATA_DIR

    paths = sorted(data_dir.glob('*_reviews.json'))
    if not paths:
        return None

    data = _load_json(paths[-1])  # most recent if multiple exist
    if data is None:
        return None

    raw_date = data.get('date', '')
    data['date_display'] = _format_date(raw_date)
    return data


def get_latest_judgement(data_dir: Path = None) -> dict | None:
    """
    Return the parsed judgement file content, or None if not found.
    Adds a formatted date string.
    """
    if data_dir is None:
        data_dir = settings.DATA_DIR

    paths = sorted(data_dir.glob('*judgement*.json'))
    if not paths:
        return None

    data = _load_json(paths[-1])
    if data is None:
        return None

    raw_date = data.get('judgement_date', '')
    data['date_display'] = _format_date(raw_date)
    return data


def _format_date(raw: str) -> str:
    """
    Turn '20260418' into 'April 18, 2026'.
    Returns raw string unchanged if it can't be parsed.
    """
    try:
        from datetime import datetime
        dt = datetime.strptime(raw[:8], '%Y%m%d')
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    except (ValueError, TypeError):
        return raw
