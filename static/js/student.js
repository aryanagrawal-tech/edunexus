/**
 * EduNexus AI - Student Dashboard Controller (Vanilla JS)
 * Coordinates real student profile & analytics, Course Hub materials/announcements,
 * assignment submissions & marks, 1-to-1 faculty support, and AI Study Assistant.
 */

let activeStudentProfile = null;

document.addEventListener('DOMContentLoaded', () => {
  initStudentDashboard();
  initSidebarToggle();
  initRoleSwitcher();
  initAIAssistant();
  initStudentSubmissionForm();
  initStudentHelpRequestForm();
});

function getInitials(name) {
  const parts = String(name || 'Student').trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return String(parts[0] || 'ST').slice(0, 2).toUpperCase();
}

/**
 * Initialize Student Metrics and Content from Flask + Supabase Backend
 */
async function initStudentDashboard() {
  const sessionUser = (window.EduNexusAPI && typeof window.EduNexusAPI.getCurrentUser === 'function')
    ? window.EduNexusAPI.getCurrentUser()
    : null;

  const targetStudentId = (sessionUser && sessionUser.role === 'student' && sessionUser.id)
    ? sessionUser.id
    : 1;
  const targetEmail = (sessionUser && sessionUser.role === 'student' && sessionUser.email)
    ? sessionUser.email
    : '';

  if (sessionUser && sessionUser.name) {
    updateStudentProfileUI({
      id: sessionUser.id || targetStudentId,
      name: sessionUser.name,
      email: sessionUser.email || '',
      course: sessionUser.department || 'Data Structures'
    });
  }

  let overallScore = 0;
  let topicMastery = [];
  let weakTopicAlerts = [];
  let recommendations = [];
  let studyResources = [];

  if (window.EduNexusAPI && typeof window.EduNexusAPI.getStudentDashboard === 'function') {
    try {
      const res = await window.EduNexusAPI.getStudentDashboard(targetStudentId, targetEmail);
      if (res && res.success && res.data) {
        const apiData = res.data;
        activeStudentProfile = apiData.profile || {
          id: targetStudentId,
          name: (sessionUser && sessionUser.name) || 'Student',
          email: targetEmail,
          course: 'Data Structures'
        };

        updateStudentProfileUI(activeStudentProfile);

        window._verifiedStudentContext = {
          profile: activeStudentProfile,
          metrics: apiData.metrics || {},
          topic_scores: apiData.topic_scores || [],
          weak_topics: apiData.weak_topics || []
        };

        const metrics = apiData.metrics || {};
        overallScore = Number(metrics.overall_score || 0);
        const totalSubs = Number(metrics.total_submissions || 0);
        const completionRate = Number(metrics.completion_rate || 0);
        const evaluatedTopicsCount = Array.isArray(apiData.topic_scores) ? apiData.topic_scores.length : 0;
        const weakCount = Array.isArray(apiData.weak_topics) ? apiData.weak_topics.length : 0;

        const scoreCardElem = document.getElementById('studentStatOverallScore');
        if (scoreCardElem) {
          scoreCardElem.textContent = totalSubs > 0 ? `${overallScore}%` : 'N/A';
        }
        const scoreMetaElem = document.getElementById('studentStatScoreMeta');
        if (scoreMetaElem) {
          scoreMetaElem.innerHTML = totalSubs > 0
            ? `Across <strong>${totalSubs}</strong> graded submission(s)`
            : 'No assessment data available';
        }

        const courseCardElem = document.getElementById('studentStatEnrolledCourse');
        const courseMetaElem = document.getElementById('studentStatCourseMeta');
        const studentCourse = activeStudentProfile.course || '';
        if (courseCardElem) {
          courseCardElem.textContent = studentCourse ? studentCourse : 'No courses assigned yet';
        }
        if (courseMetaElem) {
          courseMetaElem.textContent = activeStudentProfile.email || 'Active student account';
        }

        const topicsCardElem = document.getElementById('studentStatTopicsTracked');
        const topicsMetaElem = document.getElementById('studentStatTopicsMeta');
        if (topicsCardElem) {
          topicsCardElem.textContent = String(evaluatedTopicsCount);
        }
        if (topicsMetaElem) {
          topicsMetaElem.innerHTML = evaluatedTopicsCount > 0
            ? `<span class="${weakCount > 0 ? 'trend-attention' : 'trend-positive'}">${weakCount} weak topic(s)</span> flagged`
            : 'No assessment data available';
        }

        const subCardElem = document.getElementById('studentStatSubmissions');
        if (subCardElem) {
          subCardElem.textContent = `${totalSubs} Recorded`;
        }
        const completionMetaElem = document.getElementById('studentStatCompletionMeta');
        if (completionMetaElem) {
          completionMetaElem.innerHTML = totalSubs > 0
            ? `<span class="trend-positive">${completionRate}%</span> on-time rate`
            : 'Submit an assignment below';
        }

        if (Array.isArray(apiData.topic_scores) && apiData.topic_scores.length > 0) {
          topicMastery = apiData.topic_scores.map(ts => {
            const sc = Number(ts.score || 0);
            let level = 'Needs Focus';
            let status = 'danger';
            if (sc >= 85) {
              level = 'Mastered';
              status = 'success';
            } else if (sc >= 70) {
              level = 'Proficient';
              status = 'info';
            } else if (sc >= 50) {
              level = 'Moderate';
              status = 'warning';
            }
            return {
              topic: ts.topic,
              score: sc,
              level,
              status
            };
          });
        }

        const badgeElem = document.getElementById('weakTopicsCountBadge');
        if (badgeElem) {
          badgeElem.textContent = `${weakCount} Detected`;
        }

        if (Array.isArray(apiData.weak_topics) && apiData.weak_topics.length > 0) {
          weakTopicAlerts = apiData.weak_topics.map((wt, idx) => {
            const matchingRec = (apiData.recommendations || []).find(r => r.topic === wt.topic);
            return {
              id: `alert_live_${idx}`,
              topic: wt.topic,
              score: `${wt.score}%`,
              severity: wt.score < 45 ? 'critical' : 'warning',
              message: Array.isArray(wt.evidence) && wt.evidence.length > 0
                ? wt.evidence.join(' · ')
                : wt.reason,
              recommendedAction: matchingRec
                ? matchingRec.recommended_action
                : `Review core ${wt.topic} exercises.`
            };
          });
        }

        if (Array.isArray(apiData.recommendations) && apiData.recommendations.length > 0) {
          recommendations = apiData.recommendations.map((rec, idx) => ({
            id: `rec_live_${idx}`,
            title: `${rec.topic}: ${rec.recommended_action}`,
            type: rec.resource || 'Guided Practice',
            duration: `Score: ${rec.score}%`,
            impact: `${rec.priority} Priority`
          }));
        }

        const recsCountBadge = document.getElementById('recsCountBadge');
        if (recsCountBadge) {
          recsCountBadge.textContent = `${recommendations.length} Actions`;
        }

        // Course Hub materials & announcements
        const hub = apiData.course_hub || {};
        renderStudentCourseHub(hub, activeStudentProfile.course);

        if (Array.isArray(hub.materials) && hub.materials.length > 0) {
          studyResources = hub.materials.map(m => ({
            id: `mat_${m.id}`,
            format: m.resource_type || 'Study Material',
            title: `${m.title} (${m.topic || m.course_code})`,
            readTime: m.uploaded_by || 'Faculty Resource',
            contentOrUrl: m.content_or_url || ''
          }));
        }

        // Populate Assignments dropdown & Submissions table
        renderStudentActivitiesSelect(apiData.assigned_activities || [], activeStudentProfile.id);
        renderStudentSubmissionsTable(apiData.recent_submissions || []);

        // Populate 1-to-1 Academic Support & Faculty Feedback
        renderStudentInterventions(apiData.interventions || [], apiData.assigned_activities || [], activeStudentProfile.id);
      }
    } catch (err) {
      if (window.showToast) {
        window.showToast('Unable to load live student profile from server.', 'error');
      }
    }
  }

  // Render Charts
  if (window.EduNexusCharts) {
    window.EduNexusCharts.renderScoreDonut('overallScoreDonut', overallScore, 'Cumulative Score');
    window.EduNexusCharts.renderMasteryList('topicMasteryContainer', topicMastery);
  }

  // Render Weak-Topic Alerts
  renderWeakTopicAlerts(weakTopicAlerts);

  // Render Learning Recommendations
  renderRecommendations(recommendations);

  // Render Study Resources
  renderStudyResources(studyResources);
}

