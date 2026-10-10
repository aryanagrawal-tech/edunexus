/**
 * EduNexus AI - Authentication Controller (Vanilla JS)
 * Handles Login and Registration interactions, validation, password visibility toggles,
 * accessible feedback, and demo flows without inline JavaScript or backend dependencies.
 */

document.addEventListener('DOMContentLoaded', () => {
  initPasswordToggles();
  initLoginForm();
  initRegisterForm();
  initDemoQuickFill();
  initRoleCards();
});

/**
 * Eye Icons SVG Markup
 */
const ICONS = {
  eye: `<svg class="password-toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`,
  eyeOff: `<svg class="password-toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`
};

/**
 * Initialize accessible password show/hide toggle buttons
 */
function initPasswordToggles() {
  const toggleButtons = document.querySelectorAll('[data-toggle="password"]');
  toggleButtons.forEach(button => {
    button.addEventListener('click', () => {
      const targetId = button.getAttribute('data-target');
      const targetInput = document.getElementById(targetId);
      if (!targetInput) return;

      const isPassword = targetInput.getAttribute('type') === 'password';
      if (isPassword) {
        targetInput.setAttribute('type', 'text');
        button.innerHTML = ICONS.eyeOff;
        button.setAttribute('aria-label', 'Hide password');
        button.setAttribute('aria-pressed', 'true');
      } else {
        targetInput.setAttribute('type', 'password');
        button.innerHTML = ICONS.eye;
        button.setAttribute('aria-label', 'Show password');
        button.setAttribute('aria-pressed', 'false');
      }
      targetInput.focus();
    });
  });
}

/**
 * Email syntax format validator
 * @param {string} email
 * @returns {boolean}
 */
function isValidEmail(email) {
  const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return re.test(String(email).toLowerCase());
}

/**
 * Display field-level validation error
 */
function setFieldError(inputId, errorId, message) {
  const input = document.getElementById(inputId);
  const errorElem = document.getElementById(errorId);
  if (input) {
    input.classList.add('is-invalid');
    input.classList.remove('is-valid');
    input.setAttribute('aria-invalid', 'true');
  }
  if (errorElem) {
    errorElem.textContent = message;
    errorElem.classList.add('is-visible');
  }
}

/**
 * Clear field-level validation error
 */
function clearFieldError(inputId, errorId) {
  const input = document.getElementById(inputId);
  const errorElem = document.getElementById(errorId);
  if (input) {
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');
    input.removeAttribute('aria-invalid');
  }
  if (errorElem) {
    errorElem.textContent = '';
    errorElem.classList.remove('is-visible');
  }
}

/**
 * Initialize Login Form logic and validation
 */
