// Google Scholar citation fetcher
(function() {
  var countEl = document.getElementById('gs-citation-count');
  if (!countEl) return;
  var url = 'https://raw.githubusercontent.com/Jin-liangXiao/Jin-liangXiao.github.io/google-scholar-stats/gs_data_shieldsio.json';
  var fallbackUrl = './assets/data/gs_data_shieldsio.json';

  function setCount(data) {
    var count = Number(data && data.message);
    if (!Number.isFinite(count) || count <= 0) {
      throw new Error('Invalid Google Scholar citation count');
    }
    countEl.textContent = String(count);
    countEl.classList.add('loaded');
  }

  fetch(url)
    .then(function(r) {
      if (!r.ok) throw new Error('Citation data request failed');
      return r.json();
    })
    .then(setCount)
    .catch(function() {
      fetch(fallbackUrl)
        .then(function(r) {
          if (!r.ok) throw new Error('Fallback citation request failed');
          return r.json();
        })
        .then(setCount)
        .catch(function() {
          countEl.textContent = '—';
        });
    });
})();

// Smooth scroll for top nav links
document.querySelectorAll('.top-nav-link').forEach(function(link) {
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
  document.querySelectorAll('.top-nav-link').forEach(function(link) {
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
  }, { rootMargin: '-15% 0px -70% 0px' });
  sections.forEach(function(s) { observer.observe(s.el); });
})();
