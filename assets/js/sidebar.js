(function () {
  'use strict';

  var burger = document.getElementById('burger');
  var overlay = document.getElementById('sidebar-overlay');
  var body = document.body;

  function openSidebar() {
    body.classList.add('sidebar-open');
  }

  function closeSidebar() {
    body.classList.remove('sidebar-open');
  }

  function toggleSidebar() {
    if (body.classList.contains('sidebar-open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  }

  if (burger) {
    burger.addEventListener('click', toggleSidebar);
  }

  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && body.classList.contains('sidebar-open')) {
      closeSidebar();
    }
  });

  // Auto-close sidebar on link click (mobile)
  var mobileQuery = window.matchMedia('(max-width: 768px)');
  var sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.addEventListener('click', function (e) {
      if (e.target.tagName === 'A' && mobileQuery.matches) {
        closeSidebar();
      }
    });
  }
})();
