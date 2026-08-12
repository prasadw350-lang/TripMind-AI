/* ML prediction page: calls /api/predict and renders real model output. */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('prefForm');
  const results = document.getElementById('results');
  const button = document.getElementById('predictBtn');
  const hint = document.getElementById('perDayHint');
  const budget = document.getElementById('budget_inr');
  const days = document.getElementById('days');

  /* Restore preferences chosen elsewhere in the app. */
  const saved = App.getContext();
  if (saved) {
    if (saved.budget_inr) { budget.value = saved.budget_inr; }
    if (saved.days) { days.value = saved.days; }
    form.querySelectorAll('[name=travel_type]').forEach((el) => { el.checked = el.value === saved.travel_type; });
    form.querySelectorAll('[name=season]').forEach((el) => { el.checked = el.value === saved.season; });
    form.querySelectorAll('[name=interests]').forEach((el) => { el.checked = (saved.interests || []).includes(el.value); });
    if (saved.start_location) { form.start_location.value = saved.start_location; }
  }

  function updateHint() {
    const b = Number(budget.value);
    const d = Number(days.value);
    hint.textContent = (b > 0 && d > 0)
      ? `${App.inr(b)} total · about ${App.inr(b / d)} per day for ${d} day${d > 1 ? 's' : ''}.`
      : 'Enter budget and days to see the per-day split.';
  }
  budget.addEventListener('input', updateHint);
  days.addEventListener('input', updateHint);
  updateHint();

  function renderCard(item, index, ctx) {
    return `
      <article class="dest-card">
        <div class="dest-media">
          ${App.img(item.image_url, item.city + ', ' + item.country)}
          <span class="dest-rank">${index + 1}</span>
          <span class="dest-match">Match ${item.match}%</span>
        </div>
        <div class="dest-body">
          <div>
            <div class="dest-title">${App.esc(item.city)}, ${App.esc(item.country)}</div>
            <div class="dest-sub">${App.esc(item.region)}</div>
          </div>
          <div class="match-bar"><i style="width:${Math.max(4, Math.min(100, item.match))}%"></i></div>
          <p class="dest-desc">${App.esc(item.description)}</p>
          <div class="dest-meta">
            <div><span>Budget level</span><strong>${App.esc(item.budget_level)}</strong></div>
            <div><span>Ideal duration</span><strong>${App.esc(item.ideal_duration)}</strong></div>
            <div><span>Best month</span><strong>${App.esc(item.best_month || '—')}${item.best_month_temp != null ? ' · ' + item.best_month_temp + '°C' : ''}</strong></div>
            <div><span>Estimated total</span><strong class="dest-cost">${App.inr(item.estimated_total_inr)}</strong></div>
          </div>
          <div class="tag-row">
            ${item.within_budget
              ? '<span class="badge badge-ok">Fits your budget</span>'
              : '<span class="badge badge-accent">Above your budget</span>'}
            ${(item.tags || []).slice(0, 3).map((t) => `<span class="badge">${App.esc(t)}</span>`).join('')}
          </div>
          <div class="dest-actions">
            <button class="btn btn-primary btn-sm plan-btn" data-index="${index}">Generate AI Trip</button>
            <button class="btn btn-outline btn-sm insight-btn" data-index="${index}">AI Details</button>
          </div>
        </div>
      </article>`;
  }

  function render(data, ctx) {
    results.innerHTML = `
      <div class="summary-strip">
        <div class="stat"><span>Total budget</span><strong>${App.inr(ctx.budget_inr)}</strong></div>
        <div class="stat"><span>Per day</span><strong>${App.inr(data.per_day_inr)}</strong></div>
        <div class="stat"><span>Budget level</span><strong>${App.esc(data.budget_level)}</strong></div>
        <div class="stat"><span>Duration class</span><strong>${App.esc(data.duration_label)}</strong></div>
        <div class="stat"><span>Matches</span><strong>${data.results.length}</strong></div>
      </div>
      <div class="dest-grid">${data.results.map((item, i) => renderCard(item, i, ctx)).join('')}</div>`;

    results.querySelectorAll('.plan-btn').forEach((btn) => {
      btn.addEventListener('click', () => go(data.results[Number(btn.dataset.index)], ctx, '/planner'));
    });
    results.querySelectorAll('.insight-btn').forEach((btn) => {
      btn.addEventListener('click', () => go(data.results[Number(btn.dataset.index)], ctx, '/ai-recommendation'));
    });
  }

  function go(item, ctx, url) {
    App.setContext({
      ...ctx,
      destination: item.city,
      country: item.country,
      latitude: item.latitude,
      longitude: item.longitude,
      image_url: item.image_url,
      match: item.match,
      estimated_total_inr: item.estimated_total_inr,
    });
    window.location.href = url;
  }

  async function run() {
    const prefs = App.readPreferences(form);
    const error = App.validatePreferences(prefs);
    if (error) { App.toast(error, 'error'); return; }

    const ctx = { ...prefs, budget_inr: Number(String(prefs.budget_inr).replace(/,/g, '')), days: Number(prefs.days) };
    App.setContext(ctx);
    App.busy(button, true, 'Predicting…');
    results.innerHTML = App.loadingBlock('Running the recommendation model on your preferences…');
    try {
      const data = await App.api('/api/predict', { method: 'POST', body: ctx });
      render(data, ctx);
    } catch (e) {
      results.innerHTML = App.errorBlock(e.message, 'retryPredict');
      const retry = document.getElementById('retryPredict');
      if (retry) { retry.addEventListener('click', run); }
      App.toast(e.message, 'error');
    } finally {
      App.busy(button, false);
    }
  }

  form.addEventListener('submit', (event) => { event.preventDefault(); run(); });
});
