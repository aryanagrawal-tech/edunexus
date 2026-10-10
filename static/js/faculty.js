/**
 * EduNexus AI - Faculty Dashboard Controller (Vanilla JS)
 * Coordinates real cohort analytics, explainable AI insights, at-risk student support,
 * 1-to-1 interventions, Unified Course Hub, and Submissions Evaluation Queue.
 */

let activeFacultyProfile = {
  name: 'Dr. Sarah Mitchell',
  department: 'Computer Science',
  role: 'faculty'
};
let cachedStudentsRoster = [];

document.addEventListener('DOMContentLoaded', () => {
  initFacultySessionProfile();
  initFacultyDashboard();
  initSidebarToggle();
  initRoleSwitcher();
  initInterventionModal();
  initFacultyCourseHubForms();
  initFacultyCreateAssessmentForm();
});

function getInitials(name) {
  const parts = String(name || 'Faculty').trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return String(parts[0] || 'FC').slice(0, 2).toUpperCase();
}

function escapeHtml(raw) {
  return String(raw || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function initFacultySessionProfile() {
  const sessionUser = (window.EduNexusAPI && typeof window.EduNexusAPI.getCurrentUser === 'function')
    ? window.EduNexusAPI.getCurrentUser()
    : null;

  if (sessionUser && sessionUser.name) {
    activeFacultyProfile = {
      name: sessionUser.name,
      department: sessionUser.department || 'Computer Science',
      email: sessionUser.email || '',
      role: sessionUser.role || 'faculty'
    };
  }

  const avatarElem = document.getElementById('facultySidebarAvatar');
  const nameElem = document.getElementById('facultySidebarName');
  const deptElem = document.getElementById('facultySidebarDept');
  const subtitleElem = document.getElementById('facultyTopbarSubtitle');

  if (avatarElem) avatarElem.textContent = getInitials(activeFacultyProfile.name);
  if (nameElem) nameElem.textContent = activeFacultyProfile.name;
  if (deptElem) deptElem.textContent = activeFacultyProfile.department;
  if (subtitleElem) {
    subtitleElem.textContent = `${activeFacultyProfile.name} · ${activeFacultyProfile.department}`;
  }
}

/**
 * Initialize Faculty Metrics and Cohort Views from Flask + Supabase Backend
 */
async function initFacultyDashboard() {
  let topicDist = [];
  let atRiskStudents = [];
  let assessments = [];
  let explainableInsights = [];
  let insightsMeta = { has_sufficient_data: false, message: 'No assessment data available' };
  let submissionsQueue = [];
  let interventionsList = [];
  let courseHub = { courses: [], materials: [], announcements: [] };

  if (window.EduNexusAPI) {
    try {
      const overviewRes = await window.EduNexusAPI.getFacultyOverview();
      if (overviewRes && overviewRes.success && overviewRes.data) {
        const ov = overviewRes.data;
        cachedStudentsRoster = Array.isArray(ov.students_roster) ? ov.students_roster : [];
        populateModalStudentsDropdown(cachedStudentsRoster);

        const enrolledElem = document.getElementById('statEnrolledCount');
        const avgElem = document.getElementById('statClassAverage');
        const atRiskElem = document.getElementById('statAtRiskCount');
        const sidebarAtRiskPill = document.getElementById('sidebarAtRiskPill');
        const subCountElem = document.getElementById('statAttendanceRate');
        const subMetaElem = document.getElementById('statSubmissionsMeta');

        if (enrolledElem && typeof ov.enrolled_count === 'number') {
          enrolledElem.textContent = String(ov.enrolled_count);
        }
        if (avgElem && typeof ov.class_average === 'number') {
          avgElem.textContent = `${ov.class_average}%`;
        }
        if (atRiskElem && typeof ov.at_risk_count === 'number') {
          atRiskElem.textContent = String(ov.at_risk_count);
        }
        if (sidebarAtRiskPill && typeof ov.at_risk_count === 'number') {
          sidebarAtRiskPill.textContent = `${ov.at_risk_count} Flagged`;
        }

        submissionsQueue = Array.isArray(ov.submissions_queue) ? ov.submissions_queue : [];
        const pendingEvalCount = submissionsQueue.filter(s => s.status === 'pending_review' || !s.evaluated_by).length;
        if (subCountElem) {
          subCountElem.textContent = String(submissionsQueue.length);
        }
        if (subMetaElem) {
          subMetaElem.innerHTML = pendingEvalCount > 0
            ? `<span class="trend-attention">${pendingEvalCount} submission(s)</span> awaiting grading`
            : 'All submissions evaluated';
        }

        if (Array.isArray(ov.topic_mastery_distribution) && ov.topic_mastery_distribution.length > 0) {
          topicDist = ov.topic_mastery_distribution.map(item => ({
            topic: item.topic,
            avgScore: item.avg_score,
            benchmark: item.benchmark || 70,
            masteryStatus: item.status
          }));
        }

        if (Array.isArray(ov.at_risk_students)) {
          atRiskStudents = ov.at_risk_students.map(std => ({
            id: std.student_id,
            name: std.name,
            email: std.email || '',
            studentId: `ID-${std.student_id}`,
            courseCode: ov.course || 'Data Structures',
            currentScore: std.overall_score,
            riskLevel: std.risk_level,
            riskSeverity: std.risk_level === 'High Risk' ? 'danger' : 'warning',
            indicators: Array.isArray(std.primary_concerns) ? std.primary_concerns.join(' · ') : (std.primary_concerns || 'Below threshold'),
            lastActive: `${std.submission_count || 0} submission(s)`,
            suggestedIntervention: std.suggested_intervention
          }));
        }

        explainableInsights = Array.isArray(ov.explainable_insights) ? ov.explainable_insights : [];
        if (ov.insights_meta) {
          insightsMeta = ov.insights_meta;
        }
        interventionsList = Array.isArray(ov.interventions) ? ov.interventions : [];
        if (ov.course_hub) {
          courseHub = ov.course_hub;
        }
      }
    } catch (err) {
      if (window.showToast) {
        window.showToast('Unable to load faculty overview from backend.', 'error');
      }
    }

    try {
      const actRes = await window.EduNexusAPI.getActivities();
      if (actRes && actRes.success && Array.isArray(actRes.data)) {
        assessments = actRes.data.map(act => ({
          id: act.id,
          title: act.title,
          topic: act.topic || 'General',
          dueDate: act.due_date || 'Rolling',
          type: act.activity_type || 'quiz',
          assignedStudentId: act.assigned_student_id,
          maxScore: act.max_score || 100,
          status: act.assigned_student_id ? `Targeted (Student #${act.assigned_student_id})` : 'Course-Wide'
        }));
      }
    } catch (err) {
      // Keep empty list if request fails
    }
  }

  // Render Priority 5: Explainable & Actionable AI Insights
  renderExplainableInsights(explainableInsights, insightsMeta);

  // Render Comparative Bar Chart
  if (window.EduNexusCharts) {
    window.EduNexusCharts.renderComparativeBarChart('facultyTopicChart', topicDist);
  }

  // Render Priority 3A: At-Risk Students Table
  renderAtRiskStudents(atRiskStudents);

  // Render Priority 3B: One-to-One Interventions & Help Requests
  renderFacultyInterventions(interventionsList);

  // Render Priority 4: Unified Course Hub
  renderFacultyCourseHub(courseHub);

  // Render Priority 4: Assessments & Submissions Evaluation Queue
  renderAssessments(assessments);
  renderEvaluationQueue(submissionsQueue);
}

/**
 * Priority 5: Render Explainable & Actionable AI Insights
 */
function renderExplainableInsights(insights, meta) {
  const container = document.getElementById('explainableInsightsContainer');
  const badgeElem = document.getElementById('insightsCountBadge');
  if (!container) return;

  container.innerHTML = '';

  if (!Array.isArray(insights) || insights.length === 0) {
    if (badgeElem) badgeElem.textContent = '0 Alerts';
    const msg = (meta && meta.message)
      ? meta.message
      : 'Insufficient assessment data to generate cohort insights. Record or evaluate student submissions first.';
    container.innerHTML = `<div class="empty-state-box">${escapeHtml(msg)}</div>`;
    return;
  }

  if (badgeElem) {
    badgeElem.textContent = `${insights.length} Actionable Insight(s)`;
  }

  insights.forEach(item => {
    const card = document.createElement('div');
    const sevClass = item.severity === 'critical' ? 'insight-card-critical' : 'insight-card-warning';
    card.className = `insight-card ${sevClass}`;

    const evidenceItemsHtml = (Array.isArray(item.evidence) ? item.evidence : [])
      .map(ev => `<li>${escapeHtml(ev)}</li>`)
      .join('');

    card.innerHTML = `
      <div class="weak-alert-header">
        <span class="weak-alert-title" style="font-size: 0.95rem;">${escapeHtml(item.summary || item.topic)}</span>
        <span class="weak-alert-score">Cohort Avg: ${escapeHtml(String(item.average_score))}% (${escapeHtml(item.priority || 'High')} Priority)</span>
      </div>
      <div style="font-size: 0.78rem; font-weight: 600; color: #334155; margin-top: 2px;">Underlying Database Evidence:</div>
      <ul class="insight-evidence-list">
        ${evidenceItemsHtml}
      </ul>
      <div class="insight-footer">
        <div style="font-size: 0.8rem; color: #1E293B;">
          <strong>Recommended Faculty Action:</strong> ${escapeHtml(item.recommended_action)}
        </div>
        <button
          type="button"
          class="btn btn-primary"
          style="padding: 0.35rem 0.85rem; font-size: 0.78rem;"
          data-action="initiate-insight-action"
          data-topic="${escapeHtml(item.topic)}"
          data-action-type="${escapeHtml(item.action_type || 'assign_remedial_quiz')}"
          data-recommended="${escapeHtml(item.recommended_action)}"
        >
          Initiate Action
        </button>
      </div>
    `;
    container.appendChild(card);
  });

  container.querySelectorAll('[data-action="initiate-insight-action"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const topic = btn.getAttribute('data-topic') || 'General';
      const recommended = btn.getAttribute('data-recommended') || '';
      const titleInput = document.getElementById('newAssessmentTitle');
      const topicInput = document.getElementById('newAssessmentTopic');
      const instrInput = document.getElementById('newAssessmentInstructions');

      if (titleInput) titleInput.value = `${topic} — Targeted Remedial Quiz`;
      if (topicInput) topicInput.value = topic;
      if (instrInput) instrInput.value = `${recommended} Focus on core ${topic} problem-solving patterns.`;

      const formElem = document.getElementById('facultyCreateAssessmentForm');
      if (formElem && typeof formElem.scrollIntoView === 'function') {
        formElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      if (titleInput) titleInput.focus();
      window.showToast(`Pre-filled remedial assessment for "${topic}". Click Publish Assessment to assign.`, 'info');
    });
  });
}

