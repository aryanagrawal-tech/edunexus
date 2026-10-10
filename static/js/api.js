/**
 * EduNexus AI - Frontend API Service & Configuration
 * Provides configurable endpoints and graceful client-side demo fallbacks
 * until Flask & Supabase backend endpoints are implemented.
 */

const API_CONFIG = {
  // Configurable base URL for Flask backend
  baseUrl: (typeof window !== 'undefined' && window.location.origin && window.location.origin.startsWith('http'))
    ? `${window.location.origin}/api`
    : 'http://localhost:5000/api',
  // Active demo mode toggle (set to false to connect directly to live backend)
  isDemoMode: true,
  // Simulated request latency in milliseconds
  simulatedDelayMs: 600,
  // Demo accounts for rapid evaluation
  demoAccounts: {
    student: {
      email: 'student.demo@edunexus.edu',
      password: 'DemoStudent@2026',
      name: 'Aryan Agrawal',
      role: 'student',
      course: 'B.Sc. Information Technology (Honors)',
      semester: 'Semester VI'
    },
    faculty: {
      email: 'faculty.demo@edunexus.edu',
      password: 'DemoFaculty@2026',
      name: 'Dr. Sarah Mitchell',
      role: 'faculty',
      department: 'Department of Computer Science',
      courses: ['Data Structures & Algorithms', 'AI Systems Architecture']
    },
    admin: {
      email: 'admin.demo@edunexus.edu',
      password: 'DemoAdmin@2026',
      name: 'System Administrator',
      role: 'admin',
      scope: 'Global Institution'
    }
  }
};

/**
 * Toast notification dispatcher
 * @param {string} message - Message text
 * @param {'info' | 'success' | 'error'} type - Notification type
 * @param {number} duration - Auto dismiss time in ms
 */
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'auth-toast-container';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'true');
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'status');

  const content = document.createElement('div');
  content.textContent = message;
  toast.appendChild(content);

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-fadeout');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 250);
  }, duration);
}

/**
 * Unified API Client
 */
