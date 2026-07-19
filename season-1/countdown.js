// Countdown to Episode 01 premiere
(function() {
  var el = document.getElementById('countdown');
  if (!el) return;
  var target = new Date(el.getAttribute('data-target')).getTime();
  var days = document.getElementById('cd-days');
  var hours = document.getElementById('cd-hours');
  var mins = document.getElementById('cd-mins');
  var secs = document.getElementById('cd-secs');

  function tick() {
    var now = Date.now();
    var d = target - now;
    if (d <= 0) {
      days.textContent = '00';
      hours.textContent = '00';
      mins.textContent = '00';
      secs.textContent = '00';
      return;
    }
    var dd = Math.floor(d / 86400000);
    var hh = Math.floor((d % 86400000) / 3600000);
    var mm = Math.floor((d % 3600000) / 60000);
    var ss = Math.floor((d % 60000) / 1000);
    days.textContent = String(dd).padStart(2, '0');
    hours.textContent = String(hh).padStart(2, '0');
    mins.textContent = String(mm).padStart(2, '0');
    secs.textContent = String(ss).padStart(2, '0');
  }
  tick();
  setInterval(tick, 1000);
})();
