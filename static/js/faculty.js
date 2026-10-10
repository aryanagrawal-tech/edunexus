/**
 * EduNexus AI - Faculty Dashboard Controller (Vanilla JS)
 * Coordinates course analytics, class performance charts, at-risk student monitoring,
 * and academic intervention workflows.
 */

document.addEventListener('DOMContentLoaded', () => {
  initFacultyDashboard();
  initSidebarToggle();
  initRoleSwitcher();
  initInterventionModal();
});

/**
 * Initialize Faculty Metrics and Cohort Views
 */
function initFacultyDashboard() {
  const data = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.faculty;
  if (!data) return;

  // Render Comparative Bar Chart
  if (window.EduNexusCharts) {
    window.EduNexusCharts.renderComparativeBarChart('facultyTopicChart', data.topicMasteryDistribution);
  }

  // Render At-Risk Students Table
  renderAtRiskStudents(data.atRiskStudents);

  // Render Assessments List
  renderAssessments(data.recentAssessments);

  // Course Selector Listener
  const courseSelect = document.getElementById('facultyCourseSelect');
  if (courseSelect) {
    courseSelect.addEventListener('change', () => {
      const selectedId = courseSelect.value;
      const course = data.courses.find(c => c.id === selectedId);
      if (course) {
        updateCourseStats(course);
        window.showToast(`Switched active view to ${course.code}: ${course.title}`, 'info');
      }
    });
  }
}

/**
 * Update Dashboard Stat Cards on Course Switch
 */
function updateCourseStats(course) {
  const enrolledElem = document.getElementById('statEnrolledCount');
  const avgElem = document.getElementById('statClassAverage');
  const atRiskElem = document.getElementById('statAtRiskCount');
  const attendanceElem = document.getElementById('statAttendanceRate');

  if (enrolledElem) enrolledElem.textContent = course.enrolledCount;
  if (avgElem) avgElem.textContent = `${course.classAverage}%`;
  if (atRiskElem) atRiskElem.textContent = course.atRiskCount;
  if (attendanceElem) attendanceElem.textContent = `${course.attendanceRate}%`;
}

/**
 * Render At-Risk Students Table
 */
function renderAtRiskStudents(students) {
  const tbody = document.getElementById('atRiskTableBody');
  if (!tbody || !students) return;

  tbody.innerHTML = '';
  students.forEach(std => {
    const tr = document.createElement('tr');

    const isHigh = std.riskSeverity === 'danger';
    const pillClass = isHigh ? 'risk-danger' : 'risk-warning';

    tr.innerHTML = `
      <td>
        <div class="cell-title">${std.name}</div>
        <div class="cell-sub">${std.studentId} · ${std.courseCode}</div>
      </td>
      <td>
        <span class="mastery-score-tag ${isHigh ? 'mastery-tag-danger' : 'mastery-tag-warning'}">
          ${std.currentScore}%
        </span>
      </td>
      <td>
        <span class="risk-pill ${pillClass}">
          ${std.riskLevel}
        </span>
      </td>
      <td>
        <div class="cell-body">${std.indicators}</div>
      </td>
      <td>
        <span class="cell-sub">${std.lastActive}</span>
      </td>
      <td>
        <button 
          type="button" 
          class="action-pill-btn" 
          data-action="intervene"
          data-student-id="${std.id}"
          data-student-name="${std.name}"
          data-suggested-action="${std.suggestedIntervention}"
        >
          Intervene
        </button>
      </td>
    `;

    tbody.appendChild(tr);
  });

  // Attach intervention button listeners
  tbody.querySelectorAll('[data-action="intervene"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const studentName = btn.getAttribute('data-student-name');
      const suggestedAction = btn.getAttribute('data-suggested-action');
      openInterventionModal(studentName, suggestedAction);
    });
  });
}

/**
 * Render Recent Assessments Table
 */
function renderAssessments(assessments) {
  const tbody = document.getElementById('assessmentsTableBody');
  if (!tbody || !assessments) return;

  tbody.innerHTML = '';
  assessments.forEach(asm => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${asm.title}</strong></td>
      <td>${asm.date}</td>
      <td>${asm.submissions}</td>
      <td><strong>${asm.averageScore}</strong></td>
      <td>
        <span class="badge ${asm.status === 'Graded' ? 'badge-info' : 'badge-demo'}">
          ${asm.status}
        </span>
      </td>
    `;
    tbody.appendChild(tr);
  });

  const createBtn = document.getElementById('createAssessmentBtn');
  if (createBtn) {
    createBtn.addEventListener('click', () => {
      window.showToast("Assessment creation module simulated [Phase 1 Demo].", "info");
    });
  }
}

/**
 * Intervention Modal Logic
 */
let activeInterventionModal = null;

function initInterventionModal() {
  const backdrop = document.getElementById('interventionModalBackdrop');
  const closeBtn = document.getElementById('closeModalBtn');
  const cancelBtn = document.getElementById('cancelModalBtn');
  const confirmBtn = document.getElementById('confirmInterventionBtn');

  if (!backdrop) return;
  activeInterventionModal = backdrop;

  const closeModal = () => {
    backdrop.classList.remove('is-open');
  };

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) closeModal();
  });

  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      const studentNameElem = document.getElementById('modalStudentName');
      const name = studentNameElem ? studentNameElem.textContent : 'Student';
      closeModal();
      window.showToast(`Academic intervention dispatched to ${name}! [Simulated]`, 'success');
    });
  }
}

function openInterventionModal(studentName, suggestedAction) {
  if (!activeInterventionModal) return;

  const nameElem = document.getElementById('modalStudentName');
  const actionElem = document.getElementById('modalSuggestedAction');
  const notesElem = document.getElementById('modalInterventionNotes');

  if (nameElem) nameElem.textContent = studentName;
  if (actionElem) actionElem.value = suggestedAction;
  if (notesElem) notesElem.value = `Follow-up on recent assessment challenges. Proactive academic counseling recommended.`;

  activeInterventionModal.classList.add('is-open');
}

/**
 * Mobile Sidebar Drawer Toggle
 */
function initSidebarToggle() {
  const toggleBtn = document.getElementById('sidebarToggleBtn');
  const sidebar = document.getElementById('appSidebar');
  const backdrop = document.getElementById('sidebarBackdrop');

  if (!toggleBtn || !sidebar || !backdrop) return;

  toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('is-open');
    backdrop.classList.toggle('is-open');
  });

  backdrop.addEventListener('click', () => {
    sidebar.classList.remove('is-open');
    backdrop.classList.remove('is-open');
  });
}

/**
 * Role Switcher & Logout Navigation
 */
function initRoleSwitcher() {
  const switcher = document.getElementById('roleSwitcherSelect');
  if (switcher) {
    switcher.addEventListener('change', () => {
      const targetRole = switcher.value;
      if (targetRole === 'student') {
        window.location.href = '/student-dashboard';
      } else if (targetRole === 'faculty') {
        window.location.href = '/faculty-dashboard';
      } else if (targetRole === 'admin') {
        window.location.href = '/admin-dashboard';
      }
    });
  }

  const logoutButtons = document.querySelectorAll('[data-action="logout"]');
  logoutButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      if (window.EduNexusAPI) {
        window.EduNexusAPI.logout();
      }
      window.showToast("Logged out of faculty session. Redirecting...", "info");
      setTimeout(() => {
        window.location.href = '/login';
      }, 500);
    });
  });
}
