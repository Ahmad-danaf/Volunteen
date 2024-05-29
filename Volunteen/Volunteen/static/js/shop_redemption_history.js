document.addEventListener('DOMContentLoaded', function() {
    var ctx = document.getElementById('redemptionChart').getContext('2d');
    var chartData = {
        labels: [{% for redemption in monthly_redemptions %}"{{ redemption.month|date:'F Y' }}"{% if not forloop.last %}, {% endif %}{% endfor %}],
        datasets: [{
            label: 'Points Used',
            data: [{% for redemption in monthly_redemptions %}{{ redemption.total_points }}{% if not forloop.last %}, {% endif %}{% endfor %}],
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 1
        }, {
            label: 'Max Points',
            data: [{% for redemption in monthly_redemptions %}{{ redemption.max_points }}{% if not forloop.last %}, {% endif %}{% endfor %}],
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }]
    };
    var chart = new Chart(ctx, {
        type: 'bar', // Changed to 'bar' for better comparison visibility
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                }
            }
        }
    });
});