/**
 * Priority 3A: Render At-Risk Students Table
 */
function renderAtRiskStudents(students) {
  const tbody = document.getElementById('atRiskTableBody');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (!Array.isArray(students) || students.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="table-empty-cell">No students currently meet at-risk criteria based on graded submissions.</td>
      </tr>
    `;
    return;
  }

  students.forEach(std => {
    const tr = document.createElement('tr');
    const isHigh = std.riskSeverity === 'danger';
    const pillClass = isHigh ? 'risk-danger' : 'risk-warning';

    tr.innerHTML = `
      <td>
        <div class="cell-title">${escapeHtml(std.name)}</div>
        <div class="cell-sub">${escapeHtml(std.studentId)} · ${escapeHtml(std.courseCode)}</div>
      </td>
      <td>
        <span class="mastery-score-tag ${isHigh ? 'mastery-tag-danger' : 'mastery-tag-warning'}">
          ${escapeHtml(String(std.currentScore))}%
        </span>
      </td>
      <td>
        <span class="risk-pill ${pillClass}">
          ${escapeHtml(std.riskLevel)}
        </span>
      </td>
      <td>
        <div class="cell-body">${escapeHtml(std.indicators)}</div>
      </td>
      <td>
        <span class="cell-sub">${escapeHtml(std.lastActive)}</span>
      </td>
      <td>
        <button 
          type="button" 
          class="action-pill-btn" 
          data-action="intervene"
          data-student-id="${escapeHtml(String(std.id))}"
          data-student-name="${escapeHtml(std.name)}"
          data-suggested-action="${escapeHtml(std.suggestedIntervention)}"
        >
          Assign Support / Feedback
        </button>
      </td>
    `;

    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-action="intervene"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const studentId = Number(btn.getAttribute('data-student-id')) || 1;
      const studentName = btn.getAttribute('data-student-name');
      const suggestedAction = btn.getAttribute('data-suggested-action');
      openInterventionModal(studentId, studentName, suggestedAction);
    });
  });
}

/**
 * Priority 3B: Render One-to-One Student Help Requests & Interventions
 */
function renderFacultyInterventions(interventions) {
  const container = document.getElementById('facultyInterventionsList');
  const badgeElem = document.getElementById('interventionsCountBadge');
  if (!container) return;

  container.innerHTML = '';
  const list = Array.isArray(interventions) ? interventions : [];
  const openCount = list.filter(i => i.status === 'open').length;
  if (badgeElem) {
    badgeElem.textContent = `${openCount} Open`;
  }

  if (list.length === 0) {
    container.innerHTML = '<div class="empty-state-box">No student help requests or academic interventions recorded yet.</div>';
    return;
  }

  list.forEach(item => {
    const card = document.createElement('div');
    card.className = 'rec-card';
    const status = String(item.status || 'open');
    const isResolved = status === 'resolved' || status === 'responded';

    card.innerHTML = `
      <div class="rec-main" style="flex: 1 1 100%;">
        <div class="rec-content">
          <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;">
            <h4 class="rec-title" style="margin-bottom: 2px;">${escapeHtml(item.title)} — <span style="color: #2563EB;">${escapeHtml(item.student_name || `Student #${item.student_id}`)}</span></h4>
            <span class="badge ${isResolved ? 'badge-info' : 'badge-demo'}">${escapeHtml(status)}</span>
          </div>
          <p class="weak-alert-msg" style="margin: 4px 0;">${escapeHtml(item.details || '')}</p>
          <div class="rec-meta" style="margin-bottom: 8px;">
            <span>Topic: <strong>${escapeHtml(item.topic || 'General')}</strong></span>
            <span>·</span>
            <span>Course: ${escapeHtml(item.course_code || 'CS-301')}</span>
            <span>·</span>
            <span>Initiated by: ${escapeHtml(item.initiated_by || 'student')}</span>
          </div>
          <div class="eval-inline-controls">
            <input
              type="text"
              class="eval-feedback-input"
              data-intervention-response="${item.id}"
              placeholder="Write faculty response or office-hours schedule..."
              value="${escapeHtml(item.faculty_response || '')}"
            >
            <select class="eval-score-input" style="width: 120px;" data-intervention-status="${item.id}">
              <option value="responded" ${status === 'responded' ? 'selected' : ''}>Responded</option>
              <option value="scheduled" ${status === 'scheduled' ? 'selected' : ''}>Scheduled</option>
              <option value="resolved" ${status === 'resolved' ? 'selected' : ''}>Resolved</option>
              <option value="open" ${status === 'open' ? 'selected' : ''}>Open</option>
            </select>
            <button type="button" class="action-pill-btn" data-action="respond-intervention" data-id="${item.id}">
              Save Response
            </button>
          </div>
        </div>
      </div>
    `;
    container.appendChild(card);
  });

  container.querySelectorAll('[data-action="respond-intervention"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = Number(btn.getAttribute('data-id'));
      const respInput = container.querySelector(`[data-intervention-response="${id}"]`);
      const statusSelect = container.querySelector(`[data-intervention-status="${id}"]`);
      const facultyResponse = respInput ? respInput.value.trim() : '';
      const status = statusSelect ? statusSelect.value : 'responded';

      if (!facultyResponse) {
        window.showToast('Please enter a response before saving.', 'error');
        return;
      }

      btn.disabled = true;
      try {
        const res = await window.EduNexusAPI.respondIntervention(id, {
          role: 'faculty',
          status,
          faculty_response: facultyResponse,
          faculty_name: activeFacultyProfile.name
        });
        if (res && res.success) {
          window.showToast('Intervention response saved to database!', 'success');
          await initFacultyDashboard();
        }
      } catch (err) {
        window.showToast(err.message || 'Failed to update intervention.', 'error');
      } finally {
        btn.disabled = false;
      }
    });
  });
}

/**
 * Priority 4: Render & Handle Unified Course Hub (Announcements & Materials)
 */
function renderFacultyCourseHub(hub) {
  const annList = document.getElementById('facultyAnnouncementsList');
  if (annList) {
    annList.innerHTML = '';
    const announcements = Array.isArray(hub.announcements) ? hub.announcements : [];
    if (announcements.length === 0) {
      annList.innerHTML = '<div class="empty-state-box">No announcements published yet.</div>';
    } else {
      announcements.slice(0, 5).forEach(ann => {
        const div = document.createElement('div');
        div.className = 'rec-card';
        div.innerHTML = `
          <div class="rec-main">
            <div class="rec-content">
              <h4 class="rec-title">${escapeHtml(ann.title)}</h4>
              <p class="weak-alert-msg" style="margin-bottom: 4px;">${escapeHtml(ann.message)}</p>
              <div class="rec-meta">
                <span>${escapeHtml(ann.course_code || 'CS-301')}</span>
                <span>·</span>
                <span>${escapeHtml(ann.published_by || 'Faculty')}</span>
              </div>
            </div>
          </div>
          <span class="badge ${ann.priority === 'urgent' ? 'badge-demo' : 'badge-info'}">${escapeHtml(ann.priority || 'normal')}</span>
        `;
        annList.appendChild(div);
      });
    }
  }

  const matList = document.getElementById('facultyMaterialsList');
  if (matList) {
    matList.innerHTML = '';
    const materials = Array.isArray(hub.materials) ? hub.materials : [];
    if (materials.length === 0) {
      matList.innerHTML = '<div class="empty-state-box">No study materials uploaded yet.</div>';
    } else {
      materials.slice(0, 5).forEach(mat => {
        const div = document.createElement('div');
        div.className = 'rec-card';
        div.innerHTML = `
          <div class="rec-main">
            <div class="rec-content">
              <h4 class="rec-title">${escapeHtml(mat.title)}</h4>
              <p class="weak-alert-msg" style="margin-bottom: 4px;">${escapeHtml(mat.content_or_url || '')}</p>
              <div class="rec-meta">
                <span>Topic: ${escapeHtml(mat.topic || 'General')}</span>
                <span>·</span>
                <span>${escapeHtml(mat.uploaded_by || 'Faculty')}</span>
              </div>
            </div>
          </div>
          <span class="badge badge-info">${escapeHtml(mat.resource_type || 'Notes')}</span>
        `;
        matList.appendChild(div);
      });
    }
  }
}

function initFacultyCourseHubForms() {
  const annForm = document.getElementById('facultyAnnouncementForm');
  if (annForm) {
    annForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const titleInput = document.getElementById('announcementTitleInput');
      const priorityInput = document.getElementById('announcementPriorityInput');
      const msgInput = document.getElementById('announcementMessageInput');
      const btn = document.getElementById('publishAnnouncementBtn');

      const title = titleInput ? titleInput.value.trim() : '';
      const priority = priorityInput ? priorityInput.value : 'normal';
      const message = msgInput ? msgInput.value.trim() : '';

      if (!title || !message) {
        window.showToast('Please provide an announcement title and message.', 'error');
        return;
      }

      if (btn) btn.disabled = true;
      try {
        const res = await window.EduNexusAPI.createAnnouncement({
          role: 'faculty',
          course_code: 'CS-301',
          title,
          message,
          priority,
          published_by: activeFacultyProfile.name
        });
        if (res && res.success) {
          window.showToast('Course announcement published!', 'success');
          annForm.reset();
          await initFacultyDashboard();
        }
      } catch (err) {
        window.showToast(err.message || 'Failed to publish announcement.', 'error');
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }

  const matForm = document.getElementById('facultyMaterialForm');
  if (matForm) {
    matForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const titleInput = document.getElementById('materialTitleInput');
      const topicInput = document.getElementById('materialTopicInput');
      const typeInput = document.getElementById('materialTypeInput');
      const contentInput = document.getElementById('materialContentInput');
      const btn = document.getElementById('publishMaterialBtn');

      const title = titleInput ? titleInput.value.trim() : '';
      const topic = topicInput ? topicInput.value.trim() : 'General';
      const resourceType = typeInput ? typeInput.value : 'Lecture Notes';
      const contentOrUrl = contentInput ? contentInput.value.trim() : '';

      if (!title || !contentOrUrl) {
        window.showToast('Please provide a material title and study content/link.', 'error');
        return;
      }

      if (btn) btn.disabled = true;
      try {
        const res = await window.EduNexusAPI.createCourseMaterial({
          role: 'faculty',
          course_code: 'CS-301',
          title,
          topic,
          resource_type: resourceType,
          content_or_url: contentOrUrl,
          uploaded_by: activeFacultyProfile.name
        });
        if (res && res.success) {
          window.showToast('Study material published to Course Hub!', 'success');
          matForm.reset();
          await initFacultyDashboard();
        }
      } catch (err) {
        window.showToast(err.message || 'Failed to publish study material.', 'error');
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }
}

/**
 * Priority 4: Render & Create Assessments + Evaluate Student Submissions
 */
function renderAssessments(assessments) {
  const tbody = document.getElementById('assessmentsTableBody');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (!Array.isArray(assessments) || assessments.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="table-empty-cell">No course assessments created yet.</td>
      </tr>
    `;
    return;
  }

  assessments.forEach(asm => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${escapeHtml(asm.title)}</strong></td>
      <td>${escapeHtml(asm.topic)} · <span class="cell-sub">Due: ${escapeHtml(asm.dueDate)}</span></td>
      <td>${escapeHtml(asm.type)}</td>
      <td><strong>${escapeHtml(String(asm.maxScore))} pts</strong></td>
      <td>
        <span class="badge ${asm.assignedStudentId ? 'badge-demo' : 'badge-info'}">
          ${escapeHtml(asm.status)}
        </span>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function initFacultyCreateAssessmentForm() {
  const createBtn = document.getElementById('createAssessmentBtn');
  const form = document.getElementById('facultyCreateAssessmentForm');
  const titleInput = document.getElementById('newAssessmentTitle');

  if (createBtn && titleInput) {
    createBtn.addEventListener('click', () => {
      titleInput.focus();
    });
  }

  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('newAssessmentTitle').value.trim();
    const topic = document.getElementById('newAssessmentTopic').value.trim();
    const activityType = document.getElementById('newAssessmentType').value;
    const dueDate = document.getElementById('newAssessmentDueDate').value;
    const instructions = document.getElementById('newAssessmentInstructions').value.trim();
    const submitBtn = document.getElementById('submitNewAssessmentBtn');

    if (!title || !topic) {
      window.showToast('Please provide an assessment title and topic.', 'error');
      return;
    }

    if (submitBtn) submitBtn.disabled = true;
    try {
      const res = await window.EduNexusAPI.createActivity({
        role: 'faculty',
        title,
        topic,
        activity_type: activityType,
        max_score: 100,
        due_date: dueDate,
        instructions,
        course_code: 'CS-301',
        created_by_faculty: activeFacultyProfile.name
      });
      if (res && res.success) {
        window.showToast(`Published assessment "${title}"!`, 'success');
        form.reset();
        await initFacultyDashboard();
      }
    } catch (err) {
      window.showToast(err.message || 'Failed to create assessment.', 'error');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

function renderEvaluationQueue(submissions) {
  const tbody = document.getElementById('evaluationQueueTableBody');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (!Array.isArray(submissions) || submissions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="table-empty-cell">No student submissions in the evaluation queue yet.</td>
      </tr>
    `;
    return;
  }

  submissions.forEach(sub => {
    const tr = document.createElement('tr');
    const status = String(sub.status || 'submitted');
    const isEvaluated = status === 'evaluated' || Boolean(sub.evaluated_by);

    tr.innerHTML = `
      <td>
        <div class="cell-title">${escapeHtml(sub.student_name || `Student #${sub.student_id}`)}</div>
        <div class="cell-sub">${escapeHtml(sub.student_email || `ID-${sub.student_id}`)}</div>
      </td>
      <td>
        <div class="cell-title">${escapeHtml(sub.activity_title || `Activity #${sub.activity_id}`)}</div>
        <div class="cell-sub">Topic: ${escapeHtml(sub.topic || 'General')}</div>
      </td>
      <td>
        <div class="cell-body">${escapeHtml(sub.response_text || 'Score recorded directly')}</div>
        ${sub.evaluated_by ? `<div class="cell-sub">Graded by ${escapeHtml(sub.evaluated_by)}</div>` : ''}
      </td>
      <td>
        <span class="badge ${isEvaluated ? 'badge-info' : 'badge-demo'}">${escapeHtml(status)}</span>
      </td>
      <td>
        <div class="eval-inline-controls">
          <input
            type="number"
            class="eval-score-input"
            min="0"
            max="100"
            data-eval-score="${sub.id}"
            value="${sub.score !== undefined && sub.score !== null ? escapeHtml(String(sub.score)) : ''}"
            placeholder="Score"
            aria-label="Score for submission ${sub.id}"
          >
          <input
            type="text"
            class="eval-feedback-input"
            data-eval-feedback="${sub.id}"
            value="${escapeHtml(sub.feedback || '')}"
            placeholder="Enter faculty feedback..."
            aria-label="Feedback for submission ${sub.id}"
          >
          <button
            type="button"
            class="action-pill-btn"
            data-action="evaluate-submission"
            data-submission-id="${sub.id}"
          >
            Save Marks
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-action="evaluate-submission"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const subId = Number(btn.getAttribute('data-submission-id'));
      const scoreInput = tbody.querySelector(`[data-eval-score="${subId}"]`);
      const feedbackInput = tbody.querySelector(`[data-eval-feedback="${subId}"]`);

      const scoreVal = scoreInput ? Number(scoreInput.value) : NaN;
      const feedbackVal = feedbackInput ? feedbackInput.value.trim() : '';

      if (Number.isNaN(scoreVal) || scoreVal < 0 || scoreVal > 100) {
        window.showToast('Please enter a valid mark between 0 and 100.', 'error');
        return;
      }

      btn.disabled = true;
      try {
        const res = await window.EduNexusAPI.evaluateSubmission(subId, {
          role: 'faculty',
          score: scoreVal,
          feedback: feedbackVal,
          evaluated_by: activeFacultyProfile.name
        });
        if (res && res.success) {
          window.showToast(`Marks (${scoreVal}%) and feedback saved for submission #${subId}!`, 'success');
          await initFacultyDashboard();
        }
      } catch (err) {
        window.showToast(err.message || 'Failed to save evaluation.', 'error');
      } finally {
        btn.disabled = false;
      }
    });
  });
}

/**
 * Priority 3A: Academic Support & Targeted Practice Modal Logic
 */
let activeInterventionModal = null;

function populateModalStudentsDropdown(students) {
  const selectElem = document.getElementById('modalStudentSelect');
  if (!selectElem) return;
  selectElem.innerHTML = '';
  if (!Array.isArray(students) || students.length === 0) {
    selectElem.innerHTML = '<option value="1">Student #1</option>';
    return;
  }
  students.forEach(s => {
    const opt = document.createElement('option');
    opt.value = String(s.id);
    opt.textContent = `${s.name} (${s.email || `ID-${s.id}`})`;
    opt.setAttribute('data-student-name', s.name);
    selectElem.appendChild(opt);
  });
}

function initInterventionModal() {
  const backdrop = document.getElementById('interventionModalBackdrop');
  const closeBtn = document.getElementById('closeModalBtn');
  const cancelBtn = document.getElementById('cancelModalBtn');
  const confirmBtn = document.getElementById('confirmInterventionBtn');
  const directSupportBtn = document.getElementById('openDirectSupportBtn');

  if (!backdrop) return;
  activeInterventionModal = backdrop;

  const closeModal = () => {
    backdrop.classList.remove('is-open');
  };

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  if (directSupportBtn) {
    directSupportBtn.addEventListener('click', () => {
      const firstStudent = cachedStudentsRoster[0] || { id: 1, name: 'Student' };
      openInterventionModal(firstStudent.id, firstStudent.name, 'Targeted Topic Review & Practice');
    });
  }

  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) closeModal();
  });

  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      const selectElem = document.getElementById('modalStudentSelect');
      const modeSelect = document.getElementById('modalActionModeSelect');
      const topicInput = document.getElementById('modalTopicInput');
      const actionInput = document.getElementById('modalSuggestedAction');
      const notesInput = document.getElementById('modalInterventionNotes');

      const studentId = selectElem ? Number(selectElem.value) : 1;
      const selectedOpt = selectElem && selectElem.options[selectElem.selectedIndex];
      const studentName = (selectedOpt && selectedOpt.getAttribute('data-student-name')) || 'Student';
      const actionMode = modeSelect ? modeSelect.value : 'feedback';
      const topic = (topicInput && topicInput.value.trim()) || 'General';
      const title = (actionInput && actionInput.value.trim()) || 'Faculty Academic Support';
      const details = (notesInput && notesInput.value.trim()) || 'Please review the recommended study materials and practice problems.';

      confirmBtn.disabled = true;
      try {
        if (actionMode === 'targeted_practice') {
          await window.EduNexusAPI.createActivity({
            role: 'faculty',
            title,
            topic,
            activity_type: 'quiz',
            max_score: 100,
            instructions: details,
            assigned_student_id: studentId,
            course_code: 'CS-301',
            created_by_faculty: activeFacultyProfile.name
          });
          window.showToast(`Assigned targeted practice "${title}" to ${studentName}!`, 'success');
        } else {
          await window.EduNexusAPI.createIntervention({
            student_id: studentId,
            student_name: studentName,
            faculty_name: activeFacultyProfile.name,
            course_code: 'CS-301',
            topic,
            intervention_type: 'faculty_feedback',
            initiated_by: 'faculty',
            title,
            details,
            faculty_response: details
          });
          window.showToast(`Sent faculty feedback to ${studentName}!`, 'success');
        }
        closeModal();
        await initFacultyDashboard();
      } catch (err) {
        window.showToast(err.message || 'Failed to dispatch support action.', 'error');
      } finally {
        confirmBtn.disabled = false;
      }
    });
  }
}

