/**
 * EduNexus AI - Admin Dashboard Controller (Vanilla JS)
 * Coordinates institutional platform metrics, user directory filtering,
 * account status management, and audit log inspection.
 */

document.addEventListener('DOMContentLoaded', () => {
  initAdminDashboard();
  initSidebarToggle();
  initRoleSwitcher();
  initUserFilters();
  initAddUserModal();
});

let currentUsersList = [];

/**
 * Initialize Admin Metrics and User Directory
 */
async function initAdminDashboard() {
  const data = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.admin;
  if (!data) return;

  currentUsersList = [...data.usersDirectory];

  // Merge live students from Flask + Supabase backend into directory
  if (window.EduNexusAPI && typeof window.EduNexusAPI.getStudents === 'function') {
    try {
      const stdRes = await window.EduNexusAPI.getStudents();
      if (stdRes && stdRes.success && Array.isArray(stdRes.data) && stdRes.data.length > 0) {
        const existingEmails = new Set(currentUsersList.map(u => u.email.toLowerCase()));
        const dbStudentRows = stdRes.data
          .filter(s => s.email && !existingEmails.has(s.email.toLowerCase()))
          .map(s => ({
            id: `db_std_${s.id}`,
            name: s.name,
            email: s.email,
            role: 'Student',
            department: s.course || 'Data Structures',
            status: 'Active',
            joined: s.created_at ? new Date(s.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'Enrolled'
          }));
        currentUsersList = [...dbStudentRows, ...currentUsersList];
      }
    } catch (err) {
      // Keep local directory if request fails
    }
  }

  renderUsersTable(currentUsersList);
  renderAuditLogs(data.systemAuditLogs);
}

/**
 * Render Users Directory Table
 */
function renderUsersTable(users) {
  const tbody = document.getElementById('usersTableBody');
  const countElem = document.getElementById('usersCountDisplay');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (countElem) {
    countElem.textContent = `Showing ${users.length} accounts`;
  }

  if (users.length === 0) {
    const emptyRow = document.createElement('tr');
    emptyRow.innerHTML = `
      <td colspan="6" class="table-empty-cell">
        No user accounts match the current filter criteria.
      </td>
    `;
    tbody.appendChild(emptyRow);
    return;
  }

  users.forEach(user => {
    const tr = document.createElement('tr');

    let roleBadgeClass = 'badge-student';
    if (user.role === 'Faculty') roleBadgeClass = 'badge-faculty';
    else if (user.role === 'Admin') roleBadgeClass = 'badge-demo';

    const isActive = user.status === 'Active';

    tr.innerHTML = `
      <td>
        <div class="cell-title">${user.name}</div>
        <div class="cell-sub">${user.email}</div>
      </td>
      <td>
        <span class="badge ${roleBadgeClass}">${user.role}</span>
      </td>
      <td>${user.department}</td>
      <td>
        <span class="badge ${isActive ? 'badge-info' : 'badge-demo'}">
          ${user.status}
        </span>
      </td>
      <td>
        <span class="cell-sub">${user.joined}</span>
      </td>
      <td>
        <button 
          type="button" 
          class="action-pill-btn" 
          data-action="toggle-status"
          data-user-id="${user.id}"
          data-user-name="${user.name}"
          data-current-status="${user.status}"
        >
          ${isActive ? 'Suspend' : 'Activate'}
        </button>
      </td>
    `;

    tbody.appendChild(tr);
  });

  // Attach status toggle listeners
  tbody.querySelectorAll('[data-action="toggle-status"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const userId = btn.getAttribute('data-user-id');
      const userName = btn.getAttribute('data-user-name');
      const currentStatus = btn.getAttribute('data-current-status');
      toggleUserStatus(userId, userName, currentStatus);
    });
  });
}

/**
 * Toggle User Account Status
 */