function initLoginForm() {
  const loginForm = document.getElementById('loginForm');
  if (!loginForm) return;

  const emailInput = document.getElementById('loginEmail');
  const passwordInput = document.getElementById('loginPassword');
  const rememberCheckbox = document.getElementById('loginRemember');
  const submitBtn = document.getElementById('loginSubmitBtn');
  const formAlert = document.getElementById('loginFormAlert');

  // Check saved email from remember-me
  try {
    const savedEmail = localStorage.getItem('edunexus_remembered_email');
    if (savedEmail && emailInput && rememberCheckbox) {
      emailInput.value = savedEmail;
      rememberCheckbox.checked = true;
    }
  } catch (e) {
    // localStorage might be unavailable in restricted environments
  }

  // Show success message if redirected from registration
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const regSuccessMsg = sessionStorage.getItem('edunexus_registration_success');
    const regEmail = sessionStorage.getItem('edunexus_registered_email');
    if (urlParams.get('registered') === '1' || regSuccessMsg) {
      const displayMsg = regSuccessMsg || 'Registration successful. Please log in.';
      sessionStorage.removeItem('edunexus_registration_success');
      if (regEmail && emailInput && !emailInput.value) {
        emailInput.value = regEmail;
      }
      sessionStorage.removeItem('edunexus_registered_email');
      if (formAlert) {
        formAlert.className = 'alert alert-success is-visible';
        formAlert.innerHTML = `
          <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
          </svg>
          <div class="alert-content">
            <strong>Registration Successful</strong>
            <div>${displayMsg}</div>
          </div>
        `;
      }
      if (window.showToast) {
        window.showToast('Registration successful. Please log in.', 'success');
      }
    }
  } catch (e) {}

  // Real-time email validation on blur/input
  emailInput.addEventListener('blur', () => {
    const val = emailInput.value.trim();
    if (!val) {
      setFieldError('loginEmail', 'loginEmailError', 'Please enter your institutional email address.');
    } else if (!isValidEmail(val)) {
      setFieldError('loginEmail', 'loginEmailError', 'Please enter a valid email format (e.g., user@domain.edu).');
    } else {
      clearFieldError('loginEmail', 'loginEmailError');
    }
  });

  passwordInput.addEventListener('input', () => {
    if (passwordInput.value.trim()) {
      clearFieldError('loginPassword', 'loginPasswordError');
    }
  });

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    let hasError = false;
    const emailVal = emailInput.value.trim();
    const passwordVal = passwordInput.value;

    if (!emailVal) {
      setFieldError('loginEmail', 'loginEmailError', 'Please enter your institutional email address.');
      hasError = true;
    } else if (!isValidEmail(emailVal)) {
      setFieldError('loginEmail', 'loginEmailError', 'Please enter a valid email format.');
      hasError = true;
    } else {
      clearFieldError('loginEmail', 'loginEmailError');
    }

    if (!passwordVal) {
      setFieldError('loginPassword', 'loginPasswordError', 'Please enter your account password.');
      hasError = true;
    } else {
      clearFieldError('loginPassword', 'loginPasswordError');
    }

    if (hasError) return;

    // Save or clear remember-me preference
    try {
      if (rememberCheckbox && rememberCheckbox.checked) {
        localStorage.setItem('edunexus_remembered_email', emailVal);
      } else {
        localStorage.removeItem('edunexus_remembered_email');
      }
    } catch (e) {}

    // Show loading state
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.setAttribute('aria-disabled', 'true');
    submitBtn.innerHTML = `<span class="spinner" aria-hidden="true"></span> Authenticating...`;

    if (formAlert) {
      formAlert.classList.remove('is-visible');
    }

    try {
      const response = await window.EduNexusAPI.login({
        email: emailVal,
        password: passwordVal,
        rememberMe: rememberCheckbox ? rememberCheckbox.checked : false
      });

      // Authentication success feedback
      const userObj = response.data.user || {};
      const role = (userObj.role || 'student').toLowerCase();
      const displayName = userObj.name || userObj.fullName || 'User';
      let targetDashboard = '/student-dashboard';
      if (role === 'faculty') targetDashboard = '/faculty-dashboard';
      else if (role === 'admin') targetDashboard = '/admin-dashboard';

      if (formAlert) {
        formAlert.className = 'alert alert-success is-visible';
        formAlert.innerHTML = `
          <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
          </svg>
          <div class="alert-content">
            <strong>Login Successful</strong>
            <div>${response.message}</div>
            <div class="alert-subtext">
              Redirecting to <strong>${role.toUpperCase()} Dashboard</strong>...
              <a href="${targetDashboard}" class="auth-switch-link">Click here to enter</a>
            </div>
          </div>
        `;
      }

      window.showToast(`Welcome, ${displayName}! Entering dashboard...`, 'success');

      setTimeout(() => {
        window.location.href = targetDashboard;
      }, 1200);

    } catch (err) {
      if (formAlert) {
        formAlert.className = 'alert alert-danger is-visible';
        formAlert.innerHTML = `
          <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" />
          </svg>
          <div class="alert-content">
            <strong>Authentication Failed</strong>
            <div>${err.message || 'Unable to sign in. Please verify your credentials.'}</div>
          </div>
        `;
      }
      window.showToast(err.message || 'Authentication error', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.removeAttribute('aria-disabled');
      submitBtn.innerHTML = originalBtnText;
    }
  });
}

