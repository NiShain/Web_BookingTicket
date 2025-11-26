from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
import time
import logging

logger = logging.getLogger(__name__)


class AutoLogoutMiddleware:
    """Middleware to automatically log out users after a period of inactivity.

    Behavior:
    - If the user is authenticated, middleware checks `request.session['last_activity']`.
    - If the elapsed time since last activity exceeds `AUTO_LOGOUT_DELAY` (seconds), the
      user is logged out and redirected to the login page with `?expired=1`.
    - Otherwise, updates `last_activity` to the current time.

    The middleware skips redirect when the current path is the login/logout/verify/password
    endpoints to avoid redirect loops.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'AUTO_LOGOUT_DELAY', 300)

    def __call__(self, request):
        try:
            # Only enforce for authenticated users and when sessions are enabled
            if request.user.is_authenticated:
                # Paths to ignore to avoid redirect loops
                ignored_names = {
                    getattr(settings, 'LOGIN_URL', '/login/'),
                }
                # attempt to resolve LOGIN_URL to a path name
                try:
                    login_path = reverse(getattr(settings, 'LOGIN_URL'))
                except Exception:
                    login_path = None

                # If current path is login page or logout, skip enforcement
                if login_path and request.path == login_path:
                    return self.get_response(request)

                last_activity = request.session.get('last_activity')
                now = time.time()
                
                logger.info(f"[MIDDLEWARE] Path: {request.path}, User: {request.user.username}, last_activity: {last_activity}")
                
                # Initialize if None (first request after login)
                if last_activity is None:
                    logger.info(f"[INIT] Initializing last_activity for user {request.user.username}")
                    request.session['last_activity'] = now
                    request.session.modified = True
                else:
                    # Check for timeout
                    elapsed = now - float(last_activity)
                    logger.info(f"[CHECK] Elapsed: {elapsed:.2f}s, Timeout: {self.timeout}s")
                    
                    if elapsed > self.timeout:
                        logger.warning(f"[LOGOUT] Session timeout for user {request.user.username}")
                        logout(request)
                        login_url = login_path or getattr(settings, 'LOGIN_URL', '/login/')
                        if not login_url.startswith('/'):
                            try:
                                login_url = reverse(login_url)
                            except Exception:
                                login_url = '/'
                        return redirect(f"{login_url}?expired=1&reason=Timeout")
                    
                    # Update last activity for this request
                    logger.info(f"[UPDATE] Updating last_activity from {last_activity} to {now}")
                    request.session['last_activity'] = now
                    request.session.modified = True
        except Exception as e:
            # Log the exception but don't break the site
            logger.exception(f"[ERROR] Middleware error: {e}")

        response = self.get_response(request)
        return response
