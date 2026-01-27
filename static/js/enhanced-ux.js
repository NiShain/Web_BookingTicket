/**
 * 🎨 FUTA BUS - Enhanced UX JavaScript
 * Advanced user experience enhancements
 */

(function() {
  'use strict';

  // ========================================
  // 🎯 Auto-hide messages after delay
  // ========================================
  function initAutoHideMessages() {
    const messages = document.querySelectorAll('.message, .alert');
    
    messages.forEach(function(message) {
      setTimeout(function() {
        message.classList.add('fade-out');
        
        setTimeout(function() {
          message.remove();
        }, 400); // Remove after fade animation
      }, 5000); // Auto-hide after 5 seconds
    });
  }

  // ========================================
  // 🔄 Form Loading States
  // ========================================
  function initFormLoadingStates() {
    const forms = document.querySelectorAll('form[data-loading]');
    
    forms.forEach(function(form) {
      form.addEventListener('submit', function(e) {
        const submitBtn = form.querySelector('button[type="submit"]');
        
        if (submitBtn && !submitBtn.disabled) {
          // Save original text
          const originalText = submitBtn.innerHTML;
          submitBtn.dataset.originalText = originalText;
          
          // Add loading state
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<span class="loading"></span> Đang xử lý...';
          submitBtn.style.opacity = '0.7';
          submitBtn.style.cursor = 'not-allowed';
        }
      });
    });
  }

  // ========================================
  // ✅ Real-time Form Validation
  // ========================================
  function initRealTimeValidation() {
    const inputs = document.querySelectorAll('input[required], input[type="email"], input[type="tel"]');
    
    inputs.forEach(function(input) {
      // Validate on blur
      input.addEventListener('blur', function() {
        validateInput(input);
      });
      
      // Clear validation on input
      input.addEventListener('input', function() {
        if (input.classList.contains('is-invalid') || input.classList.contains('is-valid')) {
          validateInput(input);
        }
      });
    });
  }

  function validateInput(input) {
    const value = input.value.trim();
    const type = input.type;
    let isValid = true;
    let errorMessage = '';
    
    // Required validation
    if (input.hasAttribute('required') && !value) {
      isValid = false;
      errorMessage = 'Trường này là bắt buộc';
    }
    
    // Email validation
    else if (type === 'email' && value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) {
        isValid = false;
        errorMessage = 'Email không hợp lệ';
      }
    }
    
    // Phone validation (Vietnamese format)
    else if (type === 'tel' && value) {
      const phoneRegex = /^(0|\+84)[0-9]{9,10}$/;
      if (!phoneRegex.test(value.replace(/\s/g, ''))) {
        isValid = false;
        errorMessage = 'Số điện thoại không hợp lệ';
      }
    }
    
    // Apply validation classes
    if (isValid) {
      input.classList.remove('is-invalid');
      input.classList.add('is-valid');
      removeErrorMessage(input);
    } else {
      input.classList.remove('is-valid');
      input.classList.add('is-invalid');
      showErrorMessage(input, errorMessage);
    }
  }

  function showErrorMessage(input, message) {
    removeErrorMessage(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-error';
    errorDiv.textContent = message;
    input.parentNode.appendChild(errorDiv);
  }

  function removeErrorMessage(input) {
    const existingError = input.parentNode.querySelector('.form-error');
    if (existingError) {
      existingError.remove();
    }
  }

  // ========================================
  // 🎨 Smooth Scroll to Anchor Links
  // ========================================
  function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(function(link) {
      link.addEventListener('click', function(e) {
        const href = link.getAttribute('href');
        
        if (href === '#') return;
        
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });
  }

  // ========================================
  // 💾 Form Auto-save (Draft)
  // ========================================
  function initFormAutoSave() {
    const forms = document.querySelectorAll('[data-autosave]');
    
    forms.forEach(function(form) {
      const formId = form.dataset.autosave;
      
      // Load saved data
      loadFormData(form, formId);
      
      // Save on input
      const inputs = form.querySelectorAll('input, textarea, select');
      inputs.forEach(function(input) {
        input.addEventListener('input', debounce(function() {
          saveFormData(form, formId);
        }, 1000));
      });
      
      // Clear saved data on successful submit
      form.addEventListener('submit', function() {
        clearFormData(formId);
      });
    });
  }

  function saveFormData(form, formId) {
    try {
      const formData = {};
      const inputs = form.querySelectorAll('input, textarea, select');
      
      inputs.forEach(function(input) {
        if (input.name && input.type !== 'password') {
          formData[input.name] = input.value;
        }
      });
      
      localStorage.setItem('form_' + formId, JSON.stringify(formData));
      
      // Show subtle feedback
      showAutoSaveFeedback(form);
    } catch (e) {
      console.warn('Could not save form data:', e);
    }
  }

  function loadFormData(form, formId) {
    try {
      const savedData = localStorage.getItem('form_' + formId);
      if (savedData) {
        const formData = JSON.parse(savedData);
        
        Object.keys(formData).forEach(function(name) {
          const input = form.querySelector('[name="' + name + '"]');
          if (input && !input.value) {
            input.value = formData[name];
          }
        });
      }
    } catch (e) {
      console.warn('Could not load form data:', e);
    }
  }

  function clearFormData(formId) {
    try {
      localStorage.removeItem('form_' + formId);
    } catch (e) {
      console.warn('Could not clear form data:', e);
    }
  }

  function showAutoSaveFeedback(form) {
    let indicator = form.querySelector('.autosave-indicator');
    
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'autosave-indicator';
      indicator.style.cssText = 'position: absolute; top: 10px; right: 10px; padding: 5px 10px; background: #10b981; color: white; border-radius: 5px; font-size: 0.75rem; opacity: 0; transition: opacity 0.3s;';
      indicator.textContent = '✓ Đã lưu nháp';
      form.style.position = 'relative';
      form.appendChild(indicator);
    }
    
    indicator.style.opacity = '1';
    setTimeout(function() {
      indicator.style.opacity = '0';
    }, 2000);
  }

  // ========================================
  // 🎭 Animate Elements on Scroll
  // ========================================
  function initScrollAnimations() {
    const elements = document.querySelectorAll('[data-animate]');
    
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('fade-in');
            observer.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.1
      });
      
      elements.forEach(function(el) {
        observer.observe(el);
      });
    } else {
      // Fallback for older browsers
      elements.forEach(function(el) {
        el.classList.add('fade-in');
      });
    }
  }

  // ========================================
  // 📱 Mobile Menu Toggle
  // ========================================
  function initMobileMenu() {
    const menuToggle = document.querySelector('[data-menu-toggle]');
    const menu = document.querySelector('[data-menu]');
    
    if (menuToggle && menu) {
      menuToggle.addEventListener('click', function() {
        menu.classList.toggle('active');
        menuToggle.classList.toggle('active');
      });
    }
  }

  // ========================================
  // 🔍 Search Input Enhancement
  // ========================================
  function initSearchEnhancements() {
    const searchInputs = document.querySelectorAll('input[type="search"], input[data-search]');
    
    searchInputs.forEach(function(input) {
      // Add clear button
      const clearBtn = document.createElement('button');
      clearBtn.type = 'button';
      clearBtn.className = 'search-clear-btn';
      clearBtn.innerHTML = '×';
      clearBtn.style.cssText = 'position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; font-size: 1.5rem; color: #999; cursor: pointer; display: none;';
      
      input.parentNode.style.position = 'relative';
      input.parentNode.appendChild(clearBtn);
      
      // Show/hide clear button
      input.addEventListener('input', function() {
        clearBtn.style.display = input.value ? 'block' : 'none';
      });
      
      // Clear on button click
      clearBtn.addEventListener('click', function() {
        input.value = '';
        input.focus();
        clearBtn.style.display = 'none';
        input.dispatchEvent(new Event('input'));
      });
    });
  }

  // ========================================
  // 🎯 Tooltip System
  // ========================================
  function initTooltips() {
    const elements = document.querySelectorAll('[data-tooltip]');
    
    elements.forEach(function(el) {
      el.addEventListener('mouseenter', function() {
        showTooltip(el);
      });
      
      el.addEventListener('mouseleave', function() {
        hideTooltip(el);
      });
    });
  }

  function showTooltip(el) {
    const text = el.dataset.tooltip;
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = 'position: absolute; background: #1f2937; color: white; padding: 6px 12px; border-radius: 6px; font-size: 0.875rem; white-space: nowrap; z-index: 9999; pointer-events: none;';
    
    document.body.appendChild(tooltip);
    
    const rect = el.getBoundingClientRect();
    tooltip.style.top = (rect.top - tooltip.offsetHeight - 8) + 'px';
    tooltip.style.left = (rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)) + 'px';
    
    el._tooltip = tooltip;
  }

  function hideTooltip(el) {
    if (el._tooltip) {
      el._tooltip.remove();
      delete el._tooltip;
    }
  }

  // ========================================
  // 🛠️ Utility Functions
  // ========================================
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = function() {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // ========================================
  // 🚀 Initialize All Enhancements
  // ========================================
  function init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        initAll();
      });
    } else {
      initAll();
    }
  }

  function initAll() {
    console.log('🎨 Initializing UX enhancements...');
    
    initAutoHideMessages();
    initFormLoadingStates();
    initRealTimeValidation();
    initSmoothScroll();
    initFormAutoSave();
    initScrollAnimations();
    initMobileMenu();
    initSearchEnhancements();
    initTooltips();
    
    console.log('✅ UX enhancements initialized');
  }

  // Start initialization
  init();

  // Expose public API
  window.FutaBusUX = {
    validateInput: validateInput,
    showTooltip: showTooltip,
    hideTooltip: hideTooltip
  };

})();