function updateStudentProfileUI(profile) {
  if (!profile) return;
  const initials = getInitials(profile.name);
  const avatarElem = document.getElementById('studentSidebarAvatar');
  const nameElem = document.getElementById('studentSidebarName');
  const courseElem = document.getElementById('studentSidebarCourse');
  const subtitleElem = document.getElementById('studentTopbarSubtitle');
  const welcomeBubble = document.getElementById('assistantWelcomeBubble');

  if (avatarElem) avatarElem.textContent = initials;
  if (nameElem) nameElem.textContent = profile.name || 'Student';
  if (courseElem) courseElem.textContent = profile.course || 'No courses assigned yet';
  if (subtitleElem) {
    subtitleElem.textContent = `${profile.name || 'Student'} · ${profile.course || 'No courses assigned yet'}`;
  }
  if (welcomeBubble && profile.name) {
    const firstName = String(profile.name).trim().split(/\s+/)[0];
    welcomeBubble.textContent = `Hello ${firstName}! I am your EduNexus AI Academic Assistant. I analyze your real topic mastery data to provide tailored academic explanations and study strategies. How can I help you today?`;
  }
}

/**
 * Render Weak Topic Alerts List
 */
function renderWeakTopicAlerts(alerts) {
  const container = document.getElementById('weakAlertsContainer');
  if (!container) return;

  container.innerHTML = '';
  if (!Array.isArray(alerts) || alerts.length === 0) {
    container.innerHTML = '<div class="empty-state-box">No weak topics detected yet — submit an assessment to generate diagnostic alerts.</div>';
    return;
  }

  alerts.forEach(item => {
    const card = document.createElement('div');
    card.className = `weak-alert-card ${item.severity === 'warning' ? 'weak-alert-warning' : ''}`;

    card.innerHTML = `
      <svg class="weak-alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
        <line x1="12" y1="9" x2="12" y2="13"></line>
        <line x1="12" y1="17" x2="12.01" y2="17"></line>
      </svg>
      <div class="weak-alert-body">
        <div class="weak-alert-header">
          <span class="weak-alert-title">${escapeAssistantHtml(item.topic)}</span>
          <span class="weak-alert-score">${escapeAssistantHtml(item.score)}</span>
        </div>
        <p class="weak-alert-msg">${escapeAssistantHtml(item.message)}</p>
        <span class="weak-alert-action" role="button" tabindex="0" data-action="explore-topic" data-topic="${escapeAssistantHtml(item.topic)}">
          Suggested Action: ${escapeAssistantHtml(item.recommendedAction)}
        </span>
      </div>
    `;

    container.appendChild(card);
  });

  container.querySelectorAll('[data-action="explore-topic"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const topic = btn.getAttribute('data-topic');
      const chatInput = document.getElementById('chatInput');
      if (chatInput) {
        chatInput.value = `Can you explain ${topic} and help me review key concepts?`;
        chatInput.focus();
        window.showToast(`Selected "${topic}" for AI Study Assistant inquiry.`, 'info');
      }
    });
  });
}

