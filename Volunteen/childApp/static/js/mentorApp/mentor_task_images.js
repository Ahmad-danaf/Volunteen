document.addEventListener("DOMContentLoaded", function () {
// Fade in cards sequentially
const taskCards = document.querySelectorAll(".task-card");
taskCards.forEach((card, index) => {
    setTimeout(() => {
    card.classList.add("fade-in");
    }, 100 * index);
});

// Toggle section visibility
const onTimeHeader = document.getElementById("onTimeHeader");
const onTimeContent = document.getElementById("onTimeContent");
const onTimeToggleIcon = document.getElementById("onTimeToggleIcon");

const lateHeader = document.getElementById("lateHeader");
const lateContent = document.getElementById("lateContent");
const lateToggleIcon = document.getElementById("lateToggleIcon");

onTimeHeader.addEventListener("click", function () {
    onTimeContent.classList.toggle("hidden");
    onTimeToggleIcon.classList.toggle("rotate-180");
});

lateHeader.addEventListener("click", function () {
    lateContent.classList.toggle("hidden");
    lateToggleIcon.classList.toggle("rotate-180");
});

// Image modal functionality
const imageModal = document.getElementById("imageModal");
const modalBackdrop = document.getElementById("modalBackdrop");
const modalContent = document.getElementById("modalContent");
const modalImage = document.getElementById("modalImage");
const closeModal = document.getElementById("closeModal");
const viewImages = document.querySelectorAll(".view-image");

viewImages.forEach((img) => {
    img.addEventListener("click", function () {
    modalImage.src = this.getAttribute("data-src");
    imageModal.classList.remove("hidden");

    // Animated entrance
    setTimeout(() => {
        modalBackdrop.classList.add("opacity-100");
        modalContent.classList.remove("scale-95", "opacity-0");
        modalContent.classList.add("scale-100", "opacity-100");
    }, 10);
    });
});

function hideImageModal() {
    modalContent.classList.remove("scale-100", "opacity-100");
    modalContent.classList.add("scale-95", "opacity-0");
    modalBackdrop.classList.remove("opacity-100");

    setTimeout(() => {
    imageModal.classList.add("hidden");
    }, 300);
}

closeModal.addEventListener("click", hideImageModal);
modalBackdrop.addEventListener("click", hideImageModal);

// Checkbox functionality
const taskCheckboxes = document.querySelectorAll(".task-checkbox");
const selectAllBtn = document.getElementById("selectAllBtn");
const submitSelectedBtn = document.getElementById("submitSelectedBtn");
const rejectSelectedBtn = document.getElementById("rejectSelectedBtn");
const selectAllInSectionCheckboxes = document.querySelectorAll(
    ".selectAllInSection"
);

// Points tracking for selected tasks
let minTaskPoints = Infinity;
let maxTaskPoints = 0;
const taskPointsMap = new Map(); // Map to track task points

// Initialize task points map
taskCheckboxes.forEach((checkbox) => {
    const taskId = checkbox.getAttribute("data-task-id");
    const taskCard = checkbox.closest('.task-card');
    taskCheckboxes.forEach((checkbox) => {
    const taskId = checkbox.getAttribute("data-task-id");
    const points = parseInt(checkbox.getAttribute("data-points"), 10) || 0;
    taskPointsMap.set(taskId, points);
});
});

function updatePointsRange() {
    // Reset min/max values
    minTaskPoints = Infinity;
    maxTaskPoints = 0;
    
    // Check all selected tasks
    const selectedCheckboxes = document.querySelectorAll(".task-checkbox:checked");
    
    if (selectedCheckboxes.length === 0) {
    minTaskPoints = 0;
    maxTaskPoints = 0;
    } else {
    selectedCheckboxes.forEach((checkbox) => {
        const taskId = checkbox.getAttribute("data-task-id");
        const points = taskPointsMap.get(taskId) || 0;
        
        // Update min/max
        if (points < minTaskPoints) minTaskPoints = points;
        if (points > maxTaskPoints) maxTaskPoints = points;
    });
    }
    
    // Update the display elements
    document.querySelectorAll('#maxPointsDisplay, #maxPointsDisplay2').forEach(el => {
    el.textContent = maxTaskPoints;
    });
    document.getElementById('minPointsDisplay').textContent = minTaskPoints;
    
    // Update the partial approval input limits
    const partialInput = document.getElementById('partialApprovalInput');
    partialInput.min = 1;
    partialInput.max = maxTaskPoints;
    
    // Update validation message
    validatePartialInput();
}

function validatePartialInput() {
    const input = document.getElementById('partialApprovalInput');
    const value = parseInt(input.value, 10);
    const validationMsg = document.getElementById('pointsValidationMessage');
    
    if (isNaN(value) || value < 1 || value > maxTaskPoints) {
    validationMsg.classList.remove('hidden');
    return false;
    } else {
    validationMsg.classList.add('hidden');
    return true;
    }
}

// Update UI when checkboxes change
taskCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", function() {
    updateButtonStates();
    updatePointsRange();
    });
});

