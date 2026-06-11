/* Kemele CPMS — Main JavaScript */
'use strict';

document.addEventListener('DOMContentLoaded', function () {

  // ── Sidebar toggle ────────────────────────────────────────
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('collapsed');
      sidebar.classList.toggle('show');
      localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    });
    // Restore state
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
      sidebar.classList.add('collapsed');
    }
  }

  // ── Auto-dismiss alerts ───────────────────────────────────
  document.querySelectorAll('.alert-dismissible[data-auto-dismiss]').forEach(function (el) {
    const delay = parseInt(el.dataset.autoDismiss, 10) || 4000;
    setTimeout(function () {
      const alert = bootstrap.Alert.getOrCreateInstance(el);
      if (alert) alert.close();
    }, delay);
  });

  // ── Confirm dialogs ───────────────────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(el.dataset.confirm || 'Are you sure?')) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });

  // ── File input preview ────────────────────────────────────
  document.querySelectorAll('input[type="file"][data-preview]').forEach(function (input) {
    const previewId = input.dataset.preview;
    const preview = document.getElementById(previewId);
    if (!preview) return;
    input.addEventListener('change', function () {
      const file = this.files[0];
      if (!file) return;
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function (e) { preview.src = e.target.result; };
        reader.readAsDataURL(file);
      } else {
        preview.textContent = file.name;
      }
    });
  });

  // ── Table search filter ───────────────────────────────────
  document.querySelectorAll('[data-table-search]').forEach(function (input) {
    const tableId = input.dataset.tableSearch;
    const table = document.getElementById(tableId);
    if (!table) return;
    input.addEventListener('input', function () {
      const query = this.value.toLowerCase();
      table.querySelectorAll('tbody tr').forEach(function (row) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });
  });

  // ── Numeric formatting ────────────────────────────────────
  document.querySelectorAll('.fmt-currency').forEach(function (el) {
    const val = parseFloat(el.textContent.replace(/,/g, ''));
    if (!isNaN(val)) {
      el.textContent = 'K ' + val.toLocaleString('en-PG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
  });

  // ── Tooltip initialisation ────────────────────────────────
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  // ── Popover initialisation ────────────────────────────────
  document.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
    new bootstrap.Popover(el);
  });

  // ── GPS coordinates helper ────────────────────────────────
  const gpsBtn = document.getElementById('getGpsBtn');
  if (gpsBtn) {
    gpsBtn.addEventListener('click', function () {
      if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
      }
      navigator.geolocation.getCurrentPosition(function (pos) {
        const latEl = document.getElementById('id_gps_lat') || document.querySelector('[name="gps_lat"]');
        const lngEl = document.getElementById('id_gps_lng') || document.querySelector('[name="gps_lng"]');
        if (latEl) latEl.value = pos.coords.latitude.toFixed(6);
        if (lngEl) lngEl.value = pos.coords.longitude.toFixed(6);
      }, function () {
        alert('Unable to retrieve location. Please ensure location permission is granted.');
      });
    });
  }

  // ── AJAX CSRF helper ──────────────────────────────────────
  function getCookie(name) {
    let val = null;
    if (document.cookie && document.cookie !== '') {
      document.cookie.split(';').forEach(function (c) {
        c = c.trim();
        if (c.startsWith(name + '=')) {
          val = decodeURIComponent(c.slice(name.length + 1));
        }
      });
    }
    return val;
  }
  window.cpmsCSRF = getCookie('csrftoken');

  // ── Mark notification read on click ──────────────────────
  document.querySelectorAll('.notification-item[data-mark-url]').forEach(function (el) {
    el.addEventListener('click', function () {
      const url = el.dataset.markUrl;
      fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': window.cpmsCSRF, 'Content-Type': 'application/json' }
      });
    });
  });

});
