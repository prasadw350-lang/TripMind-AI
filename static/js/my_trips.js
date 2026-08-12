/* My Trips: lists saved trips from SQLite via /api/my-trips. */
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('tripsRoot');

  const date = (iso) => {
    const d = new Date(iso + (iso && iso.endsWith('Z') ? '' : 'Z'));
    return isNaN(d) ? '' : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  function detail(trip) {
    const plan = trip.plan || {};
    const days = (plan.itinerary || []).map((d) => `
      <div class="day-row">
        <div class="day-chip">Day ${App.esc(d.day)}</div>
        <div><h4>${App.esc(d.title || '')}</h4>
          ${d.morning ? `<p class="day-slot"><b>Morning:</b> ${App.esc(d.morning)}</p>` : ''}
          ${d.afternoon ? `<p class="day-slot"><b>Afternoon:</b> ${App.esc(d.afternoon)}</p>` : ''}
          ${d.evening ? `<p class="day-slot"><b>Evening:</b> ${App.esc(d.evening)}</p>` : ''}
        </div>
      </div>`).join('');
    return `<section class="acc"><button type="button" class="acc-head">Saved itinerary<span class="caret">▼</span></button>
      <div class="acc-body">
        ${plan.overview ? `<p>${App.esc(plan.overview)}</p>` : ''}
        ${days || '<p>No day plan stored.</p>'}
      </div></section>`;
  }

  function render(trips) {
    if (!trips.length) {
      root.innerHTML = `<div class="empty-state card card-pad">
        <h3>No saved trips yet</h3>
        <p>Generate an itinerary in the AI planner and hit Save Trip — it will appear here.</p>
        <a class="btn btn-primary" href="/planner">Open AI Planner</a></div>`;
      return;
    }
    root.innerHTML = trips.map((t) => `
      <div class="card" style="margin-bottom:16px">
        <div class="trip-card">
          ${App.img(t.image_url, t.destination)}
          <div>
            <h3 style="margin-bottom:2px">${App.esc(t.destination)}${t.country ? ', ' + App.esc(t.country) : ''}</h3>
            <p style="margin:0;color:var(--ink-500);font-size:13.5px">Saved ${App.esc(date(t.created_at))}</p>
            <div class="trip-meta">
              <span class="badge badge-blue">${App.inr(t.budget_inr)} total</span>
              <span class="badge">${t.days} days</span>
              ${t.travel_type ? `<span class="badge">${App.esc(t.travel_type)}</span>` : ''}
              ${t.season ? `<span class="badge">${App.esc(t.season)}</span>` : ''}
              ${(t.interests || []).map((i) => `<span class="badge badge-accent">${App.esc(i)}</span>`).join('')}
            </div>
          </div>
          <button class="btn btn-ghost del-btn" data-id="${t.id}">Delete</button>
        </div>
        <div style="padding: 0 16px 16px">${detail(t)}</div>
      </div>`).join('');

    App.bindAccordions(root);
    root.querySelectorAll('.del-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        App.busy(btn, true, 'Deleting…');
        try {
          await App.api('/api/my-trips/' + btn.dataset.id, { method: 'DELETE' });
          App.toast('Trip deleted.', 'success');
          load();
        } catch (e) {
          App.toast(e.message, 'error');
          App.busy(btn, false);
        }
      });
    });
  }

  async function load() {
    root.innerHTML = App.loadingBlock('Loading your saved trips…');
    try {
      const data = await App.api('/api/my-trips');
      render(data.trips || []);
    } catch (e) {
      root.innerHTML = App.errorBlock(e.message, 'retryTrips');
      const retry = document.getElementById('retryTrips');
      if (retry) { retry.addEventListener('click', load); }
    }
  }

  load();
});
