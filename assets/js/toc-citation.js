// Google Scholar citation fetcher
(function() {
  var countEl = document.getElementById('gs-citation-count');
  if (!countEl) return;
  var url = 'https://raw.githubusercontent.com/Jin-liangXiao/Jin-liangXiao.github.io/google-scholar-stats/gs_data_shieldsio.json';
  fetch(url)
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d && d.message) {
        countEl.textContent = d.message;
        countEl.classList.add('loaded');
      }
    })
    .catch(function() {
      countEl.textContent = '—';
    });
})();

// Smooth scroll for TOC links
document.querySelectorAll('.toc-link').forEach(function(link) {
  link.addEventListener('click', function(e) {
    e.preventDefault();
    var target = document.getElementById(this.dataset.target);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// Highlight current section on scroll
(function() {
  var sections = [];
  document.querySelectorAll('.toc-link').forEach(function(link) {
    var el = document.getElementById(link.dataset.target);
    if (el) sections.push({ link: link, el: el });
  });
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        sections.forEach(function(s) {
          s.link.classList.toggle('active', s.el === entry.target);
        });
      }
    });
  }, { rootMargin: '-20% 0px -70% 0px' });
  sections.forEach(function(s) { observer.observe(s.el); });
})();
