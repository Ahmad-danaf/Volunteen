function toggleTasks(childId) {
    var row = document.getElementById('tasks-' + childId);
    if (row.classList.contains('hidden')) {
        row.classList.remove('hidden');
    } else {
        row.classList.add('hidden');
    }
}
