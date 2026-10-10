/**
 * EduNexus AI - Lightweight Pure SVG & HTML Chart Renderers
 * Zero external dependencies. Fully responsive and accessible.
 */

const EduNexusCharts = {
  /**
   * Render Topic Mastery Progress Bars
   * @param {string} containerId - Target element ID
   * @param {Array<{topic: string, score: number, level: string, status: string}>} topics
   */
  renderMasteryList(containerId, topics) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';
    const listWrap = document.createElement('div');
    listWrap.className = 'mastery-list';

    topics.forEach(item => {
      let tagClass = 'mastery-tag-info';
      let fillClass = 'fill-info';

      if (item.status === 'success') {
        tagClass = 'mastery-tag-success';
        fillClass = 'fill-success';
      } else if (item.status === 'warning') {
        tagClass = 'mastery-tag-warning';
        fillClass = 'fill-warning';
      } else if (item.status === 'danger') {
        tagClass = 'mastery-tag-danger';
        fillClass = 'fill-danger';
      }

      const itemWrap = document.createElement('div');
      itemWrap.className = 'mastery-item';

      const meta = document.createElement('div');
      meta.className = 'mastery-meta';

      const title = document.createElement('span');
      title.className = 'mastery-title';
      title.textContent = item.topic;

      const tag = document.createElement('span');
      tag.className = `mastery-score-tag ${tagClass}`;
      tag.textContent = `${item.score}% · ${item.level}`;

      meta.appendChild(title);
      meta.appendChild(tag);

      const track = document.createElement('div');
      track.className = 'progress-track';
      track.setAttribute('role', 'progressbar');
      track.setAttribute('aria-valuenow', String(item.score));
      track.setAttribute('aria-valuemin', '0');
      track.setAttribute('aria-valuemax', '100');
      track.setAttribute('aria-label', `${item.topic} score`);

      const fill = document.createElement('div');
      fill.className = `progress-fill ${fillClass}`;
      fill.style.width = `${item.score}%`;

      track.appendChild(fill);
      itemWrap.appendChild(meta);
      itemWrap.appendChild(track);
      listWrap.appendChild(itemWrap);
    });

    container.appendChild(listWrap);
  },

  /**
   * Render Donut / Radial Score Gauge in SVG
   * @param {string} containerId
   * @param {number} score - Percentage score (0 - 100)
   * @param {string} label - e.g. "Overall Score"
   */
  renderScoreDonut(containerId, score, label = "Cumulative Mastery") {
    const container = document.getElementById(containerId);
    if (!container) return;

    const radius = 64;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    const svg = `
      <svg class="chart-svg" viewBox="0 0 160 160" width="160" height="160" role="img" aria-label="${label}: ${score}%">
        <circle cx="80" cy="80" r="${radius}" fill="none" stroke="#E2E8F0" stroke-width="14" />
        <circle 
          cx="80" 
          cy="80" 
          r="${radius}" 
          fill="none" 
          stroke="#2563EB" 
          stroke-width="14" 
          stroke-linecap="round"
          stroke-dasharray="${circumference}" 
          stroke-dashoffset="${offset}"
          transform="rotate(-90 80 80)"
        />
        <text x="80" y="76" text-anchor="middle" font-size="22" font-weight="700" fill="#0F172A">${score}%</text>
        <text x="80" y="96" text-anchor="middle" font-size="10" font-weight="500" fill="#64748B">${label}</text>
      </svg>
    `;
    container.innerHTML = svg;
  },

  /**
   * Render Class Performance Comparative Bar Chart in SVG
   * @param {string} containerId
   * @param {Array<{topic: string, avgScore: number, benchmark: number}>} data
   */
  renderComparativeBarChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const width = 500;
    const height = 240;
    const padding = { top: 25, right: 20, bottom: 45, left: 45 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const barWidth = 28;
    const gap = (chartWidth - (data.length * barWidth)) / (data.length + 1);

    let barsHtml = '';
    let labelsHtml = '';

    // Draw horizontal reference lines (0, 25, 50, 75, 100)
    let gridLinesHtml = '';
    [25, 50, 75, 100].forEach(val => {
      const y = padding.top + chartHeight - (val / 100 * chartHeight);
      gridLinesHtml += `
        <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" class="chart-grid-line" />
        <text x="${padding.left - 8}" y="${y + 4}" text-anchor="end" class="chart-label">${val}%</text>
      `;
    });

    data.forEach((d, i) => {
      const x = padding.left + gap + i * (barWidth + gap);
      const barH = (d.avgScore / 100) * chartHeight;
      const y = padding.top + chartHeight - barH;

      let fillColor = '#2563EB'; // primary
      if (d.avgScore < 60) fillColor = '#DC2626'; // low
      else if (d.avgScore < 75) fillColor = '#D97706'; // warning

      barsHtml += `
        <rect 
          x="${x}" 
          y="${y}" 
          width="${barWidth}" 
          height="${barH}" 
          rx="4" 
          fill="${fillColor}" 
          class="chart-bar"
        >
          <title>${d.topic}: ${d.avgScore}%</title>
        </rect>
        <text x="${x + barWidth / 2}" y="${y - 6}" text-anchor="middle" class="chart-value">${d.avgScore}%</text>
      `;

      // Abbreviate label for mobile/space
      const shortLabel = d.topic.length > 12 ? d.topic.slice(0, 10) + '…' : d.topic;
      labelsHtml += `
        <text x="${x + barWidth / 2}" y="${height - padding.bottom + 18}" text-anchor="middle" class="chart-label">
          ${shortLabel}
        </text>
      `;
    });

    const svg = `
      <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Class Topic Mastery Distribution Chart">
        ${gridLinesHtml}
        ${barsHtml}
        ${labelsHtml}
      </svg>
    `;

    container.innerHTML = svg;
  }
};

window.EduNexusCharts = EduNexusCharts;
