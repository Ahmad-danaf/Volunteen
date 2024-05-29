/* static/js/mentor_completed_tasks_view.js */

document.addEventListener('DOMContentLoaded', function() {
    const toggles = document.querySelectorAll('.toggle-details, .task-title');
    toggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const taskId = this.getAttribute('data-task-id');
            const detailsRow = document.querySelector(`.task-details[data-task-id="${taskId}"]`);
            detailsRow.style.display = detailsRow.style.display === 'none' ? 'table-row' : 'none';
        });
    });
});
