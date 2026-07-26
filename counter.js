/* Free page-view counter via CounterAPI (no signup, no cookies). */
(function () {
  var el = document.getElementById("visitor-count");
  if (!el) return;

  var endpoint =
    "https://api.counterapi.dev/v1/gullahgeecheebiz/homepage/up";

  fetch(endpoint, { method: "GET", mode: "cors", cache: "no-store" })
    .then(function (res) {
      if (!res.ok) throw new Error("counter " + res.status);
      return res.json();
    })
    .then(function (data) {
      var n = data && (data.count || data.value);
      if (typeof n === "number") {
        el.textContent = n.toLocaleString("en-US");
      } else if (n != null) {
        el.textContent = String(n);
      } else {
        el.textContent = "—";
      }
    })
    .catch(function () {
      el.textContent = "—";
    });
})();