function openInterventionModal(studentId, studentName, suggestedAction) {
  if (!activeInterventionModal) return;

  const selectElem = document.getElementById('modalStudentSelect');
  const nameElem = document.getElementById('modalStudentName');
  const actionElem = document.getElementById('modalSuggestedAction');
  const notesElem = document.getElementById('modalInterventionNotes');

  if (selectElem && studentId) {
    selectElem.value = String(studentId);
  }
  if (nameElem) nameElem.textContent = `Target Student: ${studentName} (ID #${studentId})`;
  if (actionElem) actionElem.value = suggestedAction || 'Targeted Academic Support';
  if (notesElem) {
    notesElem.value = `Proactive faculty support for ${studentName}: ${suggestedAction || 'Review recent weak topics and complete practice exercises.'}`;
  }

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
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
      window.location.reload();
    }
  });

  const switcher = document.getElementById('roleSwitcherSelect');
  if (switcher) {
    switcher.value = 'faculty';
    switcher.addEventListener('change', () => {
      if (switcher.value !== 'faculty') {
        switcher.value = 'faculty';
        if (window.showToast) {
          window.showToast('Role access is restricted to your authenticated Faculty session.', 'error');
        }
      }
    });
  }

  const logoutButtons = document.querySelectorAll('[data-action="logout"]');
  logoutButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      if (window.EduNexusAPI) {
        await window.EduNexusAPI.logout();
      }
      window.showToast("Logged out of faculty session. Redirecting...", "info");
      setTimeout(() => {
        window.location.replace('/login');
      }, 300);
    });
  });
}
