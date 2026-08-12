/* AI Planner page: full itinerary from /api/ai-plan, saveable to My Trips. */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('prefForm');
  const results = document.getElementById('results');
  const button = document.getElementById('generateBtn');
  const hint = document.getElementById('perDayHint');
  let lastPlan = null;
  let lastCtx = null;
  const ctx0 = App.getContext();

  if (ctx0) {
    form.destination.value = ctx0.destination || '';
    form.country.value = ctx0.country || '';
    if (ctx0.budget_inr) { form.budget_inr.value = ctx0.budget_inr; }
    if (ctx0.days) { form.days.value = ctx0.days; }
    form.querySelectorAll('[name=travel_type]').forEach((el) => { el.checked = el.value === ctx0.travel_type; });
    form.querySelectorAll('[name=season]').forEach((el) => { el.checked = el.value === ctx0.season; });
    form.querySelectorAll('[name=interests]').forEach((el) => { el.checked = (ctx0.interests || []).includes(el.value); });
    form.start_location.value = ctx0.start_location || '';
  }

  function updateHint() {
    const b = Number(form.budget_inr.value); const d = Number(form.days.value);
    hint.textContent = (b > 0 && d > 0)
      ? `${App.inr(b)} total for ${d} day${d > 1 ? 's' : ''} · about ${App.inr(b / d)} per day.`
      : 'Budget covers the entire trip, not each day.';
  }
  form.budget_inr.addEventListener('input', updateHint);
  form.days.addEventListener('input', updateHint);
  form.destination.addEventListener('input', () => { form.country.value = ''; });
  updateHint();

  const listOf = (items) => `<ul class="list-clean">${(items || [])
    .map((i) => `<li>${App.esc(typeof i === 'string' ? i : (i && i.text) || '')}</li>`).join('')}</ul>`;

  function accordion(title, inner, open) {
    return `<section class="acc ${open ? 'open' : ''}">
      <button type="button" class="acc-head">${App.esc(title)}<span class="caret">▼</span></button>
      <div class="acc-body">${inner}</div></section>`;
  }

  function render(ctx, plan, weather) {
    const days = (plan.itinerary || []).map((d) => `
      <div class="day-row">
        <div class="day-chip">Day ${App.esc(d.day)}</div>
        <div>
          <h4>${App.esc(d.title || '')}</h4>
          ${d.morning ? `<p class="day-slot"><b>Morning:</b> ${App.esc(d.morning)}</p>` : ''}
          ${d.afternoon ? `<p class="day-slot"><b>Afternoon:</b> ${App.esc(d.afternoon)}</p>` : ''}
          ${d.evening ? `<p class="day-slot"><b>Evening:</b> ${App.esc(d.evening)}</p>` : ''}
          ${d.estimated_cost_inr ? `<span class="badge badge-blue">Approx ${App.inr(d.estimated_cost_inr)}</span>` : ''}
        </div>
      </div>`).join('');

    const cards = (items, body) => `<div class="grid grid-3">${(items || []).map((it) => `
      <div class="media-card">${App.img(it.image_url, it.name)}
        <div class="mc-body">${body(it)}</div></div>`).join('')}</div>`;

    const breakdown = (plan.budget_breakdown || []).map((b) => `
      <div class="budget-row"><span>${App.esc(b.category)}</span><strong>${App.inr(b.amount_inr)}</strong></div>`).join('');

    results.innerHTML = `
      <div class="hero-banner">
        ${App.img(plan.hero_image, ctx.destination)}
        <div class="hb-overlay">
          <h2>${App.esc(ctx.destination)}${ctx.country ? ', ' + App.esc(ctx.country) : ''}</h2>
          <p>${ctx.days} days · ${App.inr(ctx.budget_inr)} total · ${App.esc(ctx.travel_type)} · ${App.esc(ctx.season)}</p>
        </div>
      </div>

      <div class="summary-strip">
        <div class="stat"><span>Total budget</span><strong>${App.inr(ctx.budget_inr)}</strong></div>
        <div class="stat"><span>AI estimate</span><strong>${plan.total_estimated_inr ? App.inr(plan.total_estimated_inr) : '—'}</strong></div>
        <div class="stat"><span>Days planned</span><strong>${(plan.itinerary || []).length}</strong></div>
        ${weather ? `<div class="stat"><span>Weather now</span><strong>${weather.temp}°C</strong></div>` : ''}
      </div>

      <div class="card card-pad" style="margin-bottom:14px">
        <h3>Overview</h3><p style="margin:0">${App.esc(plan.overview || '')}</p>
      </div>

      ${accordion('Day-by-day itinerary', days || '<p>No days returned.</p>', true)}
      ${accordion('Hotels', cards(plan.hotels, (h) => `
        <h4>${App.esc(h.name)}</h4>
        <p>${App.esc(h.area || '')}</p>
        <p class="price">${h.price_per_night_inr ? App.inr(h.price_per_night_inr) + ' / night' : ''}</p>
        <p>${App.esc(h.why || '')}</p>`))}
      ${accordion('Restaurants', cards(plan.restaurants, (r) => `
        <h4>${App.esc(r.name)}</h4>
        <p>${App.esc(r.cuisine || '')}</p>
        <p>${App.esc(r.must_try || '')}</p>
        <p class="price">${r.avg_cost_inr ? App.inr(r.avg_cost_inr) + ' for two' : ''}</p>`))}
      ${accordion('Activities', cards(plan.activities, (a) => `
        <h4>${App.esc(a.name)}</h4>
        <p>${App.esc(a.detail || '')}</p>
        <p class="price">${a.cost_inr ? App.inr(a.cost_inr) : ''}</p>`))}
      ${accordion('Budget breakdown (₹)', breakdown +
        `<div class="budget-row" style="border-top:2px solid var(--border);margin-top:6px">
           <span><b>AI estimated total</b></span><strong>${plan.total_estimated_inr ? App.inr(plan.total_estimated_inr) : '—'}</strong></div>`)}
      ${accordion('Travel tips', listOf(plan.tips))}
      ${accordion('Packing list', listOf(plan.packing))}
      ${accordion('Safety', listOf(plan.safety))}

      <div class="card card-pad" style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between">
        <div><h3 style="margin:0">Happy with this plan?</h3><p style="margin:0">Save it and find it again under My Trips.</p></div>
        <div style="display:flex;gap:10px">
          <button class="btn btn-outline" id="regenBtn">Regenerate</button>
          <button class="btn btn-primary" id="saveBtn">Save Trip</button>
        </div>
      </div>`;

    App.bindAccordions(results);
    document.getElementById('regenBtn').addEventListener('click', run);
    document.getElementById('saveBtn').addEventListener('click', save);
  }

  async function save() {
    if (!lastPlan || !lastCtx) { return; }
    const btn = document.getElementById('saveBtn');
    App.busy(btn, true, 'Saving…');
    try {
      const stored = App.getContext() || {};
      await App.api('/api/save-trip', {
        method: 'POST',
        body: { ...lastCtx, image_url: lastPlan.hero_image || stored.image_url, plan: lastPlan },
      });
      App.toast('Trip saved to My Trips.', 'success');
    } catch (e) {
      App.toast(e.message, 'error');
    } finally {
      App.busy(btn, false);
    }
  }

  async function run() {
    const prefs = App.readPreferences(form);
    prefs.destination = form.destination.value.trim();
    prefs.country = form.country.value.trim();
    if (!prefs.destination) { App.toast('Please enter or choose a destination.', 'error'); return; }
    const error = App.validatePreferences(prefs);
    if (error) { App.toast(error, 'error'); return; }

    const stored = App.getContext() || {};
    const ctx = { ...prefs, budget_inr: Number(prefs.budget_inr), days: Number(prefs.days) };
    App.setContext({ ...stored, ...ctx });
    App.busy(button, true, 'Planning…');
    results.innerHTML = App.loadingBlock('Building a ' + ctx.days + '-day plan for ' + ctx.destination + '. This can take up to a minute…');
    try {
      const data = await App.api('/api/ai-plan', {
        method: 'POST',
        body: { ...ctx, latitude: stored.latitude, longitude: stored.longitude },
      });
      lastPlan = data.plan;
      lastCtx = ctx;
      render(ctx, data.plan, data.weather);
    } catch (e) {
      results.innerHTML = App.errorBlock(e.message, 'retryPlan');
      const retry = document.getElementById('retryPlan');
      if (retry) { retry.addEventListener('click', run); }
      App.toast(e.message, 'error');
    } finally {
      App.busy(button, false);
    }
  }

  form.addEventListener('submit', (event) => { event.preventDefault(); run(); });
});