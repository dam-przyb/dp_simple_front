import json
import os
import re

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .utils import delete_files_by_type, detect_file_type, get_latest_judgement, get_latest_reports, get_latest_review


def _normalize_token(value: str) -> str:
    """Create a lowercase slug token used for stable UI IDs and matching."""
    cleaned = re.sub(r'[^a-z0-9]+', '-', (value or '').strip().lower())
    return cleaned.strip('-')


def _team_from_report_name(report_name: str) -> str:
    """Extract and normalize team name from report filenames when team is missing."""
    stem = os.path.splitext(os.path.basename(report_name or ''))[0]
    if '_report_' not in stem:
        return ''
    return _normalize_token(stem.split('_report_', 1)[1])


def index(request):
    """Redirect root URL to the report page."""
    return redirect('report')


def report(request):
    """Report page — renders AI trade reports."""
    reports = get_latest_reports()
    teams = list(dict.fromkeys(
        report.get('team', '')
        for report in reports
        if report.get('team')
    ))

    return render(request, 'viewer/report.html', {
        'reports': reports,
        'teams': teams,
    })


def review(request):
    """Review page — renders peer review of AI picks."""
    review_data = get_latest_review()
    review_picks = []
    review_teams = []
    seen_teams = set()

    for team_block in (review_data or {}).get('teams', []):
        team_label = team_block.get('team', '')
        team_slug = _normalize_token(team_label)
        if not team_slug:
            continue

        if team_slug not in seen_teams:
            review_teams.append({'slug': team_slug, 'label': team_label})
            seen_teams.add(team_slug)

        for pick in team_block.get('team_review', []):
            ticker = str(pick.get('ticker', '')).strip()
            ticker_slug = _normalize_token(ticker)
            anchor_id = f'pick-{team_slug}-{ticker_slug}' if ticker_slug else ''
            review_picks.append({
                'team': team_slug,
                'team_label': team_label,
                'ticker': ticker,
                'name': pick.get('stock_name', ''),
                'side': str(pick.get('side', '')).lower(),
                'note': pick.get('note', 0),
                'valid': bool(pick.get('still_valid', False)),
                'reasoning': pick.get('reasoning', ''),
                'anchor_id': anchor_id,
            })

    return render(request, 'viewer/review.html', {
        'review': review_data,
        'review_picks': review_picks,
        'review_teams': review_teams,
    })


def judgement(request):
    """Judgement page — renders final curated picks."""
    judgement_data = get_latest_judgement()
    if judgement_data:
        normalized_picks = []
        for pick in judgement_data.get('picks', []):
            item = dict(pick)
            team_slug = _normalize_token(item.get('team', '')) or _team_from_report_name(item.get('report_name', ''))
            ticker_slug = _normalize_token(str(item.get('ticker', '')))
            item['team'] = team_slug
            if team_slug and ticker_slug:
                item['review_anchor'] = f'pick-{team_slug}-{ticker_slug}'
            elif ticker_slug:
                item['review_anchor'] = f'ticker-{ticker_slug}'
            else:
                item['review_anchor'] = ''
            normalized_picks.append(item)
        judgement_data['picks'] = normalized_picks

    return render(request, 'viewer/judgement.html', {
        'judgement': judgement_data,
    })


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def upload(request):
    """Upload page — handles multi-file JSON upload."""
    if request.method == 'GET':
        return render(request, 'viewer/upload.html')

    # --- POST: process uploaded files ---
    data_dir = settings.DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for f in request.FILES.getlist('files'):
        # Sanitise filename — prevent any path traversal attempts
        filename = os.path.basename(f.name)

        # 1. Reject non-JSON extensions
        if not filename.lower().endswith('.json'):
            results.append({'filename': filename, 'ok': False,
                            'error': 'Only .json files are accepted', 'type': None})
            continue

        # 2. Read and validate JSON
        try:
            raw = f.read()
            json.loads(raw)   # will raise if invalid
        except (json.JSONDecodeError, Exception) as exc:
            results.append({'filename': filename, 'ok': False,
                            'error': f'Invalid JSON — {exc}', 'type': None})
            continue

        # 3. Detect document type from filename
        file_type = detect_file_type(filename)
        if file_type is None:
            results.append({
                'filename': filename, 'ok': False,
                'error': 'Unrecognised filename. Expected *_report_*, *_reviews*, or *judgement*.',
                'type': None,
            })
            continue

        # 4. For review / judgement: delete the old file of that type first
        if file_type == 'review':
            for old in data_dir.glob('*_reviews*.json'):
                old.unlink(missing_ok=True)
        elif file_type == 'judgement':
            for old in data_dir.glob('*judgement*.json'):
                old.unlink(missing_ok=True)

        # 5. Save to DATA_DIR
        dest = data_dir / filename
        try:
            with open(dest, 'wb') as out:
                out.write(raw)
            results.append({'filename': filename, 'ok': True, 'error': None, 'type': file_type})
        except OSError as exc:
            results.append({'filename': filename, 'ok': False,
                            'error': f'Could not save file: {exc}', 'type': None})

    return JsonResponse({'results': results})


@require_http_methods(["POST"])
def clean_files(request):
    """Delete all files of a given type from DATA_DIR."""
    file_type = request.POST.get('type', '')
    if file_type not in ('report', 'review', 'judgement'):
        return JsonResponse({'ok': False, 'error': 'Invalid type'}, status=400)

    deleted = delete_files_by_type(file_type)
    return JsonResponse({'ok': True, 'deleted': deleted, 'type': file_type})
