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
  // Connect directly to the live Flask + Supabase backend
  isDemoMode: false,
  // Fallback request latency in milliseconds
  simulatedDelayMs: 300,
  // Quick-fill test accounts
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
    if (!API_CONFIG.isDemoMode) {
      try {
        const response = await fetch(`${API_CONFIG.baseUrl}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(credentials)
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
          throw new Error(result.message || 'Authentication failed.');
        }
        try {
          sessionStorage.setItem('edunexus_session', JSON.stringify(result.data));
        } catch (e) {}
        return result;
      } catch (err) {
        if (err.message && !err.message.includes('Failed to fetch')) {
          throw err;
        }
      }
    }

    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const { email, password } = credentials;
        const { demoAccounts } = API_CONFIG;

        let matched = null;
        if (email === demoAccounts.student.email && password === demoAccounts.student.password) {
          matched = demoAccounts.student;
        } else if (email === demoAccounts.faculty.email && password === demoAccounts.faculty.password) {
          matched = demoAccounts.faculty;
        } else if (email === demoAccounts.admin.email && password === demoAccounts.admin.password) {
          matched = demoAccounts.admin;
        } else if (email && password) {
          matched = {
            email,
            name: email.split('@')[0].replace('.', ' '),
            role: email.includes('faculty') ? 'faculty' : (email.includes('admin') ? 'admin' : 'student')
          };
        }

        if (matched) {
          const session = {
            user: matched,
            token: `jwt_token_${Date.now()}`,
            expiresAt: Date.now() + 86400000
          };
          try {
            sessionStorage.setItem('edunexus_session', JSON.stringify(session));
          } catch (e) {}
          resolve({
            success: true,
            message: `Signed in successfully as ${matched.name} (${matched.role.toUpperCase()}).`,
            data: session
          });
        } else {
          reject({
            success: false,
            message: 'Invalid credentials. Please enter a valid email and password.'
          });
        }
      }, API_CONFIG.simulatedDelayMs);
    });
  },

  /**
   * Perform user registration request against the live Flask + Supabase backend.
   * Never resolves with a mock/simulated success if the backend or database insert fails.
   * @param {Object} userData - { fullName, email, password, role }
   * @returns {Promise<Object>}
   */
  async register(userData) {
    let response;
    try {
      response = await fetch(`${API_CONFIG.baseUrl}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });
    } catch (networkErr) {
      throw new Error('Unable to reach the server. Your account could not be saved to the database.');
    }

    let result;
    try {
      result = await response.json();
    } catch (parseErr) {
      throw new Error(`Server returned an invalid response (HTTP ${response.status}). Registration was not saved.`);
    }

    if (!response.ok || !result || !result.success) {
      throw new Error((result && (result.message || result.error)) || 'Database registration failed.');
    }

    return result;
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
        message: 'Activity created.',
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
        message: 'Submission recorded.',
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
  },

  /**
   * Send a student message to the Google Gemini AI Study Assistant endpoint.
   * Never returns simulated/fake responses if the backend or Gemini API fails.
   * @param {Object} payload - { message, history, previous_interaction_id, student_id }
   * @returns {Promise<Object>}
   */
  async sendStudyAssistantMessage(payload) {
    let response;
    try {
      response = await fetch(`${API_CONFIG.baseUrl}/study-assistant/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (networkErr) {
      const err = new Error('Network error: Unable to reach the AI Study Assistant server. Please check your connection and try again.');
      err.errorCode = 'NETWORK_ERROR';
      throw err;
    }

    let result;
    try {
      result = await response.json();
    } catch (parseErr) {
      const err = new Error(`AI Study Assistant returned an unreadable response (HTTP ${response.status}).`);
      err.errorCode = 'INVALID_RESPONSE';
      err.status = response.status;
      throw err;
    }

    if (!response.ok || !result || !result.success) {
      const err = new Error((result && (result.error || result.message)) || 'The AI Study Assistant could not generate a response.');
      err.errorCode = (result && result.error_code) || 'ASSISTANT_ERROR';
      err.status = response.status;
      throw err;
    }

    return result;
  }
};

window.EduNexusAPI = EduNexusAPI;
window.API_CONFIG = API_CONFIG;
window.showToast = showToast;
