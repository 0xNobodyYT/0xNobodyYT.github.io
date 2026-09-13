(function () {
  'use strict';

  var measurementId = 'G-7K3SQNSXS9';
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  window.gtag('config', measurementId);

  document.addEventListener('click', function (event) {
    var link = event.target.closest && event.target.closest('a[href*="lootbar.com"]');
    if (!link) return;

    window.gtag('event', 'lootbar_click', {
      link_url: link.href,
      link_text: (link.textContent || '').trim(),
      page_path: window.location.pathname,
      transport_type: 'beacon'
    });
  });
}());
