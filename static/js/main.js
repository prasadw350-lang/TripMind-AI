/* Shared helpers for every page. Vanilla JS only. */

const App = (() => {
  /* ------------------------------------------------------------ toasts */
  function toast(message, type = 'info', ms = 4200) {
    const host = document.getElementById('toastHost');
    if (!host) { return; }
    const el = document.createElement('div');
    el.className = 'toast ' + type;
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => el.remove(), ms);
  }

  /* --------------------------------------------------------------- api */
  async function api(url, options = {}) {
    let res;
    try {
      res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        ...options,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });
    } catch (e) {
      throw new Error('Cannot reach the server. Please check that the app is running.');
    }
    if (res.status === 401) {
      throw new Error('Your session expired. Please sign in again.');
    }
    let data = {};
    try { data = await res.json(); } catch (e) { data = {}; }
    if (!res.ok) { throw new Error(data.error || 'Something went wrong. Please try again.'); }
    return data;
  }

  /* ------------------------------------------------------------ format */
  const inr = (value) => {
    const n = Number(value);
    if (!isFinite(n)) { return '—'; }
    return '₹' + Math.round(n).toLocaleString('en-IN');
  };

  const esc = (value) => String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const fallbackImage = 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=1200&q=70';

  function img(src, alt) {
    return `<img src="${esc(src || fallbackImage)}" alt="${esc(alt)}" loading="lazy"
      onerror="this.onerror=null;this.src='${fallbackImage}'">`;
  }

  /* --------------------------------------------------------- form state */
  function readPreferences(form) {
    const fd = new FormData(form);
    return {
      budget_inr: fd.get('budget_inr'),
      days: fd.get('days'),
      travel_type: fd.get('travel_type') || null,
      season: fd.get('season') || null,
      start_location: (fd.get('start_location') || '').trim(),
      interests: fd.getAll('interests'),
    };
  }

  function validatePreferences(prefs) {
    const budget = Number(String(prefs.budget_inr).replace(/,/g, ''));
    const days = Number(prefs.days);
    if (!budget || budget < 1000) { return 'Enter a total trip budget of at least ₹1,000.'; }
    if (budget > 100000000) { return 'That budget looks too large. Please check it.'; }
    if (!days || days < 1 || days > 60) { return 'Number of days must be between 1 and 60.'; }
    if (!prefs.travel_type) { return 'Please choose a travel type.'; }
    if (!prefs.season) { return 'Please choose a season.'; }
    if (!prefs.interests.length) { return 'Select at least one interest.'; }
    return null;
  }

  /* -------------------------------------------- cross page trip context */
  const KEY = 'atp_context';
  const setContext = (ctx) => sessionStorage.setItem(KEY, JSON.stringify(ctx));
  const getContext = () => {
    try { return JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch (e) { return null; }
  };

  /* ----------------------------------------------------------- loading */
  function busy(button, isBusy, busyLabel) {
    if (!button) { return; }
    if (isBusy) {
      button.dataset.label = button.innerHTML;
      button.disabled = true;
      button.innerHTML = `<span class="spinner"></span> ${busyLabel || 'Working…'}`;
    } else {
      button.disabled = false;
      if (button.dataset.label) { button.innerHTML = button.dataset.label; }
    }
  }

  function loadingBlock(text) {
    return `<div class="loading-block"><span class="spinner spinner-dark"></span>
      <p>${esc(text)}</p></div>`;
  }

  function errorBlock(message, retryId) {
    return `<div class="empty-state"><h3>We hit a problem</h3><p>${esc(message)}</p>
      ${retryId ? `<button class="btn btn-outline" id="${retryId}">Try again</button>` : ''}</div>`;
  }

  /* --------------------------------------------------------- accordion */
  function bindAccordions(scope) {
    (scope || document).querySelectorAll('.acc-head').forEach((head) => {
      if (head.dataset.bound) { return; }
      head.dataset.bound = '1';
      head.addEventListener('click', () => head.parentElement.classList.toggle('open'));
    });
  }

  /* --------------------------------------------------------------- nav */
  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('navToggle');
    const nav = document.getElementById('mainNav');
    if (toggle && nav) {
      toggle.addEventListener('click', () => {
        const open = nav.classList.toggle('open');
        toggle.setAttribute('aria-expanded', String(open));
      });
    }
    bindAccordions(document);
  });

  return { toast, api, inr, esc, img, readPreferences, validatePreferences,
           setContext, getContext, busy, loadingBlock, errorBlock, bindAccordions, fallbackImage };
})();