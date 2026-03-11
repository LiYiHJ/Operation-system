function renderLineChart(canvasId, labels, values) {
  const el = document.getElementById(canvasId);
  if (!el || typeof Chart === 'undefined') return;
  new Chart(el, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Sales',
        data: values,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37,99,235,.15)',
        fill: true,
        tension: .25,
      }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });
}
window.renderLineChart = renderLineChart;
