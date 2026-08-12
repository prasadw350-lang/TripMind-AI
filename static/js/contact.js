/* Contact form: posts to /api/contact, stored in SQLite. */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('contactForm');
  const button = document.getElementById('contactBtn');
  const status = document.getElementById('contactStatus');
  const message = document.getElementById('message');
  const count = document.getElementById('charCount');

  message.addEventListener('input', () => { count.textContent = message.value.length; });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    status.innerHTML = '';
    const body = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      message: message.value.trim(),
    };
    if (body.name.length < 2) { App.toast('Please enter your name.', 'error'); return; }
    if (!/^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$/.test(body.email)) { App.toast('Please enter a valid email address.', 'error'); return; }
    if (body.message.length < 10) { App.toast('Message must be at least 10 characters.', 'error'); return; }

    App.busy(button, true, 'Sending…');
    try {
      const data = await App.api('/api/contact', { method: 'POST', body });
      status.innerHTML = `<div class="alert alert-success">${App.esc(data.message)}</div>`;
      form.reset();
      count.textContent = '0';
      App.toast('Message sent.', 'success');
    } catch (e) {
      status.innerHTML = `<div class="alert alert-error">${App.esc(e.message)}</div>`;
    } finally {
      App.busy(button, false);
    }
  });
});
