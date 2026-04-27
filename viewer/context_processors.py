def remote_user(request):
    """
    Expose the HTTP Basic Auth username to all templates as {{ remote_user }}.
    Nginx passes it via the X-Remote-User header (proxy_set_header X-Remote-User $remote_user).
    Falls back to empty string if the header is absent (e.g. local dev without Nginx).
    """
    return {'remote_user': request.META.get('HTTP_X_REMOTE_USER', '')}
