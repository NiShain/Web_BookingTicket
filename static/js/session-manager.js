/* Minimal session-manager placeholder to avoid 404. Real implementation lives elsewhere. */
// session-manager.js
// Sends a logout request when the page is unloaded to ensure server-side logout.
// Uses navigator.sendBeacon when available to avoid blocking unload.

(function(){
  // If template didn't set window.USER_LOGGED_IN, assume false
  if (!window.USER_LOGGED_IN) {
    console.debug('session-manager: user not logged in, no action');
    return;
  }

  function getCsrfToken() {
    var match = document.cookie.match(new RegExp('(^|; )' + 'csrftoken' + '=([^;]+)'));
    return match ? match[2] : null;
  }

  function sendLogout() {
    try {
      var url = window.LOGOUT_URL || '/accounts/logout/';
      var csrf = getCsrfToken();

      if (navigator.sendBeacon) {
        // send a simple form-encoded payload; include csrf as query param (best-effort)
        var body = new Blob([new URLSearchParams({logout: '1'}).toString()], {type: 'application/x-www-form-urlencoded'});
        var beaconUrl = url;
        if (csrf) {
          beaconUrl = url + (url.indexOf('?') === -1 ? '?' : '&') + 'csrfmiddlewaretoken=' + encodeURIComponent(csrf);
        }
        navigator.sendBeacon(beaconUrl, body);
      } else {
        // Fallback: synchronous XHR during unload (may be blocked by browsers)
        var xhr = new XMLHttpRequest();
        xhr.open('POST', url, false);
        if (csrf) xhr.setRequestHeader('X-CSRFToken', csrf);
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        xhr.send('logout=1');
      }
    } catch (e) {
      console.warn('session-manager logout failed', e);
    }
  }

  window.addEventListener('beforeunload', function(){
    sendLogout();
  });

})();