/**
 * Render Evidence-based Learning Recommendations
 */
function renderRecommendations(recommendations) {
  const container = document.getElementById('recommendationsContainer');
  if (!container) return;

  container.innerHTML = '';
  if (!Array.isArray(recommendations) || recommendations.length === 0) {
    container.innerHTML = '<div class="empty-state-box">No assessment data available to generate personalized recommendations yet.</div>';
    return;
  }

  recommendations.forEach(rec => {
    const card = document.createElement('div');
    card.className = 'rec-card';

    card.innerHTML = `
      <div class="rec-main">
        <div class="rec-icon-box" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
        </div>
        <div class="rec-content">
          <h4 class="rec-title">${escapeAssistantHtml(rec.title)}</h4>
          <div class="rec-meta">
            <span>${escapeAssistantHtml(rec.type)}</span>
            <span>·</span>
            <span>${escapeAssistantHtml(rec.duration)}</span>
            <span class="rec-impact-badge">${escapeAssistantHtml(rec.impact)}</span>
          </div>
        </div>
      </div>
      <button type="button" class="action-pill-btn" data-rec-title="${escapeAssistantHtml(rec.title)}">
        Ask AI Tutor
      </button>
    `;

    container.appendChild(card);
  });

  container.querySelectorAll('[data-rec-title]').forEach(btn => {
    btn.addEventListener('click', () => {
      const title = btn.getAttribute('data-rec-title');
      const chatInput = document.getElementById('chatInput');
      if (chatInput) {
        chatInput.value = `Help me practice: ${title}`;
        chatInput.focus();
      }
      window.showToast('Loaded recommendation into AI Study Assistant.', 'info');
    });
  });
}

