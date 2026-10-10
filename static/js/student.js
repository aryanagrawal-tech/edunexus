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
 * Initialize Student Metrics and Content from Flask Backend with Fallback
 */
async function initStudentDashboard() {
  const fallbackData = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.student;

  let overallScore = fallbackData ? fallbackData.metrics.overallScore : 0;
  let topicMastery = fallbackData ? fallbackData.topicMastery : [];
  let weakTopicAlerts = fallbackData ? fallbackData.weakTopicAlerts : [];
  let recommendations = fallbackData ? fallbackData.recommendations : [];
  const studyResources = fallbackData ? fallbackData.studyResources : [];

  // Attempt to load live student performance and analytics from Flask + Supabase backend
  if (window.EduNexusAPI && typeof window.EduNexusAPI.getStudentDashboard === 'function') {
    try {
      const res = await window.EduNexusAPI.getStudentDashboard(1);
      if (res && res.success && res.data && res.data.metrics) {
        const apiData = res.data;
        window._verifiedStudentContext = {
          profile: apiData.profile,
          metrics: apiData.metrics,
          topic_scores: apiData.topic_scores,
          weak_topics: apiData.weak_topics
        };
        overallScore = apiData.metrics.overall_score;

        const scoreCardElem = document.getElementById('studentStatOverallScore');
        if (scoreCardElem) {
          scoreCardElem.textContent = `${overallScore}%`;
        }

        const subCardElem = document.getElementById('studentStatSubmissions');
        if (subCardElem && typeof apiData.metrics.total_submissions === 'number') {
          subCardElem.textContent = `${apiData.metrics.total_submissions} Recorded`;
        }

        const completionMetaElem = document.getElementById('studentStatCompletionMeta');
        if (completionMetaElem && typeof apiData.metrics.completion_rate === 'number') {
          completionMetaElem.innerHTML = `<span class="trend-positive">${apiData.metrics.completion_rate}%</span> on-time rate`;
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

        if (Array.isArray(apiData.weak_topics)) {
          const badgeElem = document.getElementById('weakTopicsCountBadge');
          if (badgeElem) {
            badgeElem.textContent = `${apiData.weak_topics.length} Detected`;
          }
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
      }
    } catch (err) {
      // Fall back to client-side dataset if backend request fails
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
      window.showToast("Opening recommended learning module...", "success");
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
      window.showToast("Opening study resource...", "info");
    });
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

  // Extract fenced code blocks first so inline formatting doesn't alter code
  let processed = escaped.replace(/```([a-zA-Z0-9_+-]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const token = `__CODE_BLOCK_${codeBlocks.length}__`;
    const trimmedCode = code.replace(/\n$/, '');
    codeBlocks.push(`<pre class="chat-code-block"><code>${trimmedCode}</code></pre>`);
    return token;
  });

  // Inline code (`...`)
  processed = processed.replace(/`([^`\n]+)`/g, '<code class="chat-inline-code">$1</code>');

  // Bold (**...**)
  processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Restore fenced code blocks
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

  // Render Prompt Chips
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

  // Handle Form Submission (Send button and Enter key)
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
    avatar.textContent = sender === 'user' ? 'AA' : 'AI';

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
        student_id: window._verifiedStudentContext ? null : 1
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
      // Preserve the user's message in the input box so they can retry without typing it again
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
