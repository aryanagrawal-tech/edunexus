/**
 * EduNexus AI - Student Dashboard Controller (Vanilla JS)
 * Coordinates student analytics, topic mastery, alerts, recommendations, and AI Assistant UI.
 */

document.addEventListener('DOMContentLoaded', () => {
  initStudentDashboard();
  initSidebarToggle();
  initRoleSwitcher();
  initAIAssistant();
});

/**
 * Initialize Student Metrics and Content from Mock Data Store
 */
function initStudentDashboard() {
  const data = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.student;
  if (!data) return;

  // Render Charts
  if (window.EduNexusCharts) {
    window.EduNexusCharts.renderScoreDonut('overallScoreDonut', data.metrics.overallScore, 'Cumulative Score');
    window.EduNexusCharts.renderMasteryList('topicMasteryContainer', data.topicMastery);
  }

  // Render Weak-Topic Alerts
  renderWeakTopicAlerts(data.weakTopicAlerts);

  // Render Learning Recommendations
  renderRecommendations(data.recommendations);

  // Render Study Resources
  renderStudyResources(data.studyResources);
}

/**
 * Render Weak Topic Alerts List
 */
function renderWeakTopicAlerts(alerts) {
  const container = document.getElementById('weakAlertsContainer');
  if (!container || !alerts) return;

  container.innerHTML = '';
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
          <span class="weak-alert-title">${item.topic}</span>
          <span class="weak-alert-score">${item.score}</span>
        </div>
        <p class="weak-alert-msg">${item.message}</p>
        <span class="weak-alert-action" role="button" tabindex="0" data-action="explore-topic" data-topic="${item.topic}">
          Suggested Action: ${item.recommendedAction}
        </span>
      </div>
    `;

    container.appendChild(card);
  });

  // Attach click listener for alert actions
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
  if (!container || !recommendations) return;

  container.innerHTML = '';
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
          <h4 class="rec-title">${rec.title}</h4>
          <div class="rec-meta">
            <span>${rec.type}</span>
            <span>·</span>
            <span>${rec.duration}</span>
            <span class="rec-impact-badge">${rec.impact}</span>
          </div>
        </div>
      </div>
      <button type="button" class="action-pill-btn" data-rec-id="${rec.id}">
        Start Module
      </button>
    `;

    container.appendChild(card);
  });

  container.querySelectorAll('[data-rec-id]').forEach(btn => {
    btn.addEventListener('click', () => {
      window.showToast("Module launch simulated in demo mode.", "success");
    });
  });
}

/**
 * Render Curated Study Resources
 */
function renderStudyResources(resources) {
  const container = document.getElementById('studyResourcesContainer');
  if (!container || !resources) return;

  container.innerHTML = '';
  resources.forEach(res => {
    const card = document.createElement('div');
    card.className = 'resource-card';

    card.innerHTML = `
      <div>
        <div class="resource-header">
          <span class="resource-badge">${res.format}</span>
        </div>
        <h4 class="resource-title">${res.title}</h4>
      </div>
      <div class="resource-footer">
        <span>${res.readTime}</span>
        <button type="button" class="action-pill-btn" data-res-id="${res.id}">
          Open Resource
        </button>
      </div>
    `;

    container.appendChild(card);
  });

  container.querySelectorAll('[data-res-id]').forEach(btn => {
    btn.addEventListener('click', () => {
      window.showToast("Study resource viewer opened in demo preview.", "info");
    });
  });
}

/**
 * AI Study Assistant UI & Interactive Responses (Simulated)
 */
function initAIAssistant() {
  const data = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.student.aiAssistantKnowledge;
  if (!data) return;

  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chipsContainer = document.getElementById('promptChipsContainer');

  if (!chatMessages || !chatForm || !chatInput) return;

  // Render Prompt Chips
  if (chipsContainer && data.suggestedPrompts) {
    chipsContainer.innerHTML = '';
    const label = document.createElement('span');
    label.className = 'chip-label';
    label.textContent = 'Prompt Suggestions:';
    chipsContainer.appendChild(label);

    data.suggestedPrompts.forEach(promptText => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'prompt-chip';
      chip.textContent = promptText;
      chip.addEventListener('click', () => {
        handleUserMessage(promptText);
      });
      chipsContainer.appendChild(chip);
    });
  }

  // Handle Form Submission
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    chatInput.value = '';
    handleUserMessage(text);
  });

  function handleUserMessage(userText) {
    appendMessage('user', userText);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Simulate AI typing delay
    setTimeout(() => {
      const response = generateAIResponse(userText, data.responses);
      appendMessage('assistant', response);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 450);
  }

  function appendMessage(sender, text) {
    const msg = document.createElement('div');
    msg.className = `chat-message chat-${sender}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = sender === 'user' ? 'AA' : 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.textContent = text;

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    chatMessages.appendChild(msg);
  }

  function generateAIResponse(query, knowledge) {
    const q = query.toLowerCase();
    if (q.includes('dijkstra') || q.includes('shortest path') || q.includes('graph')) {
      return knowledge.dijkstra;
    } else if (q.includes('bcnf') || q.includes('normal') || q.includes('database')) {
      return knowledge.bcnf;
    } else if (q.includes('weak') || q.includes('improve') || q.includes('score')) {
      return knowledge.weakest;
    } else if (q.includes('quiz') || q.includes('question') || q.includes('test')) {
      return knowledge.quiz;
    }
    return `Regarding "${query}":\n\nI recommend reviewing the lecture slides and practicing with the interactive exercises in your recommendations tab. Would you like me to generate a 3-question practice drill on this topic?`;
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
        window.location.href = 'student-dashboard.html';
      } else if (targetRole === 'faculty') {
        window.location.href = 'faculty-dashboard.html';
      } else if (targetRole === 'admin') {
        window.location.href = 'admin-dashboard.html';
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
        window.location.href = 'login.html';
      }, 500);
    });
  });
}