function updateButtonStates() {
    const checkedCount = document.querySelectorAll(
    ".task-checkbox:checked"
    ).length;
    submitSelectedBtn.disabled = checkedCount === 0;
    rejectSelectedBtn.disabled = checkedCount === 0;

    if (checkedCount === 0) {
    submitSelectedBtn.classList.add(
        "disabled:opacity-50",
        "disabled:cursor-not-allowed"
    );
    rejectSelectedBtn.classList.add(
        "disabled:opacity-50",
        "disabled:cursor-not-allowed"
    );
    } else {
    submitSelectedBtn.classList.remove(
        "disabled:opacity-50",
        "disabled:cursor-not-allowed"
    );
    rejectSelectedBtn.classList.remove(
        "disabled:opacity-50",
        "disabled:cursor-not-allowed"
    );
    }
}

selectAllBtn.addEventListener("click", function () {
    const isAllChecked = [...taskCheckboxes].every((cb) => cb.checked);

    taskCheckboxes.forEach((checkbox) => {
    checkbox.checked = !isAllChecked;
    });

    selectAllInSectionCheckboxes.forEach((checkbox) => {
    checkbox.checked = !isAllChecked;
    });

    updateButtonStates();
    updatePointsRange();
});

selectAllInSectionCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", function () {
    const section = this.getAttribute("data-section");
    let selector;

    if (section === "ontime") {
        selector = "#onTimeContent .task-checkbox";
    } else if (section === "late") {
        selector = "#lateContent .task-checkbox";
    }

    if (selector) {
        const checkboxes = document.querySelectorAll(selector);
        checkboxes.forEach((cb) => {
        cb.checked = this.checked;
        });
    }

    updateButtonStates();
    updatePointsRange();
    });
});

// Validate partial input when it changes
document.getElementById('partialApprovalInput').addEventListener('input', validatePartialInput);

// Modals for approval and rejection
const approvalModal = document.getElementById("approvalModal");
const approvalModalBackdrop = document.getElementById(
    "approvalModalBackdrop"
);
const approvalModalContent = document.getElementById(
    "approvalModalContent"
);
const fullApprovalBtn = document.getElementById("fullApprovalBtn");
const partialApprovalBtn = document.getElementById("partialApprovalBtn");
const partialApprovalInput = document.getElementById(
    "partialApprovalInput"
);
const cancelApprovalBtn = document.getElementById("cancelApprovalBtn");

const rejectionModal = document.getElementById("rejectionModal");
const rejectionModalBackdrop = document.getElementById(
    "rejectionModalBackdrop"
);
const rejectionModalContent = document.getElementById(
    "rejectionModalContent"
);
const confirmRejectBtn = document.getElementById("confirmRejectBtn");
const rejectionFeedback = document.getElementById("rejectionFeedback");
const cancelRejectBtn = document.getElementById("cancelRejectBtn");