/**
 * Render Curated Study Resources
 */
function renderStudyResources(resources) {
  const container = document.getElementById('studyResourcesContainer');
  if (!container) return;

  container.innerHTML = '';
  if (!Array.isArray(resources) || resources.length === 0) {
    container.innerHTML = '<div class="empty-state-box" style="grid-column: 1 / -1;">No study materials uploaded for your course yet.</div>';
    return;
  }

  resources.forEach(res => {
    const card = document.createElement('div');
    card.className = 'resource-card';

    card.innerHTML = `
      <div>
        <div class="resource-header">
          <span class="resource-badge">${escapeAssistantHtml(res.format)}</span>
        </div>
        <h4 class="resource-title">${escapeAssistantHtml(res.title)}</h4>
        ${res.contentOrUrl ? `<p class="cell-sub" style="margin-top: 6px;">${escapeAssistantHtml(res.contentOrUrl)}</p>` : ''}
      </div>
      <div class="resource-footer">
        <span>${escapeAssistantHtml(res.readTime)}</span>
        <button type="button" class="action-pill-btn" data-res-title="${escapeAssistantHtml(res.title)}">
          Study Topic
        </button>
      </div>
    `;

    container.appendChild(card);
  });

  container.querySelectorAll('[data-res-title]').forEach(btn => {
    btn.addEventListener('click', () => {
      const title = btn.getAttribute('data-res-title');
      const chatInput = document.getElementById('chatInput');
      if (chatInput) {
        chatInput.value = `Summarize the key concepts in "${title}"`;
        chatInput.focus();
      }
      window.showToast('Loaded study resource into AI Study Assistant.', 'info');
    });
  });
}

/**
 * Priority 4: Render Unified Course Hub (Announcements & Materials)
 */