function toggleUserStatus(userId, userName, currentStatus) {
  const newStatus = currentStatus === 'Active' ? 'Suspended' : 'Active';

  // Update in local array
  currentUsersList = currentUsersList.map(u => {
    if (u.id === userId) {
      return { ...u, status: newStatus };
    }
    return u;
  });

  applyFilters();

  window.showToast(
    `Account status for ${userName} updated to "${newStatus}".`,
    newStatus === 'Active' ? 'success' : 'info'
  );
}

/**
 * Filter Users by Search Term, Role, and Status
 */
function initUserFilters() {
  const searchInput = document.getElementById('userSearchInput');
  const roleSelect = document.getElementById('userRoleFilter');
  const statusSelect = document.getElementById('userStatusFilter');

  if (searchInput) {
    searchInput.addEventListener('input', applyFilters);
  }
  if (roleSelect) {
    roleSelect.addEventListener('change', applyFilters);
  }
  if (statusSelect) {
    statusSelect.addEventListener('change', applyFilters);
  }
}

function applyFilters() {
  const data = window.EDUNEXUS_MOCK_DATA && window.EDUNEXUS_MOCK_DATA.admin;
  if (!data) return;

  const searchInput = document.getElementById('userSearchInput');
  const roleSelect = document.getElementById('userRoleFilter');
  const statusSelect = document.getElementById('userStatusFilter');

  const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
  const roleFilter = roleSelect ? roleSelect.value : 'all';
  const statusFilter = statusSelect ? statusSelect.value : 'all';

  let filtered = currentUsersList.filter(user => {
    // Search query match
    const matchesSearch = !query || 
      user.name.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query) ||
      user.department.toLowerCase().includes(query);

    // Role filter match
    const matchesRole = roleFilter === 'all' || user.role.toLowerCase() === roleFilter.toLowerCase();

    // Status filter match
    const matchesStatus = statusFilter === 'all' || user.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesRole && matchesStatus;
  });

  renderUsersTable(filtered);
}

/**
 * Render System Audit Logs List
 */
function renderAuditLogs(logs) {
  const container = document.getElementById('auditLogsContainer');
  if (!container || !logs) return;

  container.innerHTML = '';
  logs.forEach(log => {
    const item = document.createElement('div');
    item.className = 'rec-card';

    item.innerHTML = `
      <div class="rec-main">
        <div class="rec-icon-box" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
        <div class="rec-content">
          <div class="cell-title">${log.action}</div>
          <div class="cell-sub">${log.actor} · ${log.time}</div>
        </div>
      </div>
      <span class="badge ${log.status === 'Success' ? 'badge-info' : 'badge-demo'}">
        ${log.status}
      </span>
    `;

    container.appendChild(item);
  });
}

/**
 * Add User Modal Handler
 */
function initAddUserModal() {
  const modal = document.getElementById('addUserModal');
  const openBtn = document.getElementById('openAddUserModalBtn');
  const closeBtn = document.getElementById('closeAddUserModalBtn');
  const cancelBtn = document.getElementById('cancelAddUserBtn');
  const form = document.getElementById('addUserForm');

  if (!modal) return;

  const closeModal = () => modal.classList.remove('is-open');

  if (openBtn) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('is-open');
    });
  }

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = document.getElementById('newUserName').value.trim();
      const email = document.getElementById('newUserEmail').value.trim();
      const role = document.getElementById('newUserRole').value;
      const dept = document.getElementById('newUserDept').value.trim() || 'General';

      if (!name || !email) {
        window.showToast("Please fill in name and email.", "error");
        return;
      }

      const newUser = {
        id: `usr_${Date.now()}`,
        name,
        email,
        role: role.charAt(0).toUpperCase() + role.slice(1),
        department: dept,
        status: 'Active',
        joined: 'Just now'
      };

      currentUsersList.unshift(newUser);
      applyFilters();
      closeModal();
      form.reset();

      window.showToast(`User account created for ${name} (${newUser.role}).`, 'success');
    });
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
      window.showToast("Logged out of administrative session.", "info");
      setTimeout(() => {
        window.location.href = '/login';
      }, 500);
    });
  });
}
