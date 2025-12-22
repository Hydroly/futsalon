from fastapi import Request
from fastapi.responses import RedirectResponse

def is_logged_in(request: Request):
    return request.session.get("admin")

def login_required(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