const EduNexusAPI = {
  /**
   * Perform authentication login request
   * @param {Object} credentials - { email, password, rememberMe }
   * @returns {Promise<Object>}
   */
  async login(credentials) {
    if (API_CONFIG.isDemoMode) {
      return new Promise((resolve, reject) => {
        setTimeout(() => {
          const { email, password } = credentials;
          const { demoAccounts } = API_CONFIG;

          // Check against known demo accounts
          let matched = null;
          if (email === demoAccounts.student.email && password === demoAccounts.student.password) {
            matched = demoAccounts.student;
          } else if (email === demoAccounts.faculty.email && password === demoAccounts.faculty.password) {
            matched = demoAccounts.faculty;
          } else if (email === demoAccounts.admin.email && password === demoAccounts.admin.password) {
            matched = demoAccounts.admin;
          } else if (email && password) {
            // Allow general evaluation login based on email heuristic
            matched = {
              email,
              name: email.split('@')[0].replace('.', ' '),
              role: email.includes('faculty') ? 'faculty' : (email.includes('admin') ? 'admin' : 'student')
            };
          }

          if (matched) {
            const session = {
              user: matched,
              token: `mock_jwt_token_${Date.now()}`,
              isDemo: true,
              expiresAt: Date.now() + 86400000
            };
            try {
              sessionStorage.setItem('edunexus_session', JSON.stringify(session));
            } catch (e) {
              // Ignore storage errors if disabled
            }
            resolve({
              success: true,
              message: `Signed in successfully as ${matched.name} (${matched.role.toUpperCase()}) [Simulated]`,
              data: session
            });
          } else {
            reject({
              success: false,
              message: 'Invalid credentials. Please enter a valid email and password or use demo quick-fill.'
            });
          }
        }, API_CONFIG.simulatedDelayMs);
      });
    }

    // Future live backend call
    const response = await fetch(`${API_CONFIG.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    });
    return response.json();
  },

  /**
   * Perform user registration request
   * @param {Object} userData - { fullName, email, password, role }
   * @returns {Promise<Object>}
   */
  async register(userData) {
    if (API_CONFIG.isDemoMode) {
      return new Promise((resolve, reject) => {
        setTimeout(() => {
          const { fullName, email, role } = userData;
          
          // Guard: Admin registration is prohibited through public frontend
          if (role === 'admin') {
            reject({
              success: false,
              message: 'Admin registration is restricted. Platform administrator accounts must be provisioned securely.'
            });
            return;
          }

          if (!fullName || !email || !role) {
            reject({
              success: false,
              message: 'Please complete all required fields.'
            });
            return;
          }

          const newUser = {
            fullName,
            email,
            role,
            registeredAt: new Date().toISOString(),
            isDemo: true
          };

          resolve({
            success: true,
            message: `Account created for ${fullName} as ${role.toUpperCase()} [Simulated Demo Mode]`,
            data: newUser
          });
        }, API_CONFIG.simulatedDelayMs);
      });
    }

    // Future live backend call
    const response = await fetch(`${API_CONFIG.baseUrl}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });
    return response.json();
  },

  /**
   * Retrieve current active session
   */
  getCurrentSession() {
    try {
      const stored = sessionStorage.getItem('edunexus_session');
      return stored ? JSON.parse(stored) : null;
    } catch (e) {
      return null;
    }
  },

  /**
   * Clear session on logout
   */
  logout() {
    try {
      sessionStorage.removeItem('edunexus_session');
    } catch (e) {
      // Ignore
    }
  },

  /**
   * Health check probe
   */
  async getHealth() {
    try {
      const url = API_CONFIG.baseUrl.replace(/\/api$/, '') + '/health';
      const res = await fetch(url);
      return await res.json();
    } catch (err) {
      return { status: 'error', error: err.message };
    }
  },

  /**
   * Fetch all enrolled students
   */
  async getStudents() {
    if (API_CONFIG.isDemoMode) {
      return {
        success: true,
        count: 4,
        data: [
          { id: 1, name: 'Aanya Patel', email: 'aanya.demo@example.com', course: 'Data Structures' },
          { id: 2, name: 'Rohan Shah', email: 'rohan.demo@example.com', course: 'Data Structures' },
          { id: 3, name: 'Meera Joshi', email: 'meera.demo@example.com', course: 'Data Structures' },
          { id: 4, name: 'Arjun Desai', email: 'arjun.demo@example.com', course: 'Data Structures' }
        ]
      };
    }
    const res = await fetch(`${API_CONFIG.baseUrl}/students`);
    return await res.json();
  },

  /**
   * Fetch course activities
   */
  async getActivities() {
    if (API_CONFIG.isDemoMode) {
      return {
        success: true,
        count: 6,
        data: [
          { id: 1, title: 'Arrays & Dynamic Sizing Quiz', topic: 'Arrays', activity_type: 'Quiz', max_score: 100 },
          { id: 2, title: 'Linked List Reversal Lab', topic: 'Linked Lists', activity_type: 'Lab', max_score: 100 },
          { id: 3, title: 'Stack Implementation Assignment', topic: 'Stacks', activity_type: 'Assignment', max_score: 100 },
          { id: 4, title: 'Queue & Circular Buffer Quiz', topic: 'Queues', activity_type: 'Quiz', max_score: 100 },
          { id: 5, title: 'Recursion Depth & Backtracking Lab', topic: 'Recursion', activity_type: 'Lab', max_score: 100 },
          { id: 6, title: 'Comprehensive Data Structures Midterm', topic: 'Arrays', activity_type: 'Exam', max_score: 100 }
        ]
      };
    }
    const res = await fetch(`${API_CONFIG.baseUrl}/activities`);
    return await res.json();
  },

  /**
   * Create course activity
   */
  async createActivity(activityData) {
    if (API_CONFIG.isDemoMode) {
      return {
        success: true,
        message: 'Activity created (simulated demo mode).',
        data: { id: Date.now(), ...activityData }
      };
    }
    const res = await fetch(`${API_CONFIG.baseUrl}/activities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(activityData)
    });
    return await res.json();
  },

  /**
   * Fetch full student academic dashboard
   */
  async getStudentDashboard(studentId = 1) {
    if (API_CONFIG.isDemoMode) {
      const mock = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.student;
      return { success: true, data: mock };
    }
    const res = await fetch(`${API_CONFIG.baseUrl}/student/${studentId}/dashboard`);
    return await res.json();
  },

  /**
   * Fetch faculty cohort overview
   */
  async getFacultyOverview() {
    if (API_CONFIG.isDemoMode) {
      const mock = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.faculty;
      return { success: true, data: mock };
    }
    const res = await fetch(`${API_CONFIG.baseUrl}/faculty/overview`);
    return await res.json();
  },

  /**
   * Submit activity score
   */
  async submitActivity(submissionData) {
    if (API_CONFIG.isDemoMode) {
      return {
        success: true,
        message: 'Submission recorded (simulated demo mode).',
        data: { id: Date.now(), ...submissionData }
      };
    }
    const res = await fetch(`${API_CONFIG.baseUrl}/submissions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submissionData)
    });
    return await res.json();
  },

  /**
   * Run on-demand academic analytics
   */
  async analyzePerformance(payload) {
    if (API_CONFIG.isDemoMode) {
      return {
        success: true,
        data: {
          overall_score: 75.0,
          weak_topics: [],
          recommendations: []
        }
      };
    }
    const res = await fetch(`${API_CONFIG.baseUrl}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  }
};

window.EduNexusAPI = EduNexusAPI;
window.API_CONFIG = API_CONFIG;
window.showToast = showToast;
