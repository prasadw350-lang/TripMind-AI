/* AI Recommendation page: destination briefing from /api/insight. */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('prefForm');
  const results = document.getElementById('results');
  const button = document.getElementById('generateBtn');
  const hint = document.getElementById('perDayHint');
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

  const list = (items, cls) => `<ul class="${cls || 'list-clean'}">${(items || [])
    .map((i) => `<li>${App.esc(typeof i === 'string' ? i : JSON.stringify(i))}</li>`).join('')}</ul>`;

  function render(destination, country, data) {
    const highlights = (data.highlights || []).filter((h) => h && typeof h === 'object');
    results.innerHTML = `
      <div class="hero-banner">
        ${App.img(data.hero_image, destination)}
        <div class="hb-overlay">
          <h2>${App.esc(destination)}${country ? ', ' + App.esc(country) : ''}</h2>
          <p>${App.esc(data.best_time || '')}</p>
        </div>
      </div>

      <div class="card card-pad" style="margin-bottom:18px">
        <h3>Overview</h3>
        <p>${App.esc(data.summary || '')}</p>
        <h4>Why it fits you</h4>
        ${list(data.why_it_fits)}
      </div>

      <div class="grid grid-3" style="margin-bottom:18px">
        ${highlights.map((h) => `
          <div class="media-card">
            ${App.img(h.image_url, h.title)}
            <div class="mc-body"><h4>${App.esc(h.title)}</h4><p>${App.esc(h.detail)}</p></div>
          </div>`).join('')}
      </div>

      <div class="grid grid-2" style="margin-bottom:18px">
        <div class="card card-pad"><h3>Getting there</h3><p>${App.esc(data.getting_there || '')}</p></div>
        <div class="card card-pad"><h3>Budget fit</h3><p>${App.esc(data.budget_fit || '')}</p></div>
      </div>

      <div class="grid grid-2" style="margin-bottom:18px">
        <div class="card card-pad"><h3>Local food</h3>${list(data.local_food)}</div>
        <div class="card card-pad"><h3>Good to know</h3>${list(data.culture_notes)}</div>
      </div>

      <div class="card card-pad" style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between">
        <div><h3 style="margin:0">Ready to plan the days?</h3>
          <p style="margin:0">Take these inputs straight into the AI itinerary builder.</p></div>
        <button class="btn btn-primary" id="toPlanner">Generate AI Trip</button>
      </div>`;

    document.getElementById('toPlanner').addEventListener('click', () => { window.location.href = '/planner'; });
  }

  async function run() {
    const prefs = App.readPreferences(form);
    prefs.destination = form.destination.value.trim();
    prefs.country = form.country.value.trim();
    if (!prefs.destination) { App.toast('Please enter or choose a destination.', 'error'); return; }
    const error = App.validatePreferences(prefs);
    if (error) { App.toast(error, 'error'); return; }

    const ctx = { ...prefs, budget_inr: Number(prefs.budget_inr), days: Number(prefs.days) };
    App.setContext({ ...(App.getContext() || {}), ...ctx });
    App.busy(button, true, 'Generating…');
    results.innerHTML = App.loadingBlock('Asking the AI for a briefing on ' + ctx.destination + '…');
    try {
      const data = await App.api('/api/insight', { method: 'POST', body: ctx });
      render(data.destination, data.country, data.insight);
    } catch (e) {
      results.innerHTML = App.errorBlock(e.message, 'retryInsight');
      const retry = document.getElementById('retryInsight');
      if (retry) { retry.addEventListener('click', run); }
      App.toast(e.message, 'error');
    } finally {
      App.busy(button, false);
    }
  }

  form.addEventListener('submit', (event) => { event.preventDefault(); run(); });
  if (ctx0 && ctx0.destination) { run(); }
});