// Toast elements
const successToast = document.getElementById("successToast");
const errorToast = document.getElementById("errorToast");
const toastMessage = document.getElementById("toastMessage");
const errorToastMessage = document.getElementById("errorToastMessage");

function showApprovalModal() {
    // Update points range before showing modal
    updatePointsRange();
    
    approvalModal.classList.remove("hidden");
    setTimeout(() => {
    approvalModalBackdrop.classList.add("opacity-100");
    approvalModalContent.classList.remove("scale-95", "opacity-0");
    approvalModalContent.classList.add("scale-100", "opacity-100");
    }, 10);
}

function hideApprovalModal() {
    approvalModalContent.classList.remove("scale-100", "opacity-100");
    approvalModalContent.classList.add("scale-95", "opacity-0");
    approvalModalBackdrop.classList.remove("opacity-100");

    setTimeout(() => {
    approvalModal.classList.add("hidden");
    }, 300);
}

function showRejectionModal() {
    rejectionModal.classList.remove("hidden");
    setTimeout(() => {
    rejectionModalBackdrop.classList.add("opacity-100");
    rejectionModalContent.classList.remove("scale-95", "opacity-0");
    rejectionModalContent.classList.add("scale-100", "opacity-100");
    }, 10);
}

function hideRejectionModal() {
    rejectionModalContent.classList.remove("scale-100", "opacity-100");
    rejectionModalContent.classList.add("scale-95", "opacity-0");
    rejectionModalBackdrop.classList.remove("opacity-100");

    setTimeout(() => {
    rejectionModal.classList.add("hidden");
    }, 300);
}

function showToast(element, message) {
    if (element === successToast) {
    toastMessage.textContent = message;
    } else {
    errorToastMessage.textContent = message;
    }

    element.classList.remove("translate-y-20", "opacity-0");
    element.classList.add("translate-y-0", "opacity-100");

    setTimeout(() => {
    element.classList.remove("translate-y-0", "opacity-100");
    element.classList.add("translate-y-20", "opacity-0");
    }, 3000);
}

// Show/hide spinner for buttons
function toggleButtonLoading(button, isLoading) {
    const spinnerMap = {
    "fullApprovalBtn": "fullApprovalSpinner",
    "partialApprovalBtn": "partialApprovalSpinner",
    "confirmRejectBtn": "rejectSpinner"
    };
    const iconMap = {
    "fullApprovalBtn": "fullApprovalIcon",
    "confirmRejectBtn": "rejectIcon"
    };
    
    const spinnerId = spinnerMap[button.id];
    const iconId = iconMap[button.id];
    
    if (isLoading) {
    button.disabled = true;
    button.classList.add("opacity-75", "cursor-not-allowed");
    
    if (spinnerId) {
        document.getElementById(spinnerId).classList.remove("hidden");
    }
    
    if (iconId) {
        document.getElementById(iconId).classList.add("hidden");
    }
    } else {
    button.disabled = false;
    button.classList.remove("opacity-75", "cursor-not-allowed");
    
    if (spinnerId) {
        document.getElementById(spinnerId).classList.add("hidden");
    }
    
    if (iconId) {
        document.getElementById(iconId).classList.remove("hidden");
    }
    }
}

// Submit selected tasks for approval or rejection
submitSelectedBtn.addEventListener("click", showApprovalModal);
cancelApprovalBtn.addEventListener("click", hideApprovalModal);
approvalModalBackdrop.addEventListener("click", hideApprovalModal);

rejectSelectedBtn.addEventListener("click", showRejectionModal);
cancelRejectBtn.addEventListener("click", hideRejectionModal);
rejectionModalBackdrop.addEventListener("click", hideRejectionModal);

