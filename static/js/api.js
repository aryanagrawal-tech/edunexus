/**
 * EduNexus AI - Frontend API Service & Configuration
 * Connects directly to the live Flask & Supabase PostgreSQL backend.
 */

const API_CONFIG = {
  baseUrl: (typeof window !== 'undefined' && window.location.origin && window.location.origin.startsWith('http'))
    ? `${window.location.origin}/api`
    : 'http://localhost:5000/api',
  isDemoMode: false,
  simulatedDelayMs: 300,
  demoAccounts: {
    student: {
      email: 'aanya.demo@example.com',
      name: 'Aanya Patel',
      role: 'student',
      course: 'Data Structures'
    },
    faculty: {
      email: 'faculty@edunexus.com',
      name: 'Dr. Sarah Mitchell',
      role: 'faculty',
      department: 'Department of Computer Science',
      courses: ['Data Structures & Algorithms']
    },
    admin: {
      email: 'admin@edunexus.com',
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
    const response = await fetch(`${API_CONFIG.baseUrl}/auth/login`, {
      method: 'POST',
      credentials: 'same-origin',
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
        credentials: 'same-origin',
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
   * Retrieve current authenticated user object from session
   */
  getCurrentUser() {
    const session = this.getCurrentSession();
    return (session && session.user) ? session.user : null;
  },

  /**
   * Clear session on logout (invalidating both server-side Flask session and client storage)
   */
  async logout() {
    try {
      sessionStorage.removeItem('edunexus_session');
    } catch (e) {}
    try {
      await fetch(`${API_CONFIG.baseUrl}/auth/logout`, {
        method: 'POST',
        credentials: 'same-origin'
      });
    } catch (e) {}
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
    const res = await fetch(`${API_CONFIG.baseUrl}/students`);
    return await res.json();
  },

  /**
   * Fetch course activities
   */
  async getActivities(studentId = null) {
    const qs = studentId ? `?student_id=${encodeURIComponent(studentId)}` : '';
    const res = await fetch(`${API_CONFIG.baseUrl}/activities${qs}`);
    return await res.json();
  },

  /**
   * Create course activity or targeted student exercise
   */
  async createActivity(activityData) {
    const res = await fetch(`${API_CONFIG.baseUrl}/activities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(activityData)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || data.message || 'Failed to create activity.');
    }
    return data;
  },

  /**
   * Fetch full student academic dashboard for the logged-in student
   */
  async getStudentDashboard(studentId = 1, email = '') {
    const qs = email ? `?email=${encodeURIComponent(email)}` : '';
    const res = await fetch(`${API_CONFIG.baseUrl}/student/${encodeURIComponent(studentId)}/dashboard${qs}`);
    return await res.json();
  },

  /**
   * Fetch faculty cohort overview, explainable insights, evaluation queue, and course hub
   */
  async getFacultyOverview() {
    const res = await fetch(`${API_CONFIG.baseUrl}/faculty/overview`);
    return await res.json();
  },

  /**
   * Fetch admin platform overview and real registered user directory
   */
  async getAdminOverview() {
    const res = await fetch(`${API_CONFIG.baseUrl}/admin/overview`);
    return await res.json();
  },

  /**
   * Update user account status (Active / Suspended) in Supabase
   */
  async updateUserStatus(payload) {
    const res = await fetch(`${API_CONFIG.baseUrl}/admin/users/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to update account status.');
    }
    return data;
  },

  /**
   * Submit student activity or assignment response
   */
  async submitActivity(submissionData) {
    const res = await fetch(`${API_CONFIG.baseUrl}/submissions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submissionData)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to record submission.');
    }
    return data;
  },

  /**
   * Evaluate student submission with marks and feedback (Faculty only)
   */
  async evaluateSubmission(submissionId, payload) {
    const res = await fetch(`${API_CONFIG.baseUrl}/submissions/${encodeURIComponent(submissionId)}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to evaluate submission.');
    }
    return data;
  },

  /**
   * Fetch faculty-student interventions, feedback, and help requests
   */
  async getInterventions(params = {}) {
    const search = new URLSearchParams();
    if (params.student_id) search.set('student_id', params.student_id);
    if (params.course_code) search.set('course_code', params.course_code);
    const qs = search.toString() ? `?${search.toString()}` : '';
    const res = await fetch(`${API_CONFIG.baseUrl}/interventions${qs}`);
    return await res.json();
  },

  /**
   * Create faculty feedback, targeted support, or student 1-to-1 help/office-hours request
   */
  async createIntervention(payload) {
    const res = await fetch(`${API_CONFIG.baseUrl}/interventions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to save collaboration request.');
    }
    return data;
  },

  /**
   * Faculty response / status update on an intervention or help request
   */
  async respondIntervention(interventionId, payload) {
    const res = await fetch(`${API_CONFIG.baseUrl}/interventions/${encodeURIComponent(interventionId)}/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to update intervention.');
    }
    return data;
  },

  /**
   * Fetch Unified Course Hub data
   */
  async getCourseHub(params = {}) {
    const search = new URLSearchParams();
    if (params.course_code) search.set('course_code', params.course_code);
    if (params.student_id) search.set('student_id', params.student_id);
    const qs = search.toString() ? `?${search.toString()}` : '';
    const res = await fetch(`${API_CONFIG.baseUrl}/course-hub${qs}`);
    return await res.json();
  },

  /**
   * Faculty: Add study material to Course Hub
   */
  async createCourseMaterial(payload) {
    const res = await fetch(`${API_CONFIG.baseUrl}/course-materials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to add study material.');
    }
    return data;
  },

  /**
   * Faculty: Publish course announcement to Course Hub
   */
  async createAnnouncement(payload) {
    const res = await fetch(`${API_CONFIG.baseUrl}/announcements`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to publish announcement.');
    }
    return data;
  },

  /**
   * Run on-demand academic analytics
   */
  async analyzePerformance(payload) {
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
