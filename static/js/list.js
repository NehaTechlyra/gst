   /* ── Dots menu ───────────────────────────────────────────── */
function toggleDots(e) {
  e.stopPropagation();
  var btn  = document.getElementById('dotsBtn');
  var menu = document.getElementById('dotsDropdown');
  var open = menu.classList.toggle('show');
  btn.classList.toggle('open', open);
}

// Close when clicking anywhere else
document.addEventListener('click', function(e) {
  var wrap = document.querySelector('.dots-menu-wrap');
  if (wrap && !wrap.contains(e.target)) {
    document.getElementById('dotsDropdown').classList.remove('show');
    document.getElementById('dotsBtn').classList.remove('open');
  }
});

// Close on Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.getElementById('dotsDropdown').classList.remove('show');
    document.getElementById('dotsBtn').classList.remove('open');
  }
});