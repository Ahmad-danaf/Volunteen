/* static/js/mentor_home.js */

document.addEventListener('DOMContentLoaded', function() {
    var ctx = document.getElementById('tasksChart').getContext('2d');
    var openTasks = {{ open_tasks }};
    var completedTasks = {{ completed_tasks }};
    var totalTasks = {{ total_tasks }};

    var chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Open Tasks', 'Completed Tasks'],
            datasets: [{
                data: [openTasks, completedTasks],
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
                text: 'Tasks Overview'
            }
        }
    });
});
