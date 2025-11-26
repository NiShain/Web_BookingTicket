/* Session manager - Auto logout when browser closes completely */
(function(){
  console.debug('session-manager: Monitoring browser close for auto-logout');
  
  // Check if user is authenticated
  const isAuthenticated = document.body.dataset.userAuthenticated === 'true';
  
  if (!isAuthenticated) {
    console.debug('session-manager: User not authenticated, skipping');
    return;
  }

  // Use sessionStorage to track if any tab is still open
  // sessionStorage is cleared when the last tab closes
  const TAB_ID = 'tab_' + Date.now() + '_' + Math.random();
  const ACTIVE_TABS_KEY = 'active_tabs';
  
  // Get current active tabs from sessionStorage
  function getActiveTabs() {
    try {
      const tabs = sessionStorage.getItem(ACTIVE_TABS_KEY);
      return tabs ? JSON.parse(tabs) : [];
    } catch (e) {
      return [];
    }
  }
  
  // Save active tabs to sessionStorage
  function setActiveTabs(tabs) {
    try {
      sessionStorage.setItem(ACTIVE_TABS_KEY, JSON.stringify(tabs));
    } catch (e) {
      console.error('session-manager: Failed to save tabs', e);
    }
  }
  
  // Register this tab as active
  function registerTab() {
    const tabs = getActiveTabs();
    if (!tabs.includes(TAB_ID)) {
      tabs.push(TAB_ID);
      setActiveTabs(tabs);
      console.debug('session-manager: Tab registered', TAB_ID);
    }
  }
  
  // Unregister this tab
  function unregisterTab() {
    const tabs = getActiveTabs();
    const index = tabs.indexOf(TAB_ID);
    if (index > -1) {
      tabs.splice(index, 1);
      setActiveTabs(tabs);
      console.debug('session-manager: Tab unregistered', TAB_ID, 'Remaining tabs:', tabs.length);
    }
    return tabs.length;
  }
  
  // Send logout request
  function sendLogout() {
    const logoutUrl = window.LOGOUT_URL || '/logout/';
    console.debug('session-manager: Sending logout request to', logoutUrl);
    
    // Use sendBeacon for reliable delivery even when page is closing
    if (navigator.sendBeacon) {
      // Get CSRF token
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                       document.querySelector('meta[name="csrf-token"]')?.content ||
                       getCookie('csrftoken');
      
      const formData = new FormData();
      formData.append('csrfmiddlewaretoken', csrfToken);
      
      navigator.sendBeacon(logoutUrl, formData);
    } else {
      // Fallback for older browsers
      fetch(logoutUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
        keepalive: true
      }).catch(err => console.error('session-manager: Logout failed', err));
    }
  }
  
  // Get cookie value
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }
  
  // Register this tab on page load
  registerTab();
  
  // Update tab registry on page show (back/forward navigation)
  window.addEventListener('pageshow', function(event) {
    registerTab();
  });
  
  // Handle tab/browser close
  window.addEventListener('beforeunload', function(event) {
    const remainingTabs = unregisterTab();
    
    // If this is the last tab, logout
    if (remainingTabs === 0) {
      console.debug('session-manager: Last tab closing, triggering logout');
      sendLogout();
    }
  });
  
  // Handle page hide (mobile browsers, background tabs)
  window.addEventListener('pagehide', function(event) {
    if (event.persisted) {
      // Page is going into bfcache, don't logout
      console.debug('session-manager: Page cached, not logging out');
    } else {
      // Page is being unloaded
      const remainingTabs = unregisterTab();
      if (remainingTabs === 0) {
        console.debug('session-manager: Last tab closing (pagehide), triggering logout');
        sendLogout();
      }
    }
  });
  
  // Cleanup on visibility change (optional - keep tab registry updated)
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      console.debug('session-manager: Tab hidden');
    } else {
      console.debug('session-manager: Tab visible, re-registering');
      registerTab();
    }
  });
  
  console.debug('session-manager: Initialized for tab', TAB_ID);
})();