/**
 * Initialize Registration Form logic and validation
 */
function initRegisterForm() {
  const registerForm = document.getElementById('registerForm');
  if (!registerForm) return;

  const nameInput = document.getElementById('regName');
  const emailInput = document.getElementById('regEmail');
  const passwordInput = document.getElementById('regPassword');
  const confirmPasswordInput = document.getElementById('regConfirmPassword');
  const submitBtn = document.getElementById('regSubmitBtn');
  const formAlert = document.getElementById('regFormAlert');
  const termsCheckbox = document.getElementById('regTerms');

  // Name validation
  nameInput.addEventListener('blur', () => {
    const val = nameInput.value.trim();
    if (!val || val.length < 2) {
      setFieldError('regName', 'regNameError', 'Please enter your full legal or institutional name (minimum 2 characters).');
    } else {
      clearFieldError('regName', 'regNameError');
    }
  });

  // Email validation
  emailInput.addEventListener('blur', () => {
    const val = emailInput.value.trim();
    if (!val) {
      setFieldError('regEmail', 'regEmailError', 'Please enter your institutional email address.');
    } else if (!isValidEmail(val)) {
      setFieldError('regEmail', 'regEmailError', 'Please provide a valid institutional email format.');
    } else {
      clearFieldError('regEmail', 'regEmailError');
    }
  });

  // Password length & strength check
  passwordInput.addEventListener('input', () => {
    const val = passwordInput.value;
    if (val.length < 8) {
      setFieldError('regPassword', 'regPasswordError', 'Password must be at least 8 characters long.');
    } else {
      clearFieldError('regPassword', 'regPasswordError');
    }
    // Also re-evaluate confirm password if populated
    if (confirmPasswordInput.value) {
      if (val !== confirmPasswordInput.value) {
        setFieldError('regConfirmPassword', 'regConfirmError', 'Passwords do not match.');
      } else {
        clearFieldError('regConfirmPassword', 'regConfirmError');
      }
    }
  });

  // Confirm password real-time matching
  confirmPasswordInput.addEventListener('input', () => {
    if (confirmPasswordInput.value !== passwordInput.value) {
      setFieldError('regConfirmPassword', 'regConfirmError', 'Passwords do not match.');
    } else {
      clearFieldError('regConfirmPassword', 'regConfirmError');
    }
  });

  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    let hasError = false;
    const nameVal = nameInput.value.trim();
    const emailVal = emailInput.value.trim();
    const passVal = passwordInput.value;
    const confirmVal = confirmPasswordInput.value;

    // Check role selection (strictly student or faculty)
    const selectedRoleElem = registerForm.querySelector('input[name="role"]:checked');
    const roleVal = selectedRoleElem ? selectedRoleElem.value : null;

    if (!roleVal || (roleVal !== 'student' && roleVal !== 'faculty')) {
      const roleErrorElem = document.getElementById('regRoleError');
      if (roleErrorElem) {
        roleErrorElem.textContent = 'Please select your role: Student or Faculty.';
        roleErrorElem.classList.add('is-visible');
      }
      hasError = true;
    } else {
      const roleErrorElem = document.getElementById('regRoleError');
      if (roleErrorElem) {
        roleErrorElem.textContent = '';
        roleErrorElem.classList.remove('is-visible');
      }
    }

    if (!nameVal || nameVal.length < 2) {
      setFieldError('regName', 'regNameError', 'Please enter your full legal or institutional name.');
      hasError = true;
    }

    if (!emailVal || !isValidEmail(emailVal)) {
      setFieldError('regEmail', 'regEmailError', 'Please provide a valid institutional email format.');
      hasError = true;
    }

    if (passVal.length < 8) {
      setFieldError('regPassword', 'regPasswordError', 'Password must be at least 8 characters long.');
      hasError = true;
    }

    if (passVal !== confirmVal) {
      setFieldError('regConfirmPassword', 'regConfirmError', 'Passwords do not match.');
      hasError = true;
    }

    if (termsCheckbox && !termsCheckbox.checked) {
      setFieldError('regTerms', 'regTermsError', 'You must agree to the academic honor code to register.');
      hasError = true;
    } else {
      clearFieldError('regTerms', 'regTermsError');
    }

    if (hasError) return;

    // Show loading state
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.setAttribute('aria-disabled', 'true');
    submitBtn.innerHTML = `<span class="spinner" aria-hidden="true"></span> Creating Account...`;

    if (formAlert) {
      formAlert.classList.remove('is-visible');
    }

    try {
      const response = await window.EduNexusAPI.register({
        fullName: nameVal,
        email: emailVal,
        password: passVal,
        role: roleVal
      });

      const createdUser = response && response.data && response.data.user;
      if (!response || !response.success || !createdUser || !createdUser.id) {
        throw new Error((response && response.message) || 'Account could not be saved to the database.');
      }

      const successMessage = 'Registration successful. Please log in.';
      try {
        sessionStorage.setItem('edunexus_registration_success', successMessage);
        sessionStorage.setItem('edunexus_registered_email', emailVal);
      } catch (e) {}

      if (formAlert) {
        formAlert.className = 'alert alert-success is-visible';
        formAlert.innerHTML = `
          <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
          </svg>
          <div class="alert-content">
            <strong>Registration successful. Please log in.</strong>
            <div>${response.message}</div>
            <div class="alert-subtext">
              Redirecting to <a href="/login?registered=1" class="auth-switch-link">Login page</a>...
            </div>
          </div>
        `;
      }

      window.showToast(successMessage, 'success');

      // Clear sensitive inputs
      passwordInput.value = '';
      confirmPasswordInput.value = '';

      // Redirect to Login page after confirmed database insert
      setTimeout(() => {
        window.location.assign('/login?registered=1');
      }, 900);

    } catch (err) {
      if (formAlert) {
        formAlert.className = 'alert alert-danger is-visible';
        formAlert.innerHTML = `
          <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" />
          </svg>
          <div class="alert-content">
            <strong>Registration Failed</strong>
            <div>${err.message || 'Unable to complete registration.'}</div>
          </div>
        `;
      }
      window.showToast(err.message || 'Registration error', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.removeAttribute('aria-disabled');
      submitBtn.innerHTML = originalBtnText;
    }
  });
}

