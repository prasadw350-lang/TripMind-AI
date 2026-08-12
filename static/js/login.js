/* Login / register page interactions */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('authForm');
  const action = document.getElementById('authAction');
  const email = document.getElementById('email');
  const password = document.getElementById('password');
  const subtitle = document.getElementById('authSubtitle');

  document.getElementById('registerBtn').addEventListener('click', () => {
    action.value = 'register';
    subtitle.textContent = 'Creating your account';
  });
  document.getElementById('loginBtn').addEventListener('click', () => {
    action.value = 'login';
  });

  document.getElementById('forgotBtn').addEventListener('click', () => {
    App.toast('Password recovery is not enabled in this build. Register a new account or contact support from the Contact page.', 'info', 6000);
  });

  form.addEventListener('submit', (event) => {
    const emailOk = /^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$/.test(email.value.trim());
    if (!emailOk) {
      event.preventDefault();
      App.toast('Please enter a valid email address.', 'error');
      email.focus();
      return;
    }
    if (password.value.length < 6) {
      event.preventDefault();
      App.toast('Password must be at least 6 characters.', 'error');
      password.focus();
    }
  });
});