// Handle full approval action
fullApprovalBtn.addEventListener("click", async function () {
    // Show loading state
    toggleButtonLoading(fullApprovalBtn, true);
    
    const selectedIds = Array.from(
    document.querySelectorAll(".task-checkbox:checked")
    ).map((cb) => cb.getAttribute("data-task-id"));
    
    if (selectedIds.length === 0) {
    showToast(errorToast, "לא נבחרו משימות לאישור");
    hideApprovalModal();
    toggleButtonLoading(fullApprovalBtn, false);
    return;
    }

    try {
    const response = await fetch(REVIEW_TASK_URL, {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
        },
        body: JSON.stringify({
        task_ids: selectedIds,
        action: "approve",
        }),
    });

    const data = await response.json();

    if (data.success) {
        showToast(successToast, data.message);
        setTimeout(() => {
        window.location.reload();
        }, 1000);
    } else {
        showToast(errorToast, data.error || "אירעה שגיאה בעת אישור המשימות");
        toggleButtonLoading(fullApprovalBtn, false);
    }
    } catch (error) {
    showToast(errorToast, "אירעה שגיאה בעת התקשורת עם השרת");
    toggleButtonLoading(fullApprovalBtn, false);
    }
});

// Handle partial approval action
partialApprovalBtn.addEventListener("click", async function () {
    if (!validatePartialInput()) {
    return;
    }

    // Show loading state
    toggleButtonLoading(partialApprovalBtn, true);
    
    const selectedIds = Array.from(
    document.querySelectorAll(".task-checkbox:checked")
    ).map((cb) => cb.getAttribute("data-task-id"));
    const awardedCoins = partialApprovalInput.value;

    if (selectedIds.length === 0) {
    showToast(errorToast, "לא נבחרו משימות לאישור");
    hideApprovalModal();
    toggleButtonLoading(partialApprovalBtn, false);
    return;
    }

    if (!awardedCoins || isNaN(awardedCoins) || awardedCoins <= 0 || awardedCoins > maxTaskPoints) {
    showToast(errorToast, `יש להזין מספר נקודות תקין (בין 1 ל-${maxTaskPoints})`);
    toggleButtonLoading(partialApprovalBtn, false);
    return;
    }

    try {
    const response = await fetch(REVIEW_TASK_URL, {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
        },
        body: JSON.stringify({
        task_ids: selectedIds,
        action: "approve",
        awarded_coins: awardedCoins,
        }),
    });

    const data = await response.json();

    if (data.success) {
        showToast(successToast, data.message);
        setTimeout(() => {
        window.location.reload();
        }, 1000);
    } else {
        showToast(errorToast, data.error || "אירעה שגיאה בעת אישור המשימות");
        toggleButtonLoading(partialApprovalBtn, false);
    }
    } catch (error) {
    showToast(errorToast, "אירעה שגיאה בעת התקשורת עם השרת");
    toggleButtonLoading(partialApprovalBtn, false);
    }
});

// Handle reject action
confirmRejectBtn.addEventListener("click", async function () {
    // Show loading state
    toggleButtonLoading(confirmRejectBtn, true);
    
    const selectedIds = Array.from(
    document.querySelectorAll(".task-checkbox:checked")
    ).map((cb) => cb.getAttribute("data-task-id"));
    const feedback = rejectionFeedback.value;

    if (selectedIds.length === 0) {
    showToast(errorToast, "לא נבחרו משימות לדחייה");
    hideRejectionModal();
    toggleButtonLoading(confirmRejectBtn, false);
    return;
    }

    try {
    const response = await fetch(REVIEW_TASK_URL, {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
        },
        body: JSON.stringify({
        task_ids: selectedIds,
        action: "reject",
        mentor_feedback: feedback,
        }),
    });

    const data = await response.json();

    if (data.success) {
        showToast(successToast, data.message);
        setTimeout(() => {
        window.location.reload();
        }, 1000);
    } else {
        showToast(errorToast, data.error || "אירעה שגיאה בעת דחיית המשימות");
        toggleButtonLoading(confirmRejectBtn, false);
    }
    } catch (error) {
    showToast(errorToast, "אירעה שגיאה בעת התקשורת עם השרת");
    toggleButtonLoading(confirmRejectBtn, false);
    }
});
});
