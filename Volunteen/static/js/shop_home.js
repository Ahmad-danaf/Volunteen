/* static/js/shop_home.js */
document.addEventListener('DOMContentLoaded', function() {
    var ctx = document.getElementById('pointsChart').getContext('2d');
    var pointsUsed = pointsUsedData;
    var maxPoints = maxPointsData;
    var pointsLeft = maxPoints - pointsUsed;

    var chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Points Used', 'Points Left'],
            datasets: [{
                data: [pointsUsed, pointsLeft],
                backgroundColor: ['#007bff', '#28a745'],
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                position: 'bottom'
            },
            title: {
                display: true,
                text: 'Points Usage'
            }
        }
    });
});
