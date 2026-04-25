import json
import os

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .utils import delete_files_by_type, detect_file_type, get_latest_judgement, get_latest_reports, get_latest_review


def index(request):
    """Redirect root URL to the report page."""
    return redirect('report')


def report(request):
    """Report page — renders AI trade reports."""
    return render(request, 'viewer/report.html', {
        'reports': get_latest_reports(),
    })


def review(request):
    """Review page — renders peer review of AI picks."""
    return render(request, 'viewer/review.html', {
        'review': get_latest_review(),
    })


def judgement(request):
    """Judgement page — renders final curated picks."""
    return render(request, 'viewer/judgement.html', {
        'judgement': get_latest_judgement(),
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