/**
 * Initialize interactive role cards in registration form
 */
function initRoleCards() {
  const roleCards = document.querySelectorAll('[data-role-card]');
  roleCards.forEach(card => {
    card.addEventListener('click', () => {
      const radio = card.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        // Update styling
        roleCards.forEach(c => c.classList.remove('is-selected'));
        card.classList.add('is-selected');

        const roleErrorElem = document.getElementById('regRoleError');
        if (roleErrorElem) {
          roleErrorElem.textContent = '';
          roleErrorElem.classList.remove('is-visible');
        }
      }
    });
  });
}

/**
 * Initialize Demo Quick-Fill credentials buttons on login page
 */
function initDemoQuickFill() {
  const quickfillButtons = document.querySelectorAll('[data-demo-role]');
  const emailInput = document.getElementById('loginEmail');
  const passwordInput = document.getElementById('loginPassword');

  if (!quickfillButtons.length || !emailInput || !passwordInput) return;

  quickfillButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const role = btn.getAttribute('data-demo-role');
      const account = window.API_CONFIG && window.API_CONFIG.demoAccounts[role];
      if (account) {
        emailInput.value = account.email;
        passwordInput.value = account.password;
        clearFieldError('loginEmail', 'loginEmailError');
        clearFieldError('loginPassword', 'loginPasswordError');
        window.showToast(`Filled credentials for ${account.name} (${role.toUpperCase()})`, 'info');
      }
    });
  });
}