function renderStudentCourseHub(hub, studentCourse) {
  const badgeElem = document.getElementById('studentCourseHubBadge');
  if (badgeElem && studentCourse) {
    badgeElem.textContent = studentCourse;
  }

  const annContainer = document.getElementById('studentAnnouncementsContainer');
  if (annContainer) {
    annContainer.innerHTML = '';
    const announcements = Array.isArray(hub.announcements) ? hub.announcements : [];
    if (announcements.length === 0) {
      annContainer.innerHTML = '<div class="empty-state-box">No course announcements published yet.</div>';
    } else {
      announcements.forEach(ann => {
        const item = document.createElement('div');
        item.className = 'rec-card';
        const dateStr = ann.created_at ? new Date(ann.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Recent';
        item.innerHTML = `
          <div class="rec-main">
            <div class="rec-content">
              <h4 class="rec-title">${escapeAssistantHtml(ann.title)}</h4>
              <p class="weak-alert-msg" style="margin-bottom: 4px;">${escapeAssistantHtml(ann.message)}</p>
              <div class="rec-meta">
                <span>${escapeAssistantHtml(ann.course_code || 'CS-301')}</span>
                <span>·</span>
                <span>${escapeAssistantHtml(ann.published_by || 'Faculty')}</span>
                <span>·</span>
                <span>${escapeAssistantHtml(dateStr)}</span>
              </div>
            </div>
          </div>
          <span class="badge ${ann.priority === 'urgent' ? 'badge-demo' : 'badge-info'}">${escapeAssistantHtml(ann.priority || 'normal')}</span>
        `;
        annContainer.appendChild(item);
      });
    }
  }

  const matContainer = document.getElementById('studentCourseMaterialsContainer');
  if (matContainer) {
    matContainer.innerHTML = '';
    const materials = Array.isArray(hub.materials) ? hub.materials : [];
    if (materials.length === 0) {
      matContainer.innerHTML = '<div class="empty-state-box">No faculty study materials published yet.</div>';
    } else {
      materials.forEach(mat => {
        const item = document.createElement('div');
        item.className = 'rec-card';
        item.innerHTML = `
          <div class="rec-main">
            <div class="rec-content">
              <h4 class="rec-title">${escapeAssistantHtml(mat.title)}</h4>
              <p class="weak-alert-msg" style="margin-bottom: 4px;">${escapeAssistantHtml(mat.content_or_url || '')}</p>
              <div class="rec-meta">
                <span>Topic: ${escapeAssistantHtml(mat.topic || 'General')}</span>
                <span>·</span>
                <span>${escapeAssistantHtml(mat.uploaded_by || 'Faculty')}</span>
              </div>
            </div>
          </div>
          <span class="badge badge-info">${escapeAssistantHtml(mat.resource_type || 'Notes')}</span>
        `;
        matContainer.appendChild(item);
      });
    }
  }
}

/**
 * Priority 4: Populate Assignments Select & Submissions Table
 */
function renderStudentActivitiesSelect(activities, currentStudentId) {
  const selectElem = document.getElementById('studentActivitySelect');
  if (!selectElem) return;

  selectElem.innerHTML = '';
  if (!Array.isArray(activities) || activities.length === 0) {
    selectElem.innerHTML = '<option value="">No assignments available yet</option>';
    return;
  }

  activities.forEach(act => {
    const opt = document.createElement('option');
    opt.value = String(act.id);
    const isTargeted = act.assigned_student_id && Number(act.assigned_student_id) === Number(currentStudentId);
    const prefix = isTargeted ? '[Targeted Practice] ' : '';
    const dueText = act.due_date ? ` · Due: ${act.due_date}` : '';
    opt.textContent = `${prefix}${act.title} (${act.topic} · Max ${act.max_score} pts${dueText})`;
    selectElem.appendChild(opt);
  });
}

function renderStudentSubmissionsTable(submissions) {
  const tbody = document.getElementById('studentSubmissionsTableBody');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (!Array.isArray(submissions) || submissions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="table-empty-cell">No submissions recorded yet. Submit an assignment above to track your marks and feedback.</td>
      </tr>
    `;
    return;
  }

  submissions.forEach(sub => {
    const tr = document.createElement('tr');
    const status = String(sub.status || 'submitted');
    const isEvaluated = status === 'evaluated' || Boolean(sub.evaluated_by);
    const dateStr = sub.submitted_at
      ? new Date(sub.submitted_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
      : 'Recorded';

    const scoreDisplay = (status === 'pending_review' && Number(sub.score || 0) === 0)
      ? 'Pending Grading'
      : `${sub.score} / ${sub.max_score || 100}`;

    const feedbackHtml = sub.feedback
      ? `<strong>Faculty Feedback (${escapeAssistantHtml(sub.evaluated_by || 'Instructor')}):</strong> ${escapeAssistantHtml(sub.feedback)}`
      : (sub.response_text ? `<em>Submitted response:</em> ${escapeAssistantHtml(sub.response_text)}` : 'Awaiting instructor feedback');

    tr.innerHTML = `
      <td><strong>${escapeAssistantHtml(sub.activity_title || `Activity #${sub.activity_id}`)}</strong></td>
      <td>${escapeAssistantHtml(sub.topic || 'General')}</td>
      <td>
        <span class="badge ${isEvaluated ? 'badge-info' : 'badge-demo'}">
          ${escapeAssistantHtml(status)}
        </span>
      </td>
      <td><strong>${escapeAssistantHtml(scoreDisplay)}</strong></td>
      <td><div class="cell-body">${feedbackHtml}</div></td>
      <td><span class="cell-sub">${escapeAssistantHtml(dateStr)}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function initStudentSubmissionForm() {
  const form = document.getElementById('studentSubmitAssignmentForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const selectElem = document.getElementById('studentActivitySelect');
    const scoreInput = document.getElementById('studentSelfScoreInput');
    const responseInput = document.getElementById('studentResponseTextInput');
    const submitBtn = document.getElementById('studentSubmitActivityBtn');

    const activityId = selectElem ? Number(selectElem.value) : 0;
    const responseText = responseInput ? responseInput.value.trim() : '';
    const rawScore = scoreInput && scoreInput.value !== '' ? Number(scoreInput.value) : null;

    if (!activityId) {
      window.showToast('Please select an assignment to submit.', 'error');
      return;
    }
    if (!responseText && rawScore === null) {
      window.showToast('Please enter your assignment response or score.', 'error');
      return;
    }

    const studentId = (activeStudentProfile && activeStudentProfile.id) ? activeStudentProfile.id : 1;
    const payload = {
      student_id: studentId,
      activity_id: activityId,
      response_text: responseText
    };
    if (rawScore !== null && !Number.isNaN(rawScore)) {
      payload.score = rawScore;
      payload.status = 'submitted';
    } else {
      payload.status = 'pending_review';
    }

    if (submitBtn) submitBtn.disabled = true;
    try {
      const res = await window.EduNexusAPI.submitActivity(payload);
      if (res && res.success) {
        window.showToast('Assignment submitted and saved to database!', 'success');
        if (responseInput) responseInput.value = '';
        if (scoreInput) scoreInput.value = '';
        await initStudentDashboard();
      }
    } catch (err) {
      window.showToast(err.message || 'Failed to submit assignment.', 'error');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

/**
 * Priority 3: Render & Submit 1-to-1 Academic Support / Faculty Feedback
 */
function renderStudentInterventions(interventions, assignedActivities, currentStudentId) {
  const container = document.getElementById('studentInterventionsList');
  if (!container) return;

  container.innerHTML = '';

  const targetedActivities = (assignedActivities || []).filter(
    a => a.assigned_student_id && Number(a.assigned_student_id) === Number(currentStudentId)
  );

  if ((!Array.isArray(interventions) || interventions.length === 0) && targetedActivities.length === 0) {
    container.innerHTML = '<div class="empty-state-box">No faculty feedback or 1-to-1 support requests yet. Use the form above to request office hours or topic clarification.</div>';
    return;
  }

  targetedActivities.forEach(act => {
    const card = document.createElement('div');
    card.className = 'rec-card';
    card.innerHTML = `
      <div class="rec-main">
        <div class="rec-content">
          <h4 class="rec-title">[Targeted Practice Assigned] ${escapeAssistantHtml(act.title)}</h4>
          <p class="weak-alert-msg" style="margin-bottom: 4px;">${escapeAssistantHtml(act.instructions || 'Complete this targeted practice activity in the Assignments section above.')}</p>
          <div class="rec-meta">
            <span>Topic: ${escapeAssistantHtml(act.topic || 'General')}</span>
            <span>·</span>
            <span>Assigned by ${escapeAssistantHtml(act.created_by_faculty || 'Faculty')}</span>
            ${act.due_date ? `<span>· Due: ${escapeAssistantHtml(act.due_date)}</span>` : ''}
          </div>
        </div>
      </div>
      <span class="badge badge-info">Remedial Activity</span>
    `;
    container.appendChild(card);
  });

  (interventions || []).forEach(item => {
    const card = document.createElement('div');
    card.className = 'rec-card';
    const status = String(item.status || 'open');
    const isResolved = status === 'resolved' || status === 'responded' || status === 'scheduled';
    const responseHtml = item.faculty_response
      ? `<div style="margin-top: 6px; padding: 8px 10px; background: #EFF6FF; border-radius: 6px; font-size: 0.8rem; color: #1E3A8A;">
           <strong>Faculty Response (${escapeAssistantHtml(item.faculty_name || 'Instructor')}):</strong> ${escapeAssistantHtml(item.faculty_response)}
         </div>`
      : '';

    card.innerHTML = `
      <div class="rec-main">
        <div class="rec-content">
          <h4 class="rec-title">${escapeAssistantHtml(item.title)}</h4>
          <p class="weak-alert-msg" style="margin-bottom: 4px;">${escapeAssistantHtml(item.details || '')}</p>
          <div class="rec-meta">
            <span>Topic: ${escapeAssistantHtml(item.topic || 'General')}</span>
            <span>·</span>
            <span>Initiated by: ${escapeAssistantHtml(item.initiated_by || 'student')}</span>
            <span>·</span>
            <span>Type: ${escapeAssistantHtml(item.intervention_type || 'help_request')}</span>
          </div>
          ${responseHtml}
        </div>
      </div>
      <span class="badge ${isResolved ? 'badge-info' : 'badge-demo'}">${escapeAssistantHtml(status)}</span>
    `;
    container.appendChild(card);
  });
}

function initStudentHelpRequestForm() {
  const form = document.getElementById('studentHelpRequestForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const typeSelect = document.getElementById('helpRequestType');
    const topicInput = document.getElementById('helpRequestTopic');
    const detailsInput = document.getElementById('helpRequestDetails');
    const submitBtn = document.getElementById('studentHelpRequestBtn');

    const interventionType = typeSelect ? typeSelect.value : 'help_request';
    const topic = topicInput ? topicInput.value.trim() : '';
    const details = detailsInput ? detailsInput.value.trim() : '';

    if (!topic || !details) {
      window.showToast('Please enter both the topic and details for your support request.', 'error');
      return;
    }

    const studentId = (activeStudentProfile && activeStudentProfile.id) ? activeStudentProfile.id : 1;
    const studentName = (activeStudentProfile && activeStudentProfile.name) ? activeStudentProfile.name : 'Student';
    const courseCode = (activeStudentProfile && activeStudentProfile.course) ? activeStudentProfile.course : 'CS-301';

    const title = interventionType === 'office_hours'
      ? `1-to-1 Office Hours Request: ${topic}`
      : `Academic Help Request: ${topic}`;

    if (submitBtn) submitBtn.disabled = true;
    try {
      const res = await window.EduNexusAPI.createIntervention({
        student_id: studentId,
        student_name: studentName,
        course_code: courseCode,
        topic,
        intervention_type: interventionType,
        initiated_by: 'student',
        title,
        details
      });
      if (res && res.success) {
        window.showToast('Support request sent to faculty and saved to database!', 'success');
        if (topicInput) topicInput.value = '';
        if (detailsInput) detailsInput.value = '';
        await initStudentDashboard();
      }
    } catch (err) {
      window.showToast(err.message || 'Failed to submit support request.', 'error');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

/**
 * Escape HTML special characters before formatting code blocks
 */
function escapeAssistantHtml(raw) {
  return String(raw || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Format multiline text, fenced code blocks (```...```), inline code (`...`), and bold text (**...**) safely
 */
function formatAssistantMessageHtml(text) {
  const escaped = escapeAssistantHtml(text);
  const codeBlocks = [];

  let processed = escaped.replace(/```([a-zA-Z0-9_+-]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const token = `__CODE_BLOCK_${codeBlocks.length}__`;
    const trimmedCode = code.replace(/\n$/, '');
    codeBlocks.push(`<pre class="chat-code-block"><code>${trimmedCode}</code></pre>`);
    return token;
  });

  processed = processed.replace(/`([^`\n]+)`/g, '<code class="chat-inline-code">$1</code>');
  processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  codeBlocks.forEach((blockHtml, idx) => {
    processed = processed.replace(`__CODE_BLOCK_${idx}__`, blockHtml);
  });

  return processed;
}

/**
 * AI Study Assistant UI & Live Google Gemini Integration
 */
function initAIAssistant() {
  const data = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.student && window.EDUNEXUS_MOCK_DATA.student.aiAssistantKnowledge;
  const suggestedPrompts = (data && Array.isArray(data.suggestedPrompts)) ? data.suggestedPrompts : [
    "Explain Dijkstra's shortest path algorithm step-by-step",
    "How do I determine if a database schema is in BCNF?",
    "What are my weakest topics and how do I improve them?",
    "Give me a quick 3-question quiz on Graph Traversal"
  ];

  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chipsContainer = document.getElementById('promptChipsContainer');
  const sendBtn = chatForm ? chatForm.querySelector('button[type="submit"]') : null;

  if (!chatMessages || !chatForm || !chatInput) return;

  let isRequestPending = false;
  const conversationHistory = [];
  let previousInteractionId = null;

  if (chipsContainer && suggestedPrompts.length > 0) {
    chipsContainer.innerHTML = '';
    const label = document.createElement('span');
    label.className = 'chip-label';
    label.textContent = 'Prompt Suggestions:';
    chipsContainer.appendChild(label);

    suggestedPrompts.forEach(promptText => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'prompt-chip';
      chip.textContent = promptText;
      chip.addEventListener('click', () => {
        if (isRequestPending) return;
        handleUserMessage(promptText);
      });
      chipsContainer.appendChild(chip);
    });
  }

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    if (isRequestPending) return;
    const text = chatInput.value.trim();
    if (!text) {
      if (window.showToast) {
        window.showToast('Please enter a question before sending.', 'info');
      }
      return;
    }
    chatInput.value = '';
    handleUserMessage(text);
  });

  function setPendingState(pending) {
    isRequestPending = pending;
    chatInput.disabled = pending;
    if (sendBtn) {
      sendBtn.disabled = pending;
      sendBtn.setAttribute('aria-disabled', pending ? 'true' : 'false');
      sendBtn.textContent = pending ? 'Sending...' : 'Send';
    }
    if (chipsContainer) {
      chipsContainer.querySelectorAll('.prompt-chip').forEach(chip => {
        chip.disabled = pending;
      });
    }
  }

  function appendLoadingIndicator() {
    const msg = document.createElement('div');
    msg.className = 'chat-message chat-assistant chat-loading-message';
    msg.setAttribute('aria-label', 'AI Study Assistant is generating a response');

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble-loading';
    bubble.innerHTML = '<span class="chat-loading-dot"></span><span>Generating response with Gemini...</span>';

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msg;
  }

  function appendMessage(sender, text, isError = false) {
    const msg = document.createElement('div');
    msg.className = `chat-message chat-${sender === 'user' ? 'user' : 'assistant'}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = sender === 'user'
      ? (activeStudentProfile ? getInitials(activeStudentProfile.name) : 'ST')
      : 'AI';

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble${isError ? ' chat-bubble-error' : ''}`;

    if (sender === 'user' || isError) {
      bubble.textContent = text;
    } else {
      bubble.innerHTML = formatAssistantMessageHtml(text);
    }

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  async function handleUserMessage(userText) {
    if (isRequestPending) return;

    appendMessage('user', userText);
    setPendingState(true);
    const loadingElem = appendLoadingIndicator();

    try {
      if (!window.EduNexusAPI || typeof window.EduNexusAPI.sendStudyAssistantMessage !== 'function') {
        throw new Error('AI Study Assistant API client is not initialized.');
      }

      const response = await window.EduNexusAPI.sendStudyAssistantMessage({
        message: userText,
        history: conversationHistory.slice(-8),
        previous_interaction_id: previousInteractionId,
        student_context: window._verifiedStudentContext || null,
        student_id: window._verifiedStudentContext ? null : (activeStudentProfile ? activeStudentProfile.id : 1)
      });

      const replyText = response && response.data && response.data.reply;
      if (!replyText) {
        throw new Error('The AI Study Assistant returned an empty response. Please try again.');
      }

      if (loadingElem && loadingElem.parentNode) {
        loadingElem.parentNode.removeChild(loadingElem);
      }

      appendMessage('assistant', replyText);

      conversationHistory.push({ role: 'user', content: userText });
      conversationHistory.push({ role: 'assistant', content: replyText });
      if (response.data.interaction_id) {
        previousInteractionId = response.data.interaction_id;
      }
    } catch (err) {
      if (loadingElem && loadingElem.parentNode) {
        loadingElem.parentNode.removeChild(loadingElem);
      }
      if (!chatInput.value.trim()) {
        chatInput.value = userText;
      }
      const friendlyError = (err && err.message)
        ? err.message
        : 'Unable to generate a response from Google Gemini right now. Please try again.';
      appendMessage('assistant', friendlyError, true);
      if (window.showToast) {
        window.showToast(friendlyError, 'error');
      }
    } finally {
      setPendingState(false);
      chatInput.focus();
    }
  }
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
      window.showToast("Logged out of session. Redirecting to sign-in...", "info");
      setTimeout(() => {
        window.location.href = '/login';
      }, 500);
    });
  });
}
