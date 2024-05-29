/* static/js/list_tasks.js */

function toggleDetails(counter) {
    var detailsRow = document.getElementById('details-' + counter);
    if (!detailsRow.style.display || detailsRow.style.display === 'none') {
        detailsRow.style.display = 'table-row';
    } else {
        detailsRow.style.display = 'none';
    }
}
