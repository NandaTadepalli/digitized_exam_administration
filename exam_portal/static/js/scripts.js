// ========== Utility: Format Date as DD-MMM-YYYY ========== 
function formatDateDMY(dateStr) {
    if (!dateStr) return '';
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const d = new Date(dateStr);
    if (isNaN(d)) return dateStr;
    return `${d.getDate().toString().padStart(2, '0')}-${months[d.getMonth()]}-${d.getFullYear()}`;
}

// ========== Spinner Modal Utilities ==========
function showSpinnerModal(message) {
    let modal = document.getElementById('spinner-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'spinner-modal';
        modal.innerHTML = `
            <div class="spinner-modal-content">
                <span class="spinner-std"></span>
                <div class="spinner-modal-text">${message}</div>
            </div>
        `;
        document.body.appendChild(modal);
    } else {
        modal.querySelector('.spinner-modal-text').innerHTML = message;
    }
    modal.classList.add('active');
}

function closeSpinnerModal() {
    let modal = document.getElementById('spinner-modal');
    if (modal) modal.classList.remove('active');
}
// ========== Global Modal Utility System v2.0 ==========
function toggleGlobalModal(modalId, show = true) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    if (show) {
        modal.classList.add('active');
        document.body.classList.add('modal-open');
    } else {
        modal.classList.remove('active');
        document.body.classList.remove('modal-open');
    }
}

// Global listener for closing any standardized modal
document.addEventListener('click', function(e) {
    // 1. Backdrop click to close (exact match on background)
    if (e.target.classList.contains('global-modal-backdrop')) {
        toggleGlobalModal(e.target.id, false);
    }
    
    // 2. Standardized Closing Triggers (supports nested icons/spans)
    const isClosingTrigger = 
        e.target.closest('.close-global-modal') || 
        e.target.closest('.close-modal') || 
        e.target.closest('.btn-secondary') ||
        (e.target.id && e.target.id.toLowerCase().includes('cancel'));

    if (isClosingTrigger) {
        const modal = e.target.closest('.global-modal-backdrop');
        if (modal) {
            toggleGlobalModal(modal.id, false);
        }
    }
});

// Final consolidated showPopupMessage utility
function showPopupMessage(text, type = 'error') {
    let popup = document.getElementById('popup-messages');
    if (!popup) {
        popup = document.createElement('div');
        popup.id = 'popup-messages';
        popup.style.position = 'fixed';
        popup.style.top = '20px';
        popup.style.right = '30px';
        popup.style.zIndex = '99999';
        document.body.appendChild(popup);
    }
    let msgDiv = document.createElement('div');
    msgDiv.className = 'popup-message popup-' + type;
    msgDiv.innerHTML = text;
    popup.appendChild(msgDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        msgDiv.classList.add('fade-out');
        setTimeout(() => msgDiv.remove(), 500);
    }, 5000);

    msgDiv.onclick = () => msgDiv.remove();
}

// Final consolidated showPopupMessage utility
// ========== Exam Publishable Check (examination.html) ========== 
function checkExamPublishable() {
    fetch('/ops/ajax/check_exam_publishable/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
        },
        body: JSON.stringify({ exam_id: window.examIdForSlots || '' })
    })
    .then(resp => resp.json())
    .then(data => {
        var publishExamWrapper = document.getElementById('publishExamWrapper');
        if (publishExamWrapper) {
            if (data.all_completed && !data.published) {
                publishExamWrapper.style.display = 'block';
            } else {
                publishExamWrapper.style.display = 'none';
            }
        }
        // Update exam status column
        const table = document.getElementById('examination-table');
        if (table) {
            const tbody = table.querySelector('tbody');
            if (tbody) {
                Array.from(tbody.children).forEach(row => {
                    const statusCell = row.children[7];
                    if (data.published) {
                        statusCell.innerHTML = '<span class="exam-status exam-status-published">Published</span>';
                    } else if (data.all_completed) {
                        statusCell.innerHTML = '<span class="exam-status exam-status-completed">Ready to Publish</span>';
                    } else {
                        statusCell.innerHTML = '<span class="exam-status exam-status-pending">Pending</span>';
                    }
                });
            }
        }
    });
}
document.addEventListener('DOMContentLoaded', function() {
    checkExamPublishable();
});
document.addEventListener('click', function(e) {
    if (e.target && e.target.id === 'publishExamBtn') {
        e.preventDefault();
        fetch('/ops/ajax/publish_exam/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
            },
            body: JSON.stringify({ exam_id: window.examIdForSlots || '' })
        })
        .then(resp => resp.json())
        .then(data => {
            if (data.success) {
                showPopupMessage('Exam published successfully.', 'success');
                checkExamPublishable();
            } else {
                showPopupMessage(data.error || 'Failed to publish exam.', 'error');
            }
        })
        .catch(() => {
            showPopupMessage('Network error. Please try again.', 'error');
        });
    }
});
// Global popup message utility
// Robust Global Modal Triggers for Examination Table
document.addEventListener('click', function(e) {
    // 1. Edit Exam Trigger
    const editBtn = e.target.closest('.edit-exam-link-trigger');
    if (editBtn) {
        e.preventDefault();
        const row = editBtn.closest('tr');
        if (row) {
            document.getElementById('editExamId').value = editBtn.dataset.examId || '';
            document.getElementById('edit_examname').value = row.children[1].textContent.trim();
            document.getElementById('edit_academic_year').value = row.children[2].textContent.trim();
            document.getElementById('edit_semester').value = row.children[3].textContent.trim();
            
            // Dates require YYYY-MM-DD format for input[type="date"]
            const startDate = row.children[4].dataset.raw || '';
            const endDate = row.children[5].dataset.raw || '';
            document.getElementById('edit_start_date').value = startDate;
            document.getElementById('edit_end_date').value = endDate;

            toggleGlobalModal('editExamModal', true);
        }
    }

    // 2. Delete Exam Trigger
    const deleteBtn = e.target.closest('.delete-exam-link-trigger');
    if (deleteBtn) {
        e.preventDefault();
        const row = deleteBtn.closest('tr');
        if (row) {
            document.getElementById('deleteExamId').value = deleteBtn.dataset.examId || '';
            document.getElementById('deleteExamWarning').textContent = `Are you sure you want to delete "${row.children[1].textContent.trim()}"?`;
            document.getElementById('deleteExamDetails').textContent = `Academic Year: ${row.children[2].textContent.trim()} | Semester: ${row.children[3].textContent.trim()}`;
            toggleGlobalModal('deleteExamModal', true);
        }
    }

    // 3. Confirm Delete Action
    const confirmDeleteBtn = e.target.closest('#confirmDeleteExamLink');
    if (confirmDeleteBtn) {
        e.preventDefault();
        const examId = document.getElementById('deleteExamId').value;
        if (!examId) return;

        fetch('/ops/ajax/delete-examination/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
            },
            body: JSON.stringify({ exam_id: examId })
        })
        .then(resp => resp.json())
        .then(data => {
            if (data.success) {
                showPopupMessage('Examination deleted successfully.', 'success');
                toggleGlobalModal('deleteExamModal', false);
                if (typeof fetchExaminations === 'function') fetchExaminations();
            } else {
                showPopupMessage(data.error || 'Failed to delete examination.', 'error');
            }
        })
        .catch(() => showPopupMessage('Network error occurred.', 'error'));
    }
});

// Edit Examination Form Submission (AJAX)
document.addEventListener('submit', function(e) {
    if (e.target && e.target.id === 'editExamForm') {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        const data = {};
        formData.forEach((value, key) => { data[key] = value; });

        fetch(form.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
            },
            body: JSON.stringify(data)
        })
        .then(resp => resp.json())
        .then(data => {
            if (data.success) {
                showPopupMessage('Examination updated successfully.', 'success');
                toggleGlobalModal('editExamModal', false);
                if (typeof fetchExaminations === 'function') fetchExaminations();
            } else {
                showPopupMessage(data.error || 'Failed to update examination.', 'error');
            }
        })
        .catch(() => showPopupMessage('Network error occurred.', 'error'));
    }
});
// Robust publish badge click handler for dynamically rendered elements
document.addEventListener('click', function(e) {
    const publishBtn = e.target.closest('.publish-exam-btn');
    if (publishBtn) {
        e.preventDefault();
        const examId = publishBtn.dataset.examId;
        fetch('/ops/ajax/publish_exam/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
            },
            body: JSON.stringify({ exam_id: examId })
        })
        .then(resp => resp.json())
        .then(data => {
            if (data.success) {
                showPopupMessage('Exam published successfully.', 'success');
                fetchExaminations(); // Refresh table
            } else {
                showPopupMessage(data.error || 'Failed to publish exam.', 'error');
            }
        })
        .catch(() => {
            showPopupMessage('Network error. Please try again.', 'error');
        });
        return;
    }
});
// ========== Seating Plan Coloring ========== 
document.addEventListener('DOMContentLoaded', function () {
    var seatingTable = document.querySelector('.seating-table');
    if (!seatingTable) return;
    // Build color palette
    function getColorPalette(n) {
        // Brighter pastel palette
        var palette = [
            '#90caf9', '#ffd54f', '#ffb74d', '#81c784', '#f06292', '#9575cd', '#4dd0e1', '#d4e157', '#ffb300', '#64b5f6',
            '#e0e0e0', '#f8bbd0', '#ce93d8', '#ba68c8', '#ff8a65', '#aed581', '#dce775', '#fff176', '#80deea', '#fff59d'
        ];
        if (n <= palette.length) return palette.slice(0, n);
        // If more, generate random bright pastel colors
        var extra = [];
        for (var i = 0; i < n - palette.length; i++) {
            var r = Math.floor(Math.random() * 120) + 135;
            var g = Math.floor(Math.random() * 120) + 135;
            var b = Math.floor(Math.random() * 120) + 135;
            extra.push('rgb(' + r + ',' + g + ',' + b + ')');
        }
        return palette.concat(extra);
    }
    // Collect all course codes
    var courseCodes = new Set();
    seatingTable.querySelectorAll('td.seating-cell').forEach(function(cell) {
        var courseDiv = cell.querySelector('.seating-course');
        if (courseDiv && courseDiv.textContent.trim()) {
            courseCodes.add(courseDiv.textContent.trim());
        }
    });
    var codeList = Array.from(courseCodes);
    var colorMap = {};
    var palette = getColorPalette(codeList.length);
    codeList.forEach(function(code, idx) {
        colorMap[code] = palette[idx];
    });
    // Color cells
    seatingTable.querySelectorAll('td.seating-cell').forEach(function(cell) {
        var courseDiv = cell.querySelector('.seating-course');
        if (courseDiv && courseDiv.textContent.trim()) {
            var code = courseDiv.textContent.trim();
            cell.style.backgroundColor = colorMap[code];
            cell.style.color = '#fff';
        } else {
            // Empty cell: mark with '-' and brighter light red background
            cell.innerHTML = '<span style="color:#b71c1c;font-weight:bold;font-size:18px">-</span>';
            cell.style.backgroundColor = '#ffcdd2';
            cell.style.color = '#b71c1c';
        }
    });
});
// ========== Room Allocation: Dynamic Allocated Capacity ========== 
document.addEventListener('DOMContentLoaded', function () {
        // Prevent allocation if cap not reached
        // var allocationForm = document.querySelector('.rooms-table-section form');
        // if (allocationForm) {
        //     allocationForm.addEventListener('submit', function(e) {
        //         let required = parseInt(requiredCap.textContent) || 0;
        //         let allocated = parseInt(allocatedCap.textContent) || 0;
        //         if (allocated < required) {
        //             e.preventDefault();
        //             showPopupMessage('Cannot allocate: Allocated capacity is less than required.<br>Please select more rooms to meet the required capacity.', 'error');
        //         }
        //     });
        // }
    var requiredRoom = document.getElementById('required-room-display');
    var allocatedRoom = document.getElementById('allocated-room-display');
    var roomCheckboxes = document.querySelectorAll('input[name="selected_rooms"]');
    var errorMsg = null;
    var clearBtn = document.getElementById('clear-room-selection');
    // Create error message element if not exists
    if (!document.getElementById('room-capacity-error')) {
        errorMsg = document.createElement('div');
        errorMsg.id = 'room-capacity-error';
        errorMsg.style.color = 'red';
        errorMsg.style.margin = '10px 0';
        errorMsg.style.display = 'none';
        var summaryWrapper = document.querySelector('.room-capacity-summary-wrapper');
        if (summaryWrapper) summaryWrapper.appendChild(errorMsg);
    } else {
        errorMsg = document.getElementById('room-capacity-error');
    }
    if (requiredRoom && allocatedRoom && roomCheckboxes.length > 0) {
        if (clearBtn && roomCheckboxes.length > 0) {
            clearBtn.addEventListener('click', function() {
                roomCheckboxes.forEach(function(cb) {
                    cb.checked = false;
                    cb.disabled = false;
                });
                if (errorMsg) errorMsg.style.display = 'none';
                updateAllocatedRoom();
            });
        }
        // Enforce allocation rule on form submit
        var allocationForm = document.querySelector('.rooms-table-section form');
        if (allocationForm) {
            allocationForm.addEventListener('submit', function(e) {
                // Parse required and allocated from display (format: count | capacity)
                let requiredText = requiredRoom.textContent.split('|');
                let allocatedText = allocatedRoom.textContent.split('|');
                let requiredCap = 0;
                let allocatedCap = 0;
                if (requiredText.length > 1) {
                    requiredCap = parseInt(requiredText[1].trim()) || 0;
                }
                if (allocatedText.length > 1) {
                    allocatedCap = parseInt(allocatedText[1].trim()) || 0;
                }
                if (requiredCap > 0) {
                    if (allocatedCap < requiredCap) {
                        e.preventDefault();
                        showPopupMessage('Cannot allocate: Allocated capacity is less than required. Please select more rooms to meet the required capacity.', 'error');
                    }
                } else if (allocatedCap === 0) {
                    // Allow submission, but show a popup message and redirect to slot list
                    e.preventDefault();
                    showPopupMessage('No rooms were allocated for this slot.', 'error');
                    setTimeout(function() {
                        // Change the URL below to your exam slot list or dashboard as appropriate
                        window.location.href = '/ops/exam_slots/';
                    }, 2500);
                }
            });
        }
    }
// Move updateAllocatedRoom and listeners outside the if block
function updateAllocatedRoom() {
    if (!allocatedRoom) return;
    let total = 0;
    let count = 0;
    if (typeof roomCheckboxes === 'undefined') return;
    roomCheckboxes.forEach(function(cb) {
        if (cb.checked) {
            total += parseInt(cb.getAttribute('data-capacity')) || 0;
            count += 1;
        }
    });
    allocatedRoom.textContent = count + ' | ' + total;
    // Hide error if under required
    if (typeof errorMsg !== 'undefined' && errorMsg) errorMsg.style.display = 'none';
}
if (typeof roomCheckboxes !== 'undefined' && typeof allocatedRoom !== 'undefined') {
    updateAllocatedRoom();
    roomCheckboxes.forEach(function(cb) {
        cb.addEventListener('change', function(e) {
            let total = 0;
            let count = 0;
            roomCheckboxes.forEach(function(box) {
                if (box.checked) {
                    total += parseInt(box.getAttribute('data-capacity')) || 0;
                    count += 1;
                }
            });
            // Parse required from requiredRoom (format: count | capacity)
            let requiredText = requiredRoom.textContent.split('|');
            let required = 0;
            if (requiredText.length > 1) {
                required = parseInt(requiredText[1].trim()) || 0;
            }
            // Find minimum capacity among unchecked rooms
            let minCap = Infinity;
            roomCheckboxes.forEach(function(box) {
                if (!box.checked) {
                    let cap = parseInt(box.getAttribute('data-capacity')) || 0;
                    if (cap < minCap) minCap = cap;
                }
            });
            if (total >= required) {
                // Allow this selection, but disable further selection
                if (typeof errorMsg !== 'undefined' && errorMsg) {
                    errorMsg.textContent = 'Required capacity attained or exceeded. Cannot select more rooms.';
                    errorMsg.style.display = 'block';
                }
                roomCheckboxes.forEach(function(box) {
                    if (!box.checked) box.disabled = true;
                });
            } else {
                // Border condition: only allow min cap room if next selection would meet/exceed required and difference is less than 40
                let remaining = required - total;
                let minCapRooms = [];
                roomCheckboxes.forEach(function(box) {
                    if (!box.checked) {
                        let cap = parseInt(box.getAttribute('data-capacity')) || 0;
                        if (cap === minCap) minCapRooms.push(box);
                    }
                });
                let restrictToMin = false;
                if (remaining < 40) {
                    roomCheckboxes.forEach(function(box) {
                        if (!box.checked) {
                            let cap = parseInt(box.getAttribute('data-capacity')) || 0;
                            if (cap >= remaining) restrictToMin = true;
                        }
                    });
                }
                roomCheckboxes.forEach(function(box) {
                    if (!box.checked) {
                        let cap = parseInt(box.getAttribute('data-capacity')) || 0;
                        if (restrictToMin) {
                            if (cap === minCap) {
                                box.disabled = false;
                            } else {
                                box.disabled = true;
                            }
                        } else {
                            box.disabled = false;
                        }
                    }
                });
                if (typeof errorMsg !== 'undefined' && errorMsg) errorMsg.style.display = 'none';
            }
            updateAllocatedRoom();
        });
    });
}
});
// ========== Faculty Allocation: Dynamic Allocated Faculty ========== 
document.addEventListener('DOMContentLoaded', function () {
    var requiredFac = document.getElementById('required-faculty-display');
    var allocatedFac = document.getElementById('allocated-faculty-display');
    var facultyCheckboxes = document.querySelectorAll('input[name="selected_faculty"]');
    var allocationForm = document.querySelector('.faculty-assigned form');
    function updateAllocatedFaculty() {
        let count = 0;
        facultyCheckboxes.forEach(function(cb) {
            if (cb.checked) count++;
        });
        if (allocatedFac) allocatedFac.textContent = count;
        // Only disable further selection if cap reached
        if (requiredFac && count < parseInt(requiredFac.textContent)) {
            facultyCheckboxes.forEach(function(cb) {
                cb.disabled = false;
            });
        } else if (requiredFac) {
            facultyCheckboxes.forEach(function(cb) {
                if (!cb.checked) cb.disabled = true;
            });
        }
    }
    if (allocationForm) {
        allocationForm.addEventListener('submit', function(e) {
            let required = parseInt(requiredFac.textContent) || 0;
            let allocated = parseInt(allocatedFac.textContent) || 0;
            if (allocated !== required) {
                e.preventDefault();
                showPopupMessage('Cannot assign: Allocated faculty is less than required.<br>Please select more faculty to meet the required count.', 'error');
            }
        });
    }
    facultyCheckboxes.forEach(function(cb) {
        cb.addEventListener('change', updateAllocatedFaculty);
    });
    updateAllocatedFaculty();
    var clearBtn = document.getElementById('clear-faculty-selection');
    if (clearBtn && facultyCheckboxes.length > 0) {
        clearBtn.addEventListener('click', function() {
            facultyCheckboxes.forEach(function(cb) {
                cb.checked = false;
                cb.disabled = false;
            });
            updateAllocatedFaculty();
        });
    }
});
// --- Course Registration Search, Autocomplete, Table, Print, Download, Pagination ---
var courseregStudentIdList = [];
function courseregFetchStudentIdAutocomplete(query) {
    fetch(`/masters/ajax/?type=student-id-autocomplete&q=${encodeURIComponent(query)}`)
        .then(resp => resp.json())
        .then(data => {
            courseregStudentIdList = (data.results || []).map(item => `${item.id} - ${item.name}`);
            // Sort suggestions by ID (smallest to largest)
            courseregStudentIdList.sort((a, b) => {
                const idA = a.split(' - ')[0];
                const idB = b.split(' - ')[0];
                // Numeric sort if IDs are numbers, otherwise string sort
                if (!isNaN(idA) && !isNaN(idB)) {
                    return Number(idA) - Number(idB);
                }
                return idA.localeCompare(idB);
            });
            courseregShowAutocompleteList(courseregStudentIdList, query);
        });
}
function courseregShowAutocompleteList(arr, query) {
    const inp = document.getElementById('studentSearch');
    const list = document.getElementById('autocomplete-list');
    courseregCloseAllLists();
    if (!inp || !inp.value || !list) return false;
    list.innerHTML = '';
    arr.forEach(item => {
        if (item.toLowerCase().includes(query.toLowerCase())) {
            let div = document.createElement('div');
            div.innerHTML = item;
            div.className = 'autocomplete-item';
            div.tabIndex = 0;
            div.addEventListener('click', function () {
                inp.value = item; // Fill input with full suggestion text
                courseregCloseAllLists();
            });
            list.appendChild(div);
        }
    });
    if (list && list.children.length > 0) {
        list.style.display = 'block';
        let currentFocus = -1;
        inp.onkeydown = function (e) {
            let items = list.getElementsByClassName('autocomplete-item');
            if (!items.length) return;
            if (e.key === 'ArrowDown') {
                currentFocus++;
                if (currentFocus >= items.length) currentFocus = 0;
                setActive(items, currentFocus);
            } else if (e.key === 'ArrowUp') {
                currentFocus--;
                if (currentFocus < 0) currentFocus = items.length - 1;
                setActive(items, currentFocus);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (currentFocus > -1) {
                    items[currentFocus].click();
                }
            }
        };
        function setActive(items, idx) {
            for (let i = 0; i < items.length; i++) {
                items[i].classList.remove('active');
            }
            if (items[idx]) {
                items[idx].classList.add('active');
                items[idx].scrollIntoView({ block: 'nearest' });
            }
        }
    } else {
        list.style.display = 'none';
    }
}
function courseregCloseAllLists() {
    const list = document.getElementById('autocomplete-list');
    if (list) {
        list.innerHTML = '';
        list.style.display = 'none';
    }
}
document.addEventListener('mousedown', function (e) {
    const list = document.getElementById('autocomplete-list');
    if (list && !list.contains(e.target) && e.target.id !== 'studentSearch') {
        courseregCloseAllLists();
    }
});
function courseregLoadCourseRegDataByStudentId(studentId, page = 1) {
    const params = new URLSearchParams({
        type: 'coursereg',
        student_id: studentId,
        page: page
    });
    fetch(`/masters/ajax/?${params.toString()}`)
        .then(resp => resp.json())
        .then(data => {
            document.getElementById('coursereg-list').innerHTML = data.table_html;
            const tableContainer = document.getElementById('courseregTableContainer');
            if (tableContainer) {
                tableContainer.classList.remove('d-none');
                tableContainer.style.display = 'block';
            }
            // Hide old containers if present
            if (document.getElementById('courseregActions')) document.getElementById('courseregActions').style.display = 'none';
            if (document.getElementById('courseregPaginationBar')) document.getElementById('courseregPaginationBar').style.display = 'none';
            // Show new flex container
            const actionsBar = document.getElementById('courseregActionsBar');
            if (actionsBar) {
                actionsBar.classList.remove('d-none');
                actionsBar.style.display = 'flex';
            }
            // Show inner containers
            if (document.getElementById('courseregActions')) document.getElementById('courseregActions').style.display = 'flex';
            if (document.getElementById('courseregPaginationBar')) document.getElementById('courseregPaginationBar').style.display = 'flex';
            // Update pagination HTML
            if (document.getElementById('coursereg-pagination')) document.getElementById('coursereg-pagination').innerHTML = data.pagination_html || '';
        });
}
var studentSearchElem = document.getElementById('studentSearch');
var searchStudentLinkElem = document.getElementById('searchStudentLink');
var resetStudentSearchLinkElem = document.getElementById('resetStudentSearchLink');
var courseregPaginationElem = document.getElementById('coursereg-pagination');
if (studentSearchElem) {
    studentSearchElem.addEventListener('input', function () {
        courseregFetchStudentIdAutocomplete(this.value);
    });
}
if (searchStudentLinkElem) {
    searchStudentLinkElem.addEventListener('click', function (e) {
        e.preventDefault();
        const inputValue = studentSearchElem.value.trim();
        // Accept either 'id - name' or just id
        let studentId = inputValue;
        if (inputValue.includes(' - ')) {
            studentId = inputValue.split(' - ')[0].trim();
        }
        if (studentId) {
            courseregLoadCourseRegDataByStudentId(studentId);
        }
    });
}
if (resetStudentSearchLinkElem) {
    resetStudentSearchLinkElem.addEventListener('click', function (e) {
        e.preventDefault();
        studentSearchElem.value = '';
        const tableContainer = document.getElementById('courseregTableContainer');
        if (tableContainer) {
            tableContainer.classList.add('d-none');
            tableContainer.style.display = 'none';
        }
        const actionsBar = document.getElementById('courseregActionsBar');
        if (actionsBar) {
            actionsBar.classList.add('d-none');
            actionsBar.style.display = 'none';
        }
        if (document.getElementById('courseregActions')) document.getElementById('courseregActions').style.display = 'none';
        if (document.getElementById('courseregPaginationBar')) document.getElementById('courseregPaginationBar').style.display = 'none';
    });
}
if (courseregPaginationElem) {
    courseregPaginationElem.addEventListener('click', function (e) {
        if (e.target.classList.contains('page-num') || e.target.classList.contains('page-arrow')) {
            e.preventDefault();
            const page = e.target.getAttribute('data-page');
            let inputValue = studentSearchElem.value.trim();
            let studentId = inputValue;
            if (inputValue.includes(' - ')) {
                studentId = inputValue.split(' - ')[0].trim();
            }
            if (page && studentId) courseregLoadCourseRegDataByStudentId(studentId, page);
        }
    });
}

// Clear Examination Form utility
function clearExaminationForm() {
    var form = document.getElementById('examinationForm');
    if (!form) return;
    form.reset();
    // Reset selects to first option
    var selects = form.querySelectorAll('select');
    selects.forEach(function (sel) { sel.selectedIndex = 0; });
    // Clear text/date inputs explicitly
    var inputs = form.querySelectorAll('input[type="text"], input[type="date"]');
    inputs.forEach(function (inp) { inp.value = ''; });
    // Reset min for end date
    var startInput = document.getElementById('start_date');
    var endInput = document.getElementById('end_date');
    if (endInput && startInput) {
        endInput.min = startInput.min;
    }
}
// Final consolidated handling of Exam management is now done via global listeners (Lines 164-251)
// to prevent conflicting 'onclick' handlers and 'display: none' inline-style overrides.
// ============ EXAM SLOT TABLE AJAX (operations/exams.html) ============
function fetchExamSlotsAjax() {
    // Standardized popup info helper
    function getPopupSlotInfoHTML(slot) {
        return `
            <div class='mb-1em popup-slot-info' style='background:#f8fafc; border-radius:12px; padding:15px; border:1px solid #e2e8f0; margin-bottom:20px;'>
                <div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:10px;'>
                    <div><span class='popup-slot-label'>Exam:</span> <span class='popup-slot-value'>${slot.exam_type}</span></div>
                    <div><span class='popup-slot-label'>Mode:</span> <span class='popup-slot-value'>${slot.mode}</span></div>
                    <div><span class='popup-slot-label'>Date:</span> <span class='popup-slot-value'>${slot.exam_date}</span></div>
                    <div><span class='popup-slot-label'>Time:</span> <span class='popup-slot-value'>${slot.start_time}-${slot.end_time}</span></div>
                    <div><span class='popup-slot-label'>Slot:</span> <span class='popup-slot-value'>${slot.slot_code}</span></div>
                </div>
            </div>`;
    }

    // Combined Trigger Handler for all Exam Management Popups
    document.addEventListener('click', function(e) {
        // 1. Room Assignment Popup
        const roomTrigger = e.target.closest('.room-assignment-badge') || 
                           (e.target.closest('a[href*="/ops/exam_rooms_alloc/"]') && e.target.closest('a').querySelector('.exam-status-available'));
        
        if (roomTrigger) {
            e.preventDefault();
            const badgeElement = e.target.closest('.room-assignment-badge') || e.target.closest('a').querySelector('.exam-status-available');
            const slotId = badgeElement.getAttribute('data-slot-id') || 
                          e.target.closest('tr').querySelector('.slot-courses-badge')?.getAttribute('data-slot-id');

            if (!slotId) return;

            let modal = document.getElementById('roomAllocModal');
            let modalContent = document.getElementById('roomAllocModalContent');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'roomAllocModal';
                modal.className = 'global-modal-backdrop';
                modal.innerHTML = `
                    <div class="global-modal-content wide">
                        <div class="modal-header-std">
                            <h2>Allocated Rooms</h2>
                            <button type="button" class="close-global-modal">&times;</button>
                        </div>
                        <div class="modal-body-std">
                            <div id="roomAllocModalContent">Loading...</div>
                        </div>
                    </div>`;
                document.body.appendChild(modal);
                modalContent = document.getElementById('roomAllocModalContent');
            }
            toggleGlobalModal('roomAllocModal', true);
            modalContent.innerHTML = '<div class="text-center">Loading room details...</div>';

            fetch(`/ops/ajax/slot-rooms/?slot_id=${slotId}`)
                .then(resp => resp.json())
                .then(data => {
                    if (!data.success) {
                        modalContent.innerHTML = `<div class='popup-message popup-error'>${data.error || 'No allocated rooms found.'}</div>`;
                        return;
                    }
                    let html = getPopupSlotInfoHTML(data.slot);
                    html += `<div class="popup-edit-btn-container"><a href="/ops/exam_rooms_alloc/?slot_id=${slotId}" class="btn-std btn-primary" style="text-decoration:none;">Update Allocation</a></div>`;
                    
                    if (!data.rooms || data.rooms.length === 0) {
                        html += `<div class="text-center p-20">No rooms allocated for this slot.</div>`;
                    } else {
                        html += `<div class='modal-table-container'><table class='dashboard-popup-table'>
                                    <thead><tr><th>Room No</th><th>Type</th><th>Capacity</th><th>Block</th></tr></thead>
                                    <tbody>`;
                        data.rooms.forEach(room => {
                            html += `<tr>
                                        <td>${room.room_no || 'N/A'}</td>
                                        <td>${room.room_type || 'N/A'}</td>
                                        <td>${room.capacity || 'N/A'}</td>
                                        <td>${room.block || 'N/A'}</td>
                                    </tr>`;
                        });
                        html += `</tbody></table></div>`;
                    }
                    modalContent.innerHTML = html;
                })
                .catch(() => modalContent.innerHTML = `<div class='popup-message popup-error'>Failed to load room details.</div>`);
        }
    });
    // Slot courses badge click handler (delegated)
    document.addEventListener('click', function (e) {
        // Always handle publish badge first
        const publishBtnMain = e.target.closest('.publish-exam-btn');
        if (publishBtnMain) {
            e.preventDefault();
            const examId = publishBtnMain.dataset.examId;
            fetch('/ops/ajax/publish_exam/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
                },
                body: JSON.stringify({ exam_id: examId })
            })
            .then(resp => resp.json())
            .then(data => {
                if (data.success) {
                    showPopupMessage('Exam published successfully.', 'success');
                    fetchExaminations(); // Force table refresh
                } else {
                    showPopupMessage(data.error || 'Failed to publish exam.', 'error');
                }
            })
            .catch(() => {
                showPopupMessage('Network error. Please try again.', 'error');
            });
            return;
        }
                                // Publish exam button click handler
                                const publishBtn = e.target.closest('.publish-exam-btn');
                                if (publishBtn) {
                                    e.preventDefault();
                                    const examId = publishBtn.dataset.examId;
                                    fetch('/ops/ajax/publish_exam/', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json',
                                            'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
                                        },
                                        body: JSON.stringify({ exam_id: examId })
                                    })
                                    .then(resp => resp.json())
                                    .then(data => {
                                        if (data.success) {
                                            showPopupMessage('Exam published successfully.', 'success');
                                            fetchExaminations(); // Force table refresh
                                        } else {
                                            showPopupMessage(data.error || 'Failed to publish exam.', 'error');
                                        }
                                    })
                                    .catch(() => {
                                        showPopupMessage('Network error. Please try again.', 'error');
                                    });
                                    return;
                                }
        // 2. Slot courses badge click handler
        const courseBadgeTrigger = e.target.closest('.slot-courses-badge');
        if (courseBadgeTrigger) {
            e.preventDefault();
            const slotId = courseBadgeTrigger.getAttribute('data-slot-id');
            if (!slotId) return;
            
            toggleGlobalModal('slotCoursesModal', true);
            const modalContent = document.getElementById('slotCoursesModalContent');
            modalContent.innerHTML = '<div class="text-center p-20">Loading course details...</div>';
            
            fetch(`/ops/ajax/slot-courses/?slot_id=${slotId}`)
                .then(resp => resp.json())
                .then(data => {
                    if (!data.success) {
                        modalContent.innerHTML = `<div class='popup-message popup-error'>${data.error || 'Failed to load course details.'}</div>`;
                        return;
                    }
                    let html = getPopupSlotInfoHTML(data.slot);
                    if (data.courses.length === 0) {
                        html += `<div class="text-center p-20">No courses assigned to this slot.</div>`;
                    } else {
                        html += `<div class='modal-table-container'><table class='dashboard-popup-table'>
                                    <thead><tr><th>Course Code</th><th>Course Name</th><th>Regulation</th><th>AY</th><th>Sem</th><th>Students</th></tr></thead>
                                    <tbody>`;
                        data.courses.forEach(course => {
                            html += `<tr>
                                        <td>${course.course_code}</td>
                                        <td>${course.course_name}</td>
                                        <td>${course.regulation || 'N/A'}</td>
                                        <td>${course.academic_year || 'N/A'}</td>
                                        <td>${course.semester || 'N/A'}</td>
                                        <td><strong>${course.student_count}</strong></td>
                                    </tr>`;
                        });
                        html += `</tbody></table></div>`;
                    }
                    modalContent.innerHTML = html;
                })
                .catch(() => modalContent.innerHTML = `<div class='popup-message popup-error'>Failed to load course details.</div>`);
        }

        // 3. Faculty Assignment Popup
        const facultyTrigger = e.target.closest('a[href*="/ops/exam_faculty_alloc/"]') && e.target.closest('a').querySelector('.exam-status-available');
        if (facultyTrigger) {
            e.preventDefault();
            const badgeElement = e.target.closest('a').querySelector('.exam-status-available');
            const row = e.target.closest('tr');
            const slotId = badgeElement.getAttribute('data-slot-id') || row?.querySelector('.slot-courses-badge')?.getAttribute('data-slot-id');

            if (!slotId) return;

            let modal = document.getElementById('facultyAllocModal');
            let modalContent = document.getElementById('facultyAllocModalContent');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'facultyAllocModal';
                modal.className = 'global-modal-backdrop';
                modal.innerHTML = `
                    <div class="global-modal-content wide">
                        <div class="modal-header-std">
                            <h2>Assigned Faculty</h2>
                            <button type="button" class="close-global-modal">&times;</button>
                        </div>
                        <div class="modal-body-std">
                            <div id="facultyAllocModalContent">Loading...</div>
                        </div>
                    </div>`;
                document.body.appendChild(modal);
                modalContent = document.getElementById('facultyAllocModalContent');
            }
            toggleGlobalModal('facultyAllocModal', true);
            modalContent.innerHTML = '<div class="text-center">Loading faculty details...</div>';

            fetch(`/ops/ajax/slot-faculty/?slot_id=${slotId}`)
                .then(resp => resp.json())
                .then(data => {
                    if (!data.success) {
                        modalContent.innerHTML = `<div class='popup-message popup-error'>${data.error || 'No assigned faculty found.'}</div>`;
                        return;
                    }
                    let html = getPopupSlotInfoHTML(data.slot);
                    html += `<div class="popup-edit-btn-container"><a href="/ops/exam_faculty_alloc/?slot_id=${slotId}" class="btn-std btn-primary" style="text-decoration:none;">Update Faculty</a></div>`;
                    
                    if (!data.faculty || data.faculty.length === 0) {
                        html += `<div class="text-center p-20">No faculty assigned for this slot.</div>`;
                    } else {
                        html += `<div class='modal-table-container'><table class='dashboard-popup-table'>
                                    <thead><tr><th>Faculty ID</th><th>Name</th><th>Email</th><th>Department</th></tr></thead>
                                    <tbody>`;
                        data.faculty.forEach(fac => {
                            html += `<tr>
                                        <td>${fac.faculty_id || 'N/A'}</td>
                                        <td>${fac.faculty_name || 'N/A'}</td>
                                        <td>${fac.email || 'N/A'}</td>
                                        <td>${fac.dept || 'N/A'}</td>
                                    </tr>`;
                        });
                        html += `</tbody></table></div>`;
                    }
                    modalContent.innerHTML = html;
                })
                .catch(() => modalContent.innerHTML = `<div class='popup-message popup-error'>Failed to load faculty details.</div>`);
        }
    });
    // Close modal logic handled globally
    // Slot edit modal logic
    document.addEventListener('click', function (e) {
        const editBtn = e.target.closest('.edit-slot-btn');
        if (editBtn) {
            e.preventDefault();
            const slotId = editBtn.dataset.slotId;
            // Find the row for this slot
            const row = editBtn.closest('tr');
            if (!row) return;
            // Fill modal fields from row
            document.getElementById('editSlotId').value = slotId;
            document.getElementById('edit_examtype').value = row.children[0].textContent.trim();
            document.getElementById('edit_mode').value = row.children[1].textContent.trim();
            document.getElementById('edit_exam_date').value = row.children[2].textContent.trim();
            document.getElementById('edit_start_time').value = row.children[3].textContent.trim();
            document.getElementById('edit_end_time').value = row.children[4].textContent.trim();
            document.getElementById('edit_slot_code').value = row.children[5].textContent.trim();
            document.getElementById('edit_registration_type').value = row.children[6].textContent.trim();
            toggleGlobalModal('editSlotModal', true);
        }
    });
    // Cancel/Close logic handled globally or via id
    const closeEditSlotModal = document.getElementById('closeEditSlotModal');
    if (closeEditSlotModal) closeEditSlotModal.onclick = () => toggleGlobalModal('editSlotModal', false);
    const cancelEditSlotBtn = document.getElementById('cancelEditSlotBtn');
    if (cancelEditSlotBtn) cancelEditSlotBtn.onclick = (e) => { e.preventDefault(); toggleGlobalModal('editSlotModal', false); };
    var examId = window.examIdForSlots || '';
    var tbody = document.getElementById('exam-slots-list');
    if (!tbody) return;
    if (!examId) {
        tbody.innerHTML = '<tr><td colspan="14" class="text-center">No exam selected.</td></tr>';
        return;
    }
    const regTypeFilter = document.getElementById('filter_registration_type')?.value || '';
    fetch(`/ops/ajax_exam_slots/?exam_id=${encodeURIComponent(examId)}&registration_type=${encodeURIComponent(regTypeFilter)}`)
        .then(response => response.json())
        .then(data => {
            if (data.slots.length === 0) {
                tbody.innerHTML = '<tr><td colspan="14" class="text-center">No exam slots created yet.</td></tr>';
            } else {
                tbody.innerHTML = '';
                // Sort slots by exam_date, then start_time (both ascending)
                data.slots.sort(function (a, b) {
                    if (a.exam_date < b.exam_date) return -1;
                    if (a.exam_date > b.exam_date) return 1;
                    if (a.start_time < b.start_time) return -1;
                    if (a.start_time > b.start_time) return 1;
                    return 0;
                });
                // Helper to convert HH:MM to 12-hour format
                function to12Hour(timeStr) {
                    if (!timeStr) return '';
                    let [h, m] = timeStr.split(":");
                    h = parseInt(h, 10);
                    const ampm = h >= 12 ? 'PM' : 'AM';
                    h = h % 12;
                    if (h === 0) h = 12;
                    return `${h}:${m} ${ampm}`;
                }
                data.slots.forEach(function (slot) {
                    let statusCell = '';
                    const schedUrl = `/ops/exam-scheduling/${slot.id}/`;
                    // Use 'courses_completed' flag from backend
                    if (slot.courses_completed) {
                        statusCell = `<td><a href="${schedUrl}" class="slot-schedule-link" title="Go to scheduling"><span class="exam-status exam-status-available">Assigned <img src='https://img.icons8.com/?size=100&id=79211&format=png&color=000000' alt='Assigned' class='status-icon'></span></a></td>`;
                    } else {
                        statusCell = `<td><a href="${schedUrl}" class="slot-schedule-link" title="Go to scheduling"><span class="exam-status exam-status-pending">Pending <img src='https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000' alt='Pending' class='status-icon'></span></a></td>`;
                    }

                    // Add edit and delete links
                    const editLink = `<a href="#" class="edit-slot-btn" data-slot-id="${slot.id}" title="Edit"><img src="https://img.icons8.com/?size=100&id=kzmsQM0bM3Bl&format=png&color=000000" alt="Edit Slot" class="icon-edit"></a>`;
                    const deleteLink = `<a href="#" class="delete-slot-btn" data-slot-id="${slot.id}" data-slot-date="${slot.exam_date}" data-slot-time="${slot.start_time}-${slot.end_time}" data-slot-code="${slot.slot_code}"><img src="https://img.icons8.com/?size=100&id=99971&format=png&color=000000" alt="Delete Slot" class="icon-delete"></a>`;
                    
                    // Course Count Badge
                    let badgeClass = slot.course_count > 0 ? 'badge-courses badge-courses-positive' : 'badge-courses badge-courses-zero';
                    let courseBadge = `<a href="#" class="slot-courses-badge" data-slot-id="${slot.id}">
                        <span class="${badgeClass}">count : ${slot.course_count}</span>
                    </a>`;

                    // Room allocation badge - Strict Backend Data
                    let roomBadge = '';
                    if (slot.rooms_completed) {
                        roomBadge = `<span class="exam-status exam-status-available">Assigned : ${slot.assigned_room_count}</span>`;
                    } else {
                        roomBadge = `<span class="exam-status exam-status-pending">Pending <img src='https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000' alt='Pending' class='status-icon'></span>`;
                    }

                    // Faculty assignment badge - Strict Backend Data
                    let facultyBadge = '';
                    if (slot.faculty_completed) {
                        facultyBadge = `<span class="exam-status exam-status-available">Assigned : ${slot.assigned_faculty_count}</span>`;
                    } else {
                        facultyBadge = `<span class="exam-status exam-status-pending">Pending <img src='https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000' alt='Pending' class='status-icon'></span>`;
                    }

                    // Final Status Column - Purely Backend Response
                    let newStatusCell = '';
                    if (slot.status === 'Publish') {
                        newStatusCell = `<td><span class="exam-status exam-status-available" title="Updated by ${slot.updated_by}">Completed <span class='status-icon status-tick' aria-label='Completed'><svg viewBox="0 0 16 16" width="17" height="17" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="8" cy="8" r="8" fill="#e6f9e6"/><path d="M4.5 8.5L7 11L11.5 6.5" stroke="#1a7f1a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></span></span></td>`;
                    } else if (slot.rooms_completed && slot.faculty_completed && slot.courses_completed && !slot.seating_completed) {
                        // All prerequisites done but seating not generated
                        newStatusCell = `<td><a href="#" class="slot-status-link" title="Status"><span class="exam-status exam-status-generate" title="Updated by ${slot.updated_by}">Generate <img src='https://img.icons8.com/?size=100&id=11841&format=png&color=ff9900' alt='Generate' class='status-icon'></span></a></td>`;
                    } else if (slot.is_generated) {
                        // Seating generated but status is not Publish (likely due to physical record mismatch)
                        newStatusCell = `<td><a href="#" class="slot-status-link" title="Status"><span class="exam-status exam-status-available" title="Updated by ${slot.updated_by}">Update <img src='https://img.icons8.com/?size=100&id=11841&format=png&color=ff9900' alt='Update' class='status-icon'></span></a></td>`;
                    } else {
                        newStatusCell = `<td><a href="#" class="slot-status-link" title="Status"><span class="exam-status exam-status-pending" title="Updated by ${slot.updated_by}">Pending <img src='https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000' alt='Pending' class='status-icon'></span></a></td>`;
                    }
                    var row = `<tr data-slot-id="${slot.id}">
                        <td>${slot.exam_type || ''}</td>
                        <td>${slot.mode || ''}</td>
                        <td>${slot.exam_date || ''}</td>
                        <td>${to12Hour(slot.start_time) || ''}</td>
                        <td>${to12Hour(slot.end_time) || ''}</td>
                        <td>${slot.slot_code || ''}</td>
                        <td>${slot.registration_type || 'REGULAR'}</td>
                        ${statusCell}
                        <td>${courseBadge}</td>
                        <td>${slot.student_count || 0}</td>
                        <td><a href="/ops/exam_rooms_alloc/?slot_id=${slot.id}">${roomBadge}</a></td>
                        <td><a href="/ops/exam_faculty_alloc/?slot_id=${slot.id}">${facultyBadge}</a></td>
                        ${newStatusCell}
                        <td>${editLink}${deleteLink}</td>
                    </tr>`;
                    tbody.innerHTML += row;
                });
            }
        })
        .catch(() => {
            tbody.innerHTML = '<tr><td colspan="14" class="text-center">Error loading slots.</td></tr>';
        });
    // Utility to show popup message (top-right)
        // Click handler for new status column
        document.addEventListener('click', function(e) {
            const statusLink = e.target.closest('.slot-status-link');
            if (statusLink) {
                const statusSpanGenerate = statusLink.querySelector('.exam-status-generate');
                const statusSpanPending = statusLink.querySelector('.exam-status-pending');
                const row = statusLink.closest('tr');
                if (statusSpanPending) {
                    let missing = [];
                    if (row) {
                        // Check registration type (index 6)
                        // Check statusCell (index 7)
                        // Check course count (index 8)
                        const courseCountCell = row.children[8];
                        if (courseCountCell && courseCountCell.textContent.trim() === 'count : 0') missing.push('Course Assignment');
                        // Check room assignment (index 10)
                        const roomCell = row.children[10];
                        if (roomCell && roomCell.textContent.includes('Pending')) missing.push('Room Assignment');
                        // Check faculty assignment (index 11)
                        const facultyCell = row.children[11];
                        if (facultyCell && facultyCell.textContent.includes('Pending')) missing.push('Faculty Assignment');
                    }
                    let msg = 'Status is Pending.<br>Some required actions are incomplete.';
                    if (missing.length > 0) {
                        msg += '<br><span style="color:#b30000;font-weight:600;">Missing/Incomplete:</span><br>';
                        msg += missing.map(item => `<span style='display:block;margin-left:1em;'>${item}</span>`).join('');
                    }
                    showPopupMessage(msg, 'warning');
                } else if (statusSpanGenerate) {
                    // Get slot_id from row attribute
                    const slotId = row.getAttribute('data-slot-id');
                    if (!slotId) {
                        showPopupMessage('Slot ID not found for generation.', 'error');
                        return;
                    }
                    // Disable Generate button
                    statusLink.classList.add('disabled');
                    statusLink.style.pointerEvents = 'none';
                    // Show modal spinner popup in center
                    showSpinnerModal('Generating seating plan... Please wait.<br><span style="color:#b30000;font-weight:600;">Do not close or refresh the page until completed.</span><br><span id="est-time" style="color:#2563eb;font-weight:500;">Estimated time: 10-20 seconds</span>');
                    let timer = 0;
                    let estTime = 20; // Estimated max time in seconds
                    const estTimeElem = document.getElementById('est-time');
                    const interval = setInterval(() => {
                        timer++;
                        if (estTimeElem) {
                            estTimeElem.textContent = `Estimated time: ${Math.max(estTime-timer, 1)} seconds`;
                        }
                    }, 1000);
                    fetch('/ops/ajax/generate-seating-plan/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
                        },
                        body: 'slot_id=' + encodeURIComponent(slotId)
                    })
                    .then(response => response.json())
                    .then(data => {
                        clearInterval(interval);
                        statusLink.classList.remove('disabled');
                        statusLink.style.pointerEvents = '';
                        const statusCell = row.children[11]; // newStatusCell
                        if (data.status === 'success' || data.status === 'assigned') {
                            closeSpinnerModal();
                            statusCell.innerHTML = `<span class="exam-status exam-status-available exam-status-assigned">Assigned <img src='https://img.icons8.com/?size=100&id=79211&format=png&color=000000' alt='Assigned' class='status-icon'></span>`;
                            if (statusCell.querySelector('.exam-status')) {
                                statusCell.querySelector('.exam-status').classList.remove('slot-status-link');
                                statusCell.querySelector('.exam-status').style.cursor = 'default';
                            }
                            showPopupMessage('Seating plan and invigilation already completed! Status updated to Assigned.', 'success');
                        } else if (data.status === 'update') {
                            // Show missing assignments in spinner modal
                            let missing = [];
                            if (roomBadge && roomBadge.includes('Pending')) missing.push('Room Assignment');
                            if (facultyBadge && facultyBadge.includes('Pending')) missing.push('Faculty Assignment');
                            if (badgeClass && badgeClass.includes('badge-courses-zero')) missing.push('Course Assignment');
                            let msg = 'Some assignments are missing. Please update seating/invigilation.';
                            if (missing.length > 0) {
                                msg += '<br><span style="color:#b30000;font-weight:600;">Missing/Incomplete:</span><br>';
                                msg += missing.map(item => `<span style='display:block;margin-left:1em;'>${item}</span>`).join('');
                            }
                            showSpinnerModal(msg + '<br><button id="closeSpinnerBtn" style="margin-top:1em;padding:0.5em 1.2em;background:#2563eb;color:#fff;border:none;border-radius:6px;font-size:1em;cursor:pointer;">Close</button>');
                            // Add close button handler
                            setTimeout(() => {
                                const closeBtn = document.getElementById('closeSpinnerBtn');
                                if (closeBtn) closeBtn.onclick = () => closeSpinnerModal();
                            }, 100);
                            statusCell.innerHTML = `<a href="#" class="slot-status-link" title="Status"><span class="exam-status exam-status-available">Update <img src='https://img.icons8.com/?size=100&id=11841&format=png&color=ff9900' alt='Update' class='status-icon'></span></a>`;
                        } else {
                            closeSpinnerModal();
                            showPopupMessage('Error: ' + (data.error || 'Unknown error'), 'error');
                        }
                    })
                    .catch(() => {
                        clearInterval(interval);
                        closeSpinnerModal();
                        statusLink.classList.remove('disabled');
                        statusLink.style.pointerEvents = '';
                        showPopupMessage('Error generating seating plan.', 'error');
                    });
            } // Close statusSpanGenerate
        } // Close statusLink
    }); // Close click listener

    // Intercept Room Allocation and Faculty Assignment clicks for status checks
    document.addEventListener('click', function (e) {
        const slotTable = document.getElementById('slot-table');
        if (!slotTable) return;
        const roomLink = e.target.closest('a[href*="/ops/exam_rooms_alloc/"]');
        const facultyLink = e.target.closest('a[href*="/ops/exam_faculty_alloc/"]');
        if (roomLink || facultyLink) {
            const row = e.target.closest('tr');
            if (!row) return;
            // 0: Exam Type, 1: Mode, 2: Date, 3: Start, 4: End, 5: Slot Code, 6: Course Status, 7: Course Count, 8: Student Count, 9: Room Allocation, 10: Faculty Assignment
            const courseStatusCell = row.children[6];
            const roomStatusCell = row.children[9];
            const facultyStatusCell = row.children[10];
            // Check for 'Pending' in course status before allowing room allocation
            let coursePending = courseStatusCell && courseStatusCell.textContent.includes('Pending');
            let roomPending = roomStatusCell && roomStatusCell.textContent.includes('Pending');
            if (roomLink) {
                if (coursePending) {
                    e.preventDefault();
                    showPopupMessage('Room Allocation not allowed.<br><b>Previous status:</b> Course Status is <u>Pending</u>.', 'error');
                    return;
                }
            }
            if (facultyLink) {
                if (roomPending) {
                    e.preventDefault();
                    showPopupMessage('Faculty Assignment not allowed.<br><b>Previous status:</b> Room Allocation is <u>Pending</u>.', 'error');
                    return;
                }
                if (coursePending) {
                    e.preventDefault();
                    showPopupMessage('Faculty Assignment not allowed.<br><b>Previous status:</b> <span style="color:#b30000">Course Status is <u>Pending</u></span>. Please complete Course Status before proceeding.', 'error');
                    return;
                }
            }
        }
    });
    // Slot delete modal and AJAX logic
    document.addEventListener('click', function (e) {
        const delBtn = e.target.closest('.delete-slot-btn');
        if (delBtn) {
            e.preventDefault();
            const slotId = delBtn.dataset.slotId;
            const slotDate = delBtn.dataset.slotDate;
            const slotTime = delBtn.dataset.slotTime;
            const slotCode = delBtn.dataset.slotCode;
            document.getElementById('deleteSlotWarning').innerHTML = `Are you sure you want to delete this slot?<br><b>Date:</b> ${slotDate} <b>Time:</b> ${slotTime} <b>Code:</b> ${slotCode}<br>This will <b>permanently delete</b> all exams scheduled under this slot.`;
            document.getElementById('deleteSlotId').value = slotId;
            toggleGlobalModal('deleteSlotModal', true);
        }
    });
    const closeDeleteSlotModal = document.getElementById('closeDeleteSlotModal');
    if (closeDeleteSlotModal) closeDeleteSlotModal.onclick = () => toggleGlobalModal('deleteSlotModal', false);
    const cancelDeleteSlotBtn = document.getElementById('cancelDeleteSlotBtn');
    if (cancelDeleteSlotBtn) cancelDeleteSlotBtn.onclick = (e) => { e.preventDefault(); toggleGlobalModal('deleteSlotModal', false); };
    document.getElementById('confirmDeleteSlotLink').onclick = function (e) {
        e.preventDefault();
        const slotId = document.getElementById('deleteSlotId').value;
        fetch('/ops/ajax/delete-examination/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ slot_id: slotId })
        })
            .then(res => res.json())
            .then(data => {
                document.getElementById('deleteSlotModal').style.display = 'none';
                if (data.success) {
                    alert('Slot and all related exams deleted successfully.');
                    fetchExamSlotsAjax();
                } else {
                    alert('Failed to delete slot: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(() => {
                document.getElementById('deleteSlotModal').style.display = 'none';
                alert('Failed to delete slot due to network error.');
            });
    };
}
// ============ EXAMINATION TABLE AJAX (operations/examination.html) ============
document.addEventListener('DOMContentLoaded', function () {
    // ...existing code for exam_date min/max and slot form validation...
    if (!document.getElementById('examination-table')) return;

    function pendingBadge() {
        return `<span class="exam-status exam-status-pending" style="background:#fff3cd;color:#856404;padding:2px 0px 2px 10px;border-radius:6px;display:inline-flex;align-items:center">
            Pending <img src="https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000" alt="Pending" class="status-icon" style="width:1.2em;height:1.2em;vertical-align:middle;margin-left:6px;">
        </span>`;
    }
    function availableBadge(count) {
        return `<span class="exam-status exam-status-available" style="background:#e6f9e6;color:#1a7f1a;padding:2px 10px 2px 10px;border-radius:6px;display:inline-flex;align-items:center;font-weight:600;">
            Available : ${count}
        </span>`;
    }
    window.fetchExaminations = function fetchExaminations(page = 1) {
        // Always clear and hide deleteExamModal before reload
        const modal = document.getElementById('deleteExamModal');
        if (modal) {
            document.getElementById('deleteExamWarning').innerHTML = '';
            document.getElementById('deleteExamDetails').innerHTML = '';
            document.getElementById('deleteExamId').value = '';
        }
        fetch(`/ops/ajax/examinations/?page=${page}`)
            .then(resp => resp.json())
            .then(data => {
                const tbody = document.querySelector('#examination-table tbody');
                tbody.innerHTML = '';
                if (data.results && data.results.length) {
                    data.results.forEach((exam, idx) => {
                        const slotLink = `/ops/exams/?exam_id=${exam.exam_id}` +
                            `&exam_name=${encodeURIComponent(exam.exam_name)}` +
                            `&start_date=${encodeURIComponent(exam.start_date)}` +
                            `&end_date=${encodeURIComponent(exam.end_date)}`;
                        const rowId = `exam-row-${exam.exam_id}`;
                        const lockIcon = exam.is_locked ? 'https://img.icons8.com/?size=100&id=DZbPJ4lsqOdQ&format=png&color=000000' : 'https://img.icons8.com/?size=100&id=7Sm4QkMSvsON&format=png&color=000000';
                        const lockTitle = exam.is_locked ? `Locked by ${exam.locked_by_name} at ${exam.lock_updated_at}` : 'Click to lock';
                        const lockedClass = exam.is_locked ? 'exam-row-locked' : '';
                        
                        tbody.innerHTML += `<tr id="${rowId}" class="${lockedClass}">
                            <td>${exam.number}</td>
                            <td>${exam.exam_name}</td>
                            <td>${exam.academic_year || ''}</td>
                            <td>${exam.semester || ''}</td>
                            <td data-raw="${exam.start_date}">${formatDateDMY(exam.start_date)}</td>
                            <td data-raw="${exam.end_date}">${formatDateDMY(exam.end_date)}</td>
                            <td id="slot-badge-${exam.exam_id}"><a href="${slotLink}" class="slot-link" data-exam-name="${encodeURIComponent(exam.exam_name)}">${pendingBadge()}</a></td>
                            <td id="status-badge-${exam.exam_id}">${pendingBadge()}</td>
                            <td>
                                <!-- Trigger classes standardized for global listener -->
                                <a href="#" class="lock-toggle-btn" data-exam-id="${exam.exam_id}" data-is-locked="${exam.is_locked}" title="${lockTitle}" style="margin-right:12px;">
                                    <img src="${lockIcon}" alt="Lock" style="width:20px;height:20px;">
                                </a>
                                <a href="#" class="edit-exam-link-trigger ${exam.is_locked ? 'disabled-action' : ''}" data-exam-id="${exam.exam_id}" data-locked="${exam.is_locked}" title="Edit"><img src="https://img.icons8.com/?size=100&id=kzmsQM0bM3Bl&format=png&color=000000" alt="Edit Exam" style="width:20px;height:20px;margin-right:12px;"></a>
                                <a href="#" class="delete-exam-link-trigger ${exam.is_locked ? 'disabled-action' : ''}" data-exam-id="${exam.exam_id}" data-exam-name="${exam.exam_name}" data-locked="${exam.is_locked}" title="Delete"><img src="https://img.icons8.com/?size=100&id=99971&format=png&color=000000" alt="Delete Exam" style="width:20px;height:20px;"></a>
                            </td>
                        </tr>`;
                        fetch(`/ops/ajax_exam_slots/?exam_id=${exam.exam_id}`)
                            .then(resp => resp.json())
                            .then(slotData => {
                                const badgeTd = document.getElementById(`slot-badge-${exam.exam_id}`);
                                const statusTd = document.getElementById(`status-badge-${exam.exam_id}`);
                                if (badgeTd && slotData.slots && slotData.slots.length > 0) {
                                    const slotLinkClass = exam.is_locked ? 'slot-link-locked' : 'slot-link';
                                    badgeTd.innerHTML = `<a href="${slotLink}" class="${slotLinkClass}" data-exam-name="${encodeURIComponent(exam.exam_name)}" data-locked="${exam.is_locked}">${availableBadge(slotData.slots.length)}</a>`;
                                }
                                // Determine if all slots are completed (is_generated and assignments done)
                                let allCompleted = slotData.slots.length > 0 && slotData.slots.every(s => s.status === 'Publish');
                                if (statusTd) {
                                    if (exam.published) {
                                        // Published Status (Green) - Clicking allows unpublishing if not locked
                                        statusTd.innerHTML = `
                                            <a href="#" class="unpublish-exam-btn" data-exam-id="${exam.exam_id}" data-locked="${exam.is_locked}" style="text-decoration:none;">
                                                <span class="exam-status" style="background:#e6f9e6;color:#1a7f1a;padding:4px 12px;border-radius:12px;display:inline-flex;align-items:center;font-weight:700;box-shadow:0 2px 4px rgba(22,163,74,0.1);">
                                                    Published <img src="https://img.icons8.com/?size=100&id=79211&format=png&color=16a34a" alt="Published" style="width:1.2em;height:1.2em;margin-left:8px;">
                                                </span>
                                            </a>`;
                                    } else if (allCompleted) {
                                        // Ready to Publish (Amber) - Show button
                                        statusTd.innerHTML = `
                                            <a href="#" class="publish-exam-btn-trigger" data-exam-id="${exam.exam_id}" data-locked="${exam.is_locked}" style="text-decoration:none;">
                                                <span class="exam-status" style="background:#fff7ed;color:#ea580c;padding:4px 12px;border-radius:12px;display:inline-flex;align-items:center;font-weight:700;border:1.5px solid #fdba74;transition:all 0.2s;">
                                                    Publish <img src="https://img.icons8.com/?size=100&id=79211&format=png&color=ea580c" alt="Publish" style="width:1.2em;height:1.2em;margin-left:8px;">
                                                </span>
                                            </a>`;
                                    } else {
                                        // Incomplete (Grey)
                                        statusTd.innerHTML = `
                                            <span class="exam-status" style="background:#f1f5f9;color:#64748b;padding:4px 12px;border-radius:12px;display:inline-flex;align-items:center;font-weight:600;opacity:0.8;">
                                                Incomplete
                                            </span>`;
                                    }
                                }
                            });
                        // ...existing code...
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">No examinations found.</td></tr>';
                }
                const pagDiv = document.getElementById('examination-pagination');
                pagDiv.innerHTML = '';
                if (data.num_pages > 1) {
                    for (let i = 1; i <= data.num_pages; i++) {
                        pagDiv.innerHTML += `<a href="#" class="page-link${i === data.page ? ' active' : ''}" data-page="${i}">${i}</a> `;
                    }
                    pagDiv.querySelectorAll('.page-link').forEach(link => {
                        link.addEventListener('click', function (e) {
                            e.preventDefault();
                            fetchExaminations(parseInt(this.dataset.page));
                        });
                    });
                }
            });
    }
    // Register delete-exam-btn handler after table is rendered
    document.addEventListener('click', function (e) {
        // Handle click on Exam Scheduling link to check for slots
        const schedLink = e.target.closest('.exam-schedule-link');
        if (schedLink) {
            e.preventDefault();
            const examId = schedLink.dataset.examId;
            const slotLink = schedLink.dataset.slotLink;
            fetch(`/ops/ajax_exam_slots/?exam_id=${examId}`)
                .then(resp => resp.json())
                .then(data => {
                    if (data.slots && data.slots.length > 0) {
                        window.location.href = slotLink;
                    } else {
                        alert('No slots available for this examination. Please create slots first.');
                    }
                })
                .catch(() => {
                    alert('Error checking slots for this examination.');
                });
            return;
        }
        const btn = e.target.closest('.delete-exam-btn');
        if (btn) {
            e.preventDefault();
            const examId = btn.dataset.examId;
            const examName = btn.dataset.examName;
            fetch(`/ops/ajax_exam_slots/?exam_id=${examId}`)
                .then(resp => resp.json())
                .then(data => {
                    let detailsHtml = '';
                    if (data.slots && data.slots.length > 0) {
                        detailsHtml += `<b>Slots to be deleted:</b><ul style='margin-bottom:0;'>`;
                        data.slots.forEach(slot => {
                            detailsHtml += `<li>${slot.exam_date} [${slot.start_time}-${slot.end_time}] (${slot.slot_code || ''}) - <b>${slot.course_count}</b> exam(s)</li>`;
                        });
                        detailsHtml += '</ul>';
                    } else {
                        detailsHtml += '<b>No slots found for this examination.</b>';
                    }
                });
        }
    });

    // If on exams.html, autofill exam name from query param and make readonly
    if (window.location.pathname.endsWith('/exams/')) {
        const urlParams = new URLSearchParams(window.location.search);
        const examName = urlParams.get('exam_name');
        const startDate = urlParams.get('start_date');
        const endDate = urlParams.get('end_date');
        if (examName) {
            function setExamNameReadonly() {
                const examNameInput = document.getElementById('examname');
                if (examNameInput) {
                    examNameInput.value = decodeURIComponent(examName);
                    examNameInput.readOnly = true;
                    examNameInput.style.background = '#f5f5f5';
                } else {
                    setTimeout(setExamNameReadonly, 100);
                }
            }
            setExamNameReadonly();
        }
        if (startDate || endDate) {
            function setExamDateLimits() {
                const examDateInput = document.getElementById('exam_date');
                if (examDateInput) {
                    if (startDate) examDateInput.min = startDate;
                    if (endDate) examDateInput.max = endDate;
                } else {
                    setTimeout(setExamDateLimits, 100);
                }
            }
            setExamDateLimits();
        }
    }
    fetchExaminations();
});
// ============ EXAM SCHEDULING AJAX (operations/exam_scheduling.html) ============
document.addEventListener('DOMContentLoaded', function () {
    // Only run on exam scheduling page
    if (!document.getElementById('exam-schedule-groups-table')) return;

    function fetchFilters() {
        fetch('/ops/ajax/exam-scheduling/filters/')
            .then(resp => resp.json())
            .then(data => {
                const yearSel = document.getElementById('filterYear');
                const semSel = document.getElementById('filterSem');
                const regSel = document.getElementById('filterRegulation');
                if (yearSel && data.academic_years) {
                    yearSel.innerHTML = '<option value="">All Years</option>' + data.academic_years.map(y => `<option value="${y}">${y}</option>`).join('');
                }
                if (semSel && data.semesters) {
                    semSel.innerHTML = '<option value="">All Semesters</option>' + data.semesters.map(s => `<option value="${s}">${s}</option>`).join('');
                }
                if (regSel && data.regulations) {
                    regSel.innerHTML = '<option value="">All Regulations</option>' + data.regulations.map(r => `<option value="${r}">${r}</option>`).join('');
                }
            });
    }

    function fetchGroups() {
        // Only send slot_id; backend will use it to fetch academic_year and semester
        const slotId = window.examSlotId || document.getElementById('examScheduleGroupsForm').dataset.slotId;
        const params = new URLSearchParams({ slot_id: slotId });
        fetch('/ops/ajax/exam-scheduling/groups/?' + params.toString())
            .then(resp => resp.json())
            .then(data => {
                const tbody = document.querySelector('#exam-schedule-groups-table tbody');
                const form = document.getElementById('examScheduleGroupsForm');
                if (!tbody || !form) return;
                const confirmBtn = document.getElementById('confirmScheduleBtn');
                if (data.groups && data.groups.length) {
                    tbody.innerHTML = data.groups.map(group => {
                        const disabled = group.clash ? 'disabled' : '';
                        const clashStyle = group.clash ? 'background:#ffe6e6;color:#b30000;' : '';
                        const clashMsg = group.clash ? '<div style="color:#b30000;font-size:0.9em;">Clash: Student has another exam in this slot</div>' : '';
                        const studentIds = group.student_ids ? group.student_ids.join(',') : '';
                        return `
                        <tr style="${clashStyle}">
                            <td><input type="checkbox" name="selected_groups" value="${group.course_code}|${group.regulation}|${group.academic_year}|${group.semester}" ${disabled} ${group.clash ? 'tabindex="-1" aria-disabled="true"' : ''}></td>
                            <td>${group.course_code}</td>
                            <td>${group.course_name}</td>
                            <td>${group.registration_type}</td>
                            <td>${group.regulation}</td>
                            <td>${group.academic_year}</td>
                            <td>${group.semester}</td>
                            <td data-students="${studentIds}">${group.student_count}${clashMsg}</td>
                        </tr>
                        `;
                    }).join('');
                    form.style.display = '';
                    if (confirmBtn) confirmBtn.style.display = '';
                } else {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No course registrations found for the selected filters.</td></tr>';
                    form.style.display = '';
                    if (confirmBtn) confirmBtn.style.display = 'none';
                }
            });
    }

    // Initial load
    fetchFilters();
    // Do not hide table/form on load; let fetchGroups control visibility

    // Filter event listeners and fetch button removed since filters are no longer present.

    // Show/hide confirm button based on selection
    var examScheduleGroupsFormElem = document.getElementById('examScheduleGroupsForm');
    if (examScheduleGroupsFormElem) {
        examScheduleGroupsFormElem.addEventListener('change', function (e) {
            const confirmBtn = document.getElementById('confirmScheduleBtn');
            const checked = examScheduleGroupsFormElem.querySelectorAll('input[name="selected_groups"]:checked');
            if (confirmBtn) confirmBtn.style.display = checked.length ? '' : 'none';
        });
        // Prevent form submit if no group is selected
        examScheduleGroupsFormElem.addEventListener('submit', function (e) {
            const checked = examScheduleGroupsFormElem.querySelectorAll('input[name="selected_groups"]:checked');
            if (!checked.length) {
                e.preventDefault();
                alert('Please select at least one group to schedule.');
            }
        });
    }

    // Auto-fetch exam scheduling data on page load
    fetch('/ops/ajax/exam-scheduling/filters/')
        .then(resp => resp.json())
        .then(data => {
            // Use the first available academic_year and semester
            let year = Array.isArray(data.academic_years) && data.academic_years.length ? data.academic_years[0] : '';
            let sem = Array.isArray(data.semesters) && data.semesters.length ? data.semesters[0] : '';
            let reg = Array.isArray(data.regulations) && data.regulations.length ? data.regulations[0] : '';
            if (typeof fetchGroups === 'function') {
                fetchGroups(year, sem, reg);
            }
        });

    function fetchGroups(year, sem, reg) {
        year = year || '';
        sem = sem || '';
        reg = reg || '';
        const slotId = window.examSlotId || document.getElementById('examScheduleGroupsForm').dataset.slotId;
        const params = new URLSearchParams({ academic_year: year, semester: sem, regulation: reg, slot_id: slotId });
        fetch('/ops/ajax/exam-scheduling/groups/?' + params.toString())
            .then(resp => resp.json())
            .then(data => {
                const tbody = document.querySelector('#exam-schedule-groups-table tbody');
                const form = document.getElementById('examScheduleGroupsForm');
                if (!tbody || !form) return;
                const confirmBtn = document.getElementById('confirmScheduleBtn');
                if (data.groups && data.groups.length) {
                    const isLocked = form.dataset.locked === 'true';
                    tbody.innerHTML = data.groups.map(group => {
                        const disabledAttr = (group.clash || isLocked) ? 'disabled' : '';
                        const clashStyle = group.clash ? 'background:#ffe6e6;color:#b30000;' : '';
                        const clashMsg = group.clash ? '<div style="color:#b30000;font-size:0.9em;">Clash: Student has another exam in this slot</div>' : '';
                        const studentIds = group.student_ids ? group.student_ids.join(',') : '';
                        const isChecked = group.is_already_scheduled ? 'checked' : '';
                        const rowStyle = group.is_already_scheduled ? 'background: #e6f9e6;' : '';
                        const assignedLabel = group.is_already_scheduled ? ' <span style="color:#1a7f1a; font-weight:600; font-size:0.85em;">(Already Assigned)</span>' : '';
                        
                        return `
                        <tr style="${clashStyle}${rowStyle}">
                            <td><input type="checkbox" name="selected_groups" value="${group.course_code}|${group.regulation}|${group.academic_year}|${group.semester}" ${isChecked} ${disabledAttr} ${group.clash ? 'tabindex="-1" aria-disabled="true"' : ''}></td>
                            <td>${group.course_code}</td>
                            <td>${group.course_name}${assignedLabel}</td>
                            <td>${group.registration_type}</td>
                            <td>${group.regulation}</td>
                            <td>${group.academic_year}</td>
                            <td>${group.semester}</td>
                            <td data-students="${studentIds}">${group.student_count}${clashMsg}</td>
                        </tr>
                        `;
                    }).join('');
                    form.style.display = '';
                    if (confirmBtn) confirmBtn.style.display = '';
                } else {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No course registrations found for the selected filters.</td></tr>';
                    form.style.display = '';
                    if (confirmBtn) confirmBtn.style.display = 'none';
                }
            });
    }
    // Select all groups checkbox (re-bind after table update)
    document.addEventListener('change', function (e) {
        if (e.target && e.target.id === 'selectAllGroups') {
            document.querySelectorAll('input[name="selected_groups"]').forEach(cb => {
                cb.checked = e.target.checked;
            });
        }
        // Real-time clash detection (optimized)
        if (e.target && e.target.name === 'selected_groups') {
            // Cache student lists for each row
            const allCheckboxes = Array.from(document.querySelectorAll('input[name="selected_groups"]'));
            const rowStudentMap = new Map();
            allCheckboxes.forEach(cb => {
                const row = cb.closest('tr');
                const students = row.children[7].dataset.students ? row.children[7].dataset.students.split(',') : [];
                rowStudentMap.set(cb, students);
            });
            // Build a Set of all selected student IDs
            const checked = allCheckboxes.filter(cb => cb.checked);
            const selectedStudentSet = new Set();
            checked.forEach(cb => {
                rowStudentMap.get(cb).forEach(sid => selectedStudentSet.add(sid));
            });
            // For each checkbox, check if its students overlap with selectedStudentSet
            allCheckboxes.forEach(cb => {
                if (!cb.checked) {
                    const students = rowStudentMap.get(cb);
                    const clash = students.some(sid => selectedStudentSet.has(sid));
                    const row = cb.closest('tr');
                    if (clash) {
                        cb.disabled = true;
                        row.style.background = '#ffe6e6';
                        row.style.color = '#b30000';
                    } else {
                        cb.disabled = false;
                        row.style.background = '';
                        row.style.color = '';
                    }
                }
            });
        }
    });
});
// ============ EXAM SLOT CREATION (operations/exams.html) ============
// JS validation removed; backend handles all validation and messaging.
document.addEventListener('DOMContentLoaded', function () {
    const createLink = document.getElementById('createExamSlotLink');
    const form = document.getElementById('examSlotForm');
    if (createLink && form) {
        createLink.addEventListener('click', function (e) {
            e.preventDefault();
            form.submit();
        });
    }
});
document.addEventListener('DOMContentLoaded', function () {
    // ============ COURSE EDIT/DELETE MODALS ============
    // Edit modal logic
    const editModal = document.getElementById('editCourseModal');
    const editForm = document.getElementById('editCourseForm');
    const closeEditBtn = document.getElementById('closeEditModal');
    document.querySelectorAll('.edit-course-btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            document.getElementById('editCourseId').value = btn.dataset.id;
            document.getElementById('editCourseCode').value = btn.dataset.code;
            document.getElementById('editCourseName').value = btn.dataset.name;
            document.getElementById('editCourseActive').value = btn.dataset.active === 'True' ? 'true' : 'false';
            editModal.style.display = 'flex';
        });
    });
    if (closeEditBtn) closeEditBtn.onclick = () => { editModal.style.display = 'none'; };
    if (editModal) editModal.onclick = e => { if (e.target === editModal) editModal.style.display = 'none'; };

    // Delete modal logic
    const deleteModal = document.getElementById('deleteCourseModal');
    const deleteForm = document.getElementById('deleteCourseForm');
    const closeDeleteBtn = document.getElementById('closeDeleteModal');
    document.querySelectorAll('.delete-course-btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            document.getElementById('deleteCourseId').value = btn.dataset.id;
            deleteModal.style.display = 'flex';
        });
    });
    if (closeDeleteBtn) closeDeleteBtn.onclick = () => { deleteModal.style.display = 'none'; };
    if (deleteModal) deleteModal.onclick = e => { if (e.target === deleteModal) deleteModal.style.display = 'none'; };

    // AJAX for edit
    if (editForm) {
        editForm.onsubmit = function (e) {
            e.preventDefault();
            const id = document.getElementById('editCourseId').value;
            const code = document.getElementById('editCourseCode').value;
            const name = document.getElementById('editCourseName').value;
            const is_active = document.getElementById('editCourseActive').value === 'true';
            fetch(`/masters/courses/${id}/edit/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({ course_code: code, course_name: name, is_active: is_active })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        // Show notification after reload
                        localStorage.setItem('course_notify', 'Course updated successfully.');
                        window.location.reload();
                    } else {
                        alert(data.error || 'Failed to update course.');
                    }
                });
        };
    }
    // AJAX for delete
    if (deleteForm) {
        deleteForm.onsubmit = function (e) {
            e.preventDefault();
            const id = document.getElementById('deleteCourseId').value;
            fetch(`/masters/courses/${id}/delete/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        localStorage.setItem('course_notify', 'Course deleted successfully.');
                        window.location.reload();
                    } else {
                        alert(data.error || 'Failed to delete course.');
                    }
                    // Show notification if present in localStorage
                    const msg = localStorage.getItem('course_notify');
                    if (msg) {
                        let popup = document.createElement('div');
                        popup.className = 'popup-message popup-success';
                        popup.innerText = msg;
                        popup.style.position = 'fixed';
                        popup.style.top = '30px';
                        popup.style.left = '50%';
                        popup.style.transform = 'translateX(-50%)';
                        popup.style.zIndex = 99999;
                        popup.style.background = '#38a169';
                        popup.style.color = '#fff';
                        popup.style.padding = '16px 32px';
                        popup.style.borderRadius = '8px';
                        popup.style.fontSize = '1.1rem';
                        popup.style.boxShadow = '0 2px 12px rgba(30,58,95,0.18)';
                        document.body.appendChild(popup);
                        setTimeout(() => { popup.remove(); }, 2500);
                        localStorage.removeItem('course_notify');
                    }
                });
        };
    }

    // ============ PIE CHART FOR DASHBOARD ============
    const pie = document.getElementById('userPieChart');
    if (pie) {
        const adminCount = Number(pie.getAttribute('data-admin'));
        const facultyCount = Number(pie.getAttribute('data-faculty'));
        const studentCount = Number(pie.getAttribute('data-student'));
        const total = adminCount + facultyCount + studentCount;
        const data = [adminCount, facultyCount, studentCount];
        const labels = [
            `Admin (${adminCount})`,
            `Faculty (${facultyCount})`,
            `Students (${studentCount})`
        ];
        const ctx = pie.getContext('2d');
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#2563eb', // Vivid blue
                        '#10b981', // Vivid green
                        '#f59e42'  // Vivid orange
                    ],
                    borderColor: [
                        'rgba(0,0,0,0)',
                        'rgba(0,0,0,0)',
                        'rgba(0,0,0,0)'
                    ],
                    borderWidth: 0,
                    hoverOffset: 14,
                    borderRadius: 0 // sharp edges
                }]
            },
            options: {
                responsive: true,
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 900,
                    easing: 'easeOutCubic'
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            font: { size: 16, family: 'Poppins, Arial' },
                            color: '#1E3A5F',
                            padding: 18,
                            boxWidth: 22,
                            usePointStyle: true,
                            pointStyle: 'rect'
                        }
                    },
                    tooltip: {
                        backgroundColor: '#fff',
                        titleColor: '#1E3A5F',
                        bodyColor: '#1E3A5F',
                        borderColor: '#2563eb',
                        borderWidth: 1,
                        padding: 14,
                        cornerRadius: 8,
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed;
                                const percent = total ? ((value / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${value} (${percent}%)`;
                            }
                        }
                    }
                },
                layout: {
                    padding: 10
                },
                hover: {
                    mode: 'nearest',
                    intersect: true,
                    animationDuration: 400
                }
            },
            plugins: [
                {
                    id: 'piePercentLabels',
                    afterDraw(chart) {
                        const { ctx, chartArea, data } = chart;
                        if (!chartArea) return;
                        chart.getDatasetMeta(0).data.forEach((arc, i) => {
                            const value = data.datasets[0].data[i];
                            const percent = total ? ((value / total) * 100).toFixed(1) : 0;
                            const model = arc;
                            const angle = (model.startAngle + model.endAngle) / 2;
                            // For small values, move label closer to center
                            let radius = model.outerRadius - 38;
                            if (percent < 10) radius = model.outerRadius - 60;
                            const x = model.x + Math.cos(angle) * radius;
                            const y = model.y + Math.sin(angle) * radius;
                            ctx.save();
                            ctx.font = 'bold 15px Poppins, Arial';
                            ctx.fillStyle = '#1E3A5F';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';
                            ctx.fillText(percent + '%', x, y);
                            ctx.restore();
                        });
                    }
                }
            ]
        });
    }
});
// [Deleted redundant legacy print/download functions and handlers]

// ============ FACULTY DELETE MODAL (AJAX, JS-only) ============
// ============ FACULTY DELETE MODAL (Global Delegation) ============
$(document).on('click', '.faculty-delete-btn', function () {
    const btn = $(this);
    const facultyId = btn.data('faculty-id');
    const facultyName = btn.data('faculty-name');
    const facultyEmail = btn.data('faculty-email');
    const facultyDept = btn.data('faculty-dept');
    const facultyPhone = btn.data('faculty-phone');
    const facultyDesignation = btn.data('faculty-designation');
    const facultyStatus = btn.data('faculty-status');

    let facultyModal = $('#facultyDeleteModal');
    let facultyModalContent = $('#facultyDeleteModalContent');

    facultyModalContent.html(`
        <div class="delete-form">
          <h2>Delete Faculty</h2>
          <div style='text-align:left;font-size:0.98em;color:#000;margin-bottom:12px;'>
            <strong>Name:</strong> ${facultyName}<br>
            <strong>Email:</strong> ${facultyEmail}<br>
            <strong>Department:</strong> ${facultyDept}<br>
            <strong>Phone:</strong> ${facultyPhone}<br>
            <strong>Designation:</strong> ${facultyDesignation}<br>
            <strong>Status:</strong> ${facultyStatus}
          </div>
          <p>Are you sure you want to delete <strong>${facultyName}</strong>?</p>
          <form id="deleteFacultyForm" method="post" style="margin-bottom:0;">
            <input type="hidden" name="faculty_id" value="${facultyId}">
            <button type="submit">Confirm Delete</button>
          </form>
          <button type="button" id="cancelFacultyDeleteBtn" class="action-link" style="margin-top:12px;">Cancel</button>
        </div>
    `);
    facultyModal.css('display', 'flex');
});

$(document).on('click', '#cancelFacultyDeleteBtn', function() {
    $('#facultyDeleteModal').hide();
});

$(document).on('submit', '#deleteFacultyForm', function (e) {
    e.preventDefault();
    const facultyId = $(this).find('input[name="faculty_id"]').val();
    const url = `/masters/faculty/${facultyId}/delete/`;
    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

    $.ajax({
        url: url,
        type: 'POST',
        data: { csrfmiddlewaretoken: csrfToken },
        success: function(resp) {
            showPopup('Faculty deleted successfully.', 'success');
            $('#facultyDeleteModal').hide();
            setTimeout(() => { 
                if (typeof facultyTable !== 'undefined' && facultyTable.fetchFaculty) {
                    facultyTable.fetchFaculty(1);
                } else {
                    window.location.reload();
                }
            }, 1000);
        },
        error: function() {
            showPopup('Failed to delete faculty.', 'error');
            $('#facultyDeleteModal').hide();
        }
    });
});

// ============ STUDENT DELETE MODAL (AJAX) ============
// ============ STUDENT DELETE MODAL (Global Delegation) ============
$(document).on('click', '.student-delete-btn', function () {
    const btn = $(this);
    const studentId = btn.data('student-id');
    const studentName = btn.data('student-name');
    const studentReg = btn.data('student-reg');
    const studentEmail = btn.data('student-email');
    const studentDept = btn.data('student-dept');
    const studentStatus = btn.data('student-status');

    let studentModal = $('#studentDeleteModal');
    let studentModalContent = $('#studentDeleteModalContent');

    studentModalContent.html(`
        <div class="delete-form">
          <h2>Delete Student</h2>
          <div style='text-align:left;font-size:0.98em;color:#000;margin-bottom:12px;'>
            <strong>Name:</strong> ${studentName}<br>
            <strong>Student ID:</strong> ${studentReg}<br>
            <strong>Email:</strong> ${studentEmail}<br>
            <strong>Department:</strong> ${studentDept}<br>
            <strong>Status:</strong> ${studentStatus}
          </div>
          <p>Are you sure you want to delete student <strong>${studentName}</strong>?</p>
          <form id="deleteStudentFormAjax" method="post" style="margin-bottom:0;">
            <input type="hidden" name="student_id" value="${studentId}">
            <button type="submit">Confirm Delete</button>
          </form>
          <button type="button" id="cancelStudentDeleteBtn" class="action-link" style="margin-top:12px;">Cancel</button>
        </div>
    `);
    studentModal.css('display', 'flex');
});

$(document).on('click', '#cancelStudentDeleteBtn', function() {
    $('#studentDeleteModal').hide();
});

$(document).on('submit', '#deleteStudentFormAjax', function (e) {
    e.preventDefault();
    const sId = $(this).find('input[name="student_id"]').val();
    const url = `/masters/student/${sId}/delete/`;
    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

    $.ajax({
        url: url,
        type: 'POST',
        data: { csrfmiddlewaretoken: csrfToken },
        success: function(resp) {
            showPopup('Student deleted successfully.', 'success');
            $('#studentDeleteModal').hide();
            setTimeout(() => { 
                if (typeof studentsTable !== 'undefined' && studentsTable.fetchStudents) {
                    studentsTable.fetchStudents(1);
                } else {
                    window.location.reload();
                }
            }, 1000);
        },
        error: function() {
            showPopup('Failed to delete student.', 'error');
            $('#studentDeleteModal').hide();
        }
    });
});

// ============ GLOBAL POPUP FUNCTION ============
function showPopup(message, type) {
    let popupContainer = document.getElementById('popup-messages');
    if (!popupContainer) {
        popupContainer = document.createElement('div');
        popupContainer.id = 'popup-messages';
        popupContainer.style.position = 'fixed';
        popupContainer.style.top = '32px';
        popupContainer.style.right = '32px';
        popupContainer.style.zIndex = '2000';
        document.body.appendChild(popupContainer);
    }
    const popup = document.createElement('div');
    popup.className = `popup-message popup-${type}`;
    popup.tabIndex = 0;
    popup.textContent = message;
    popupContainer.appendChild(popup);
    setTimeout(() => { popup.remove(); }, 2000);
}

// ============ ROOM FUNCTIONS ============
function initializeRoomFilters() {
    const searchInput = document.getElementById('room-search');
    const blockSelect = document.getElementById('room-block');
    const minCapInput = document.getElementById('capacity-min');
    const maxCapInput = document.getElementById('capacity-max');
    const resetBtn = document.getElementById('resetRoomFilters');
    const roomsListBody = document.getElementById('rooms-list'); // Get tbody reference
    const rows = roomsListBody ? Array.from(roomsListBody.querySelectorAll('tr')) : []; // Get current rows
    const printBtn = document.getElementById('printRoomBtn'); // Get print button
    const downloadBtn = document.getElementById('downloadRoomBtn'); // Get download button

    function filterRooms() {
        const search = searchInput.value.toLowerCase();
        const block = blockSelect.value;
        const minCap = parseInt(minCapInput.value) || 0;
        const maxCap = parseInt(maxCapInput.value) || Infinity;

        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length < 4) { // Minimum cells required to perform checks
                row.style.display = 'none';
                return;
            }
            const roomId = cells[1].textContent.toLowerCase();
            const roomBlock = cells[2].textContent.trim();
            const roomCap = parseInt(cells[3].textContent) || 0;

            const matchSearch = !search || roomId.includes(search) || roomBlock.toLowerCase().includes(search);
            const matchBlock = block === 'All' || roomBlock === block;
            const matchCapacity = roomCap >= minCap && roomCap <= maxCap;

            row.style.display = (matchSearch && matchBlock && matchCapacity) ? '' : 'none';
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            searchInput.value = '';
            blockSelect.value = 'All';
            minCapInput.value = '';
            maxCapInput.value = '';
            filterRooms();
        });
    }

    // --- NEW: Attach listeners for Print and Download buttons here ---
    if (printBtn) {
        printBtn.onclick = printRoomTable; // Use onclick to overwrite previous listeners
    } else {
        console.error('printRoomBtn not found after content load');
    }
    if (downloadBtn) {
        downloadBtn.onclick = downloadRoomCSV; // Use onclick to overwrite previous listeners
    } else {
        console.error('downloadRoomBtn not found after content load');
    }
    // --- END NEW ---

    // Ensure all elements exist before adding listeners to avoid errors
    if (!searchInput || !blockSelect || !minCapInput || !maxCapInput || !roomsListBody) return;

    searchInput.addEventListener('input', filterRooms);
    blockSelect.addEventListener('change', filterRooms);
    minCapInput.addEventListener('input', filterRooms);
    maxCapInput.addEventListener('input', filterRooms);

    filterRooms(); // run initially
}

function printRoomTable() {
    const table = document.getElementById('room-table');
    if (!table) return;

    const cloneTable = table.cloneNode(true);
    const headerRow = cloneTable.querySelector("thead tr");
    if (headerRow && headerRow.children.length > 0) headerRow.lastElementChild.remove(); // Remove actions header

    const visibleRows = Array.from(table.querySelectorAll("tbody tr")).filter( // Use original table for visibility
        row => row.style.display !== "none"
    );

    const tbody = cloneTable.querySelector("tbody");
    tbody.innerHTML = ""; // Clear existing rows in clone

    visibleRows.forEach(row => {
        const cloneRow = row.cloneNode(true);
        if (cloneRow.children.length > 0) cloneRow.lastElementChild.remove(); // Remove actions cell
        tbody.appendChild(cloneRow);
    });

    const newWindow = window.open("", "_blank");
    if (!newWindow) return alert("Popup blocked!");

    newWindow.document.write(`
        <html><head><title>Print Room Data</title>
        <style>
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #000; padding: 8px; text-align: left; }
            th { background-color: #1E3A5F; color: white; }
        </style></head><body>
        <h2>Room Data</h2>
        ${cloneTable.outerHTML}
        </body></html>
    `);
    newWindow.document.close();
    newWindow.focus();
    newWindow.print();
}

function downloadRoomCSV() {
    const table = document.getElementById('room-table');
    if (!table) return;

    const rows = Array.from(document.querySelectorAll('#rooms-list tr'))
        .filter(row => row.style.display !== 'none');

    if (!rows.length) return alert('No data to download.');

    const headers = Array.from(table.querySelectorAll('thead th'))
        .slice(0, -1) // Exclude the last header ("Actions")
        .map(th => `"${th.textContent.trim()}"`)
        .join(',');

    const data = rows.map(row => {
        return Array.from(row.querySelectorAll('td'))
            .slice(0, -1) // Exclude the last cell ("Actions")
            .map(td => `"${td.textContent.trim()}"`)
            .join(',');
    });

    const csvContent = [headers, ...data].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'rooms_data.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ============ SIDEBAR ACTIVE LINK SCRIPT ============
document.addEventListener("DOMContentLoaded", function () {
    // Select all sidebar links
    const sidebarLinks = document.querySelectorAll('.sidebar-links ul li a');
    const currentPath = window.location.pathname.replace(/\/$/, '');

    sidebarLinks.forEach(link => {
        const linkPath = link.pathname.replace(/\/$/, '');
        if (linkPath === currentPath) {
            // Add active to both <a> and parent <li>
            link.classList.add('active');
            if (link.parentElement && link.parentElement.tagName === 'LI') {
                link.parentElement.classList.add('active');
            }
        }
    });
});

// ============ GLOBAL INITIALIZER ============
document.addEventListener("DOMContentLoaded", () => {
    console.log('DOM fully loaded');
    // The initial call to these functions ensures filters work on first load
    // And also attaches the print/download listeners if the table is present initially.
    initializeContentScripts(window.location.pathname); // Call for the current page
});

// Function to call appropriate initialization after AJAX content load
function initializeContentScripts(pageUrl) {
    // Student Management logic
    if (pageUrl.includes('/student/') && typeof studentsTable !== 'undefined') {
        // initialization if needed
    }
    // Faculty Management logic
    if (pageUrl.includes('/faculty/') && typeof facultyTable !== 'undefined') {
        // initialization if needed
    }
    // Room Management
    if (pageUrl.includes('/room/') && typeof initializeRoomFilters === 'function') {
        initializeRoomFilters();
    }
}

// Users Table AJAX and Pagination
window.usersTable = {
    USERS_URL: '/ajax/users/',
    currentPage: 1,
    fetchUsers: function (page = 1) {
        let params = { page };
        $("#filter-row .users-filter-input").each(function () {
            const field = $(this).data("field");
            const value = $(this).val();
            if (field && value) params[field] = value;
        });
        $.ajax({
            url: this.USERS_URL,
            data: params,
            dataType: "json",
            success: function (data) {
                usersTable.renderTable(data.users);
                usersTable.renderPagination(data.current_page, data.num_pages);
            }
        });
    },
    renderTable: function (users) {
        let html = "";
        users.forEach(function (u) {
            html += `<tr>
                <td>${u.username}</td>
                <td>${u.email}</td>
                <td>${u.first_name}</td>
                <td>${u.last_name}</td>
                <td>${u.role}</td>
                <td>${u.last_login && u.last_login.trim() ? u.last_login : '-'}</td>
            </tr>`;
        });
        $("#users-table-body").html(html);
    },
    renderPagination: function (current, total) {
        let html = "";
        let start = Math.max(1, current - 4);
        let end = Math.min(total, start + 9);
        if (end - start < 9) start = Math.max(1, end - 9);
        // First page button
        if (current > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">&laquo;&laquo;</a></li>`;
        }
        // Previous page button
        if (current > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${current - 1}">&laquo;</a></li>`;
        }
        for (let i = start; i <= end; i++) {
            html += `<li class="page-item${i === current ? ' active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
        }
        // Next page button
        if (current < total) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${current + 1}">&raquo;</a></li>`;
        }
        // Last page button
        if (current < total) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${total}">&raquo;&raquo;</a></li>`;
        }
        $("#users-pagination").html(html);
    },
    bindEvents: function () {
        $(document).on("keyup change", ".users-filter-input", function () {
            usersTable.fetchUsers(1);
        });
        $(document).on("click", "#users-pagination .page-link", function (e) {
            e.preventDefault();
            const page = parseInt($(this).data("page"));
            if (page && page !== usersTable.currentPage) {
                usersTable.currentPage = page;
                usersTable.fetchUsers(page);
            }
        });
    },
    init: function () {
        usersTable.fetchUsers();
        usersTable.bindEvents();
    }
};
$(document).ready(function () {
    if (document.getElementById('users-table')) {
        usersTable.init();
    }
});

// ============ STUDENTS TABLE (AJAX) ============
window.studentsTable = {
    STUDENTS_URL: '/masters/ajax/',
    currentPage: 1,
    fetchStudents: function (page = 1) {
        let params = { type: 'student', page };
        // Get search, department, batch (regulation) filter values
        params['search'] = $("#search").val() || '';
        params['department'] = $("#department").val() || 'all';
        params['batch'] = $("#batch").val() || 'all';
        $.ajax({
            url: this.STUDENTS_URL,
            data: params,
            dataType: "json",
            success: function (data) {
                $("#student-list").html(data.table_html);
                $("#studentPaginationBar").html(data.pagination_html);
                // Re-initialize master table logic if needed
                if (typeof initializeContentScripts === 'function') {
                    // (Optional: can call if we have other scripts to run)
                }
            }
        });
    },
    bindEvents: function () {
        // On filter change
        $(document).on("change", "#department, #batch", function () {
            studentsTable.fetchStudents(1);
        });
        // On search input
        $(document).on("input", "#search", function () {
            studentsTable.fetchStudents(1);
        });
        // On pagination click
        $(document).on("click", "#studentPaginationBar .page-arrow, #studentPaginationBar .page-num", function (e) {
            e.preventDefault();
            const page = parseInt($(this).data("page"));
            if (page && page !== studentsTable.currentPage) {
                studentsTable.currentPage = page;
                studentsTable.fetchStudents(page);
            }
        });
        // Reset filters
        $(document).on("click", "#resetStudentFilters", function () {
            $("#search").val("");
            $("#department").val("all");
            $("#batch").val("all");
            setTimeout(function () { studentsTable.fetchStudents(1); }, 0);
        });
    },
    init: function () {
        studentsTable.fetchStudents();
        studentsTable.bindEvents();
    }
};

$(document).ready(function () {
    if (document.getElementById('student-table')) {
        studentsTable.init();
    }
});

// ============ FACULTY TABLE (AJAX) ============
window.facultyTable = {
    FACULTY_URL: '/masters/ajax/',
    currentPage: 1,
    fetchFaculty: function (page = 1) {
        let params = { type: 'faculty', page };
        params['search'] = $("#search").val() || '';
        params['department'] = $("#department").val() || 'all';
        $.ajax({
            url: this.FACULTY_URL,
            data: params,
            dataType: "json",
            success: function (data) {
                $("#faculty-list").html(data.table_html);
                $(".pagination-bar").html(data.pagination_html);
                if (typeof initializeContentScripts === 'function') {
                    initializeContentScripts(window.location.pathname);
                }
            }
        });
    },
    bindEvents: function () {
        $(document).on("change", "#department", function () {
            facultyTable.fetchFaculty(1);
        });
        $(document).on("input", "#search", function () {
            facultyTable.fetchFaculty(1);
        });
        $(document).on("click", ".pagination-bar .page-arrow, .pagination-bar .page-num", function (e) {
            e.preventDefault();
            const page = $(this).data("page");
            if (page && page !== facultyTable.currentPage) {
                facultyTable.currentPage = page;
                facultyTable.fetchFaculty(page);
            }
        });
        $(document).on("click", "#resetFacultyFilters", function () {
            $("#search").val("");
            $("#department").val("all");
            setTimeout(function () { facultyTable.fetchFaculty(1); }, 0);
        });
    },
    init: function () {
        facultyTable.fetchFaculty();
        facultyTable.bindEvents();
    }
};

$(document).ready(function () {
    if (document.getElementById('faculty-table')) {
        facultyTable.init();
    }
});
// ============ BATCHES TABLE ============
window.batchesTable = {
    BATCHES_URL: '/ajax/batches/',
    currentPage: 1,
    fetchBatches: function (page = 1) {
        let params = { page };
        $("#batch-filter-row .batches-filter-input").each(function () {
            const field = $(this).data("field");
            const value = $(this).val();
            if (field && value) params[field] = value;
        });
        $.ajax({
            url: this.BATCHES_URL,
            data: params,
            dataType: "json",
            success: function (data) {
                batchesTable.renderTable(data.batches);
                batchesTable.renderPagination(data.current_page, data.num_pages);
            }
        });
    },
    renderTable: function (batches) {
        let html = "";
        batches.forEach(function (b) {
            html += `<tr>
                <td>${b.batch_code}</td>
                <td>${b.admission_year}</td>
                <td>${b.grad_year}</td>
                <td>${b.status}</td>
            </tr>`;
        });
        $("#batches-table-body").html(html);
    },
    renderPagination: function (current, total) {
        let html = "";
        let start = Math.max(1, current - 4);
        let end = Math.min(total, start + 9);
        if (end - start < 9) start = Math.max(1, end - 9);
        if (current > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">&laquo;&laquo;</a></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${current - 1}">&laquo;</a></li>`;
        }
        for (let i = start; i <= end; i++) {
            html += `<li class="page-item${i === current ? ' active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
        }
        if (current < total) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${current + 1}">&raquo;</a></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${total}">&raquo;&raquo;</a></li>`;
        }
        $("#batches-pagination").html(html);
    },
    bindEvents: function () {
        $(document).on("keyup change", ".batches-filter-input", function () {
            batchesTable.fetchBatches(1);
        });
        $(document).on("click", "#batches-pagination .page-link", function (e) {
            e.preventDefault();
            const page = parseInt($(this).data("page"));
            if (page && page !== batchesTable.currentPage) {
                batchesTable.currentPage = page;
                batchesTable.fetchBatches(page);
            }
        });
    },
    init: function () {
        batchesTable.fetchBatches();
        batchesTable.bindEvents();
    }
};

// ============ DEPARTMENTS TABLE ============
window.departmentsTable = {
    DEPARTMENTS_URL: '/ajax/departments/',
    currentPage: 1,
    fetchDepartments: function (page = 1) {
        let params = { page };
        $("#department-filter-row .departments-filter-input").each(function () {
            const field = $(this).data("field");
            const value = $(this).val();
            if (field && value) params[field] = value;
        });
        $.ajax({
            url: this.DEPARTMENTS_URL,
            data: params,
            dataType: "json",
            success: function (data) {
                departmentsTable.renderTable(data.departments);
                departmentsTable.renderPagination(data.current_page, data.num_pages);
            }
        });
    },
    renderTable: function (departments) {
        let html = "";
        departments.forEach(function (d) {
            html += `<tr>
                <td>${d.dept_code}</td>
                <td>${d.dept_name}</td>
                <td>${d.is_active}</td>
            </tr>`;
        });
        $("#departments-table-body").html(html);
    },
    renderPagination: function (current, total) {
        let html = "";
        let start = Math.max(1, current - 4);
        let end = Math.min(total, start + 9);
        if (end - start < 9) start = Math.max(1, end - 9);
        if (current > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">&laquo;&laquo;</a></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${current - 1}">&laquo;</a></li>`;
        }
        for (let i = start; i <= end; i++) {
            html += `<li class="page-item${i === current ? ' active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
        }
        if (current < total) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${current + 1}">&raquo;</a></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${total}">&raquo;&raquo;</a></li>`;
        }
        $("#departments-pagination").html(html);
    },
    bindEvents: function () {
        $(document).on("keyup change", ".departments-filter-input", function () {
            departmentsTable.fetchDepartments(1);
        });
        $(document).on("click", "#departments-pagination .page-link", function (e) {
            e.preventDefault();
            const page = parseInt($(this).data("page"));
            if (page && page !== departmentsTable.currentPage) {
                departmentsTable.currentPage = page;
                departmentsTable.fetchDepartments(page);
            }
        });
    },
    init: function () {
        departmentsTable.fetchDepartments();
        departmentsTable.bindEvents();
    }
};

// ============ PROGRAMS TABLE ============
window.programsTable = {
    PROGRAMS_URL: '/ajax/programs/',
    currentPage: 1,
    fetchPrograms: function (page = 1) {
        let params = { page };
        $("#program-filter-row .programs-filter-input").each(function () {
            const field = $(this).data("field");
            const value = $(this).val();
            if (field && value) params[field] = value;
        });
        $.ajax({
            url: this.PROGRAMS_URL,
            data: params,
            dataType: "json",
            success: function (data) {
                programsTable.renderTable(data.programs);
                programsTable.renderPagination(data.current_page, data.num_pages);
            }
        });
    },
    renderTable: function (programs) {
        let html = "";
        programs.forEach(function (p) {
            html += `<tr>
                <td>${p.program_code}</td>
                <td>${p.program_name}</td>
                <td>${p.is_active}</td>
            </tr>`;
        });
        $("#programs-table-body").html(html);
    },
    renderPagination: function (current, total) {
        let html = "";
        let start = Math.max(1, current - 4);
        let end = Math.min(total, start + 9);
        if (end - start < 9) start = Math.max(1, end - 9);
        if (current > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">&laquo;&laquo;</a></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${current - 1}">&laquo;</a></li>`;
        }
        for (let i = start; i <= end; i++) {
            html += `<li class="page-item${i === current ? ' active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
        }
        if (current < total) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${current + 1}">&raquo;</a></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${total}">&raquo;&raquo;</a></li>`;
        }
        $("#programs-pagination").html(html);
    },
    bindEvents: function () {
        $(document).on("keyup change", ".programs-filter-input", function () {
            programsTable.fetchPrograms(1);
        });
        $(document).on("click", "#programs-pagination .page-link", function (e) {
            e.preventDefault();
            const page = parseInt($(this).data("page"));
            if (page && page !== programsTable.currentPage) {
                programsTable.currentPage = page;
                programsTable.fetchPrograms(page);
            }
        });
    },
    init: function () {
        programsTable.fetchPrograms();
        programsTable.bindEvents();
    }
};

$(document).ready(function () {
    if (document.getElementById('batches-table')) {
        batchesTable.init();
    }
    if (document.getElementById('departments-table')) {
        departmentsTable.init();
    }
    if (document.getElementById('programs-table')) {
        programsTable.init();
    }
});

// ============ EXAMINATION FORM SUBMIT ============
document.addEventListener('DOMContentLoaded', function () {
    var examForm = document.getElementById('examinationForm');
    if (examForm) {
        examForm.addEventListener('submit', function (e) {
            // Optionally, add client-side validation here if needed
            // (HTML5 required/min already covers most cases)
            // Allow normal form submit for backend processing
        });
        // Dynamic end date min logic (already in template, but keep for robustness)
        var startInput = document.getElementById('start_date');
        var endInput = document.getElementById('end_date');
        function updateEndMin() {
            if (startInput.value) {
                endInput.min = startInput.value;
                if (endInput.value && endInput.value < startInput.value) {
                    endInput.value = '';
                }
            } else {
                endInput.min = startInput.min;
            }
        }
        startInput.addEventListener('change', updateEndMin);
        updateEndMin();
    }
});

// Rogue jQuery edit-exam-btn handler purged to favor global Vanilla JS listener

// ========== Data Export Manager (Student, Faculty, Room, Course) ==========
const ExportManager = {
    currentType: '', // 'student', 'faculty', 'room', 'course'
    currentAction: '', // 'print', 'download'
    
    init: function() {
        console.log("ExportManager Initialized");
        const modal = document.getElementById('exportOptionsModal');
        if (!modal) return;
        
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('button, a');
            if (!btn) return;
            
            const id = btn.id || '';
            // Match IDs like printStudentBtn, downloadFacultyBtn, printRoomBtn, etc.
            if (id.startsWith('print') || id.startsWith('download')) {
                const typeMatch = id.match(/(Student|Faculty|Room|Course|CourseReg)/i);
                if (typeMatch) {
                    e.preventDefault();
                    // Don't stop propagation if it's already an ExportManager button or similar
                    if (!id.includes('export')) {
                        this.currentType = typeMatch[1].toLowerCase();
                        this.currentAction = id.startsWith('print') ? 'print' : 'download';
                        this.showModal();
                    }
                }
            }
        });
        
        // Modal internal buttons
        const currentBtn = document.getElementById('exportCurrentBtn');
        const completeBtn = document.getElementById('exportCompleteBtn');
        const closeX = document.getElementById('closeExportModal');
        const cancelBtn = document.getElementById('cancelExportBtn');

        if (currentBtn) currentBtn.addEventListener('click', () => this.handleCurrent());
        if (completeBtn) completeBtn.addEventListener('click', () => this.handleComplete());
        if (closeX) closeX.addEventListener('click', () => this.hideModal());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.hideModal());
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.hideModal();
        });
    },
    
    showModal: function() {
        const modal = document.getElementById('exportOptionsModal');
        if (!modal) return;

        const title = document.getElementById('exportModalTitle');
        const text = document.getElementById('exportModalText');
        
        const actionLabel = this.currentAction === 'print' ? 'Print' : 'Download';
        const typeLabel = this.currentType.charAt(0).toUpperCase() + this.currentType.slice(1);
        
        if (title) title.innerText = `${actionLabel} ${typeLabel} Data`;
        if (text) text.innerText = `Choose the scope for your ${this.currentAction} action.`;
        
        modal.classList.add('active');
        modal.style.display = 'block';
    },
    
    hideModal: function() {
        const modal = document.getElementById('exportOptionsModal');
        if (modal) {
            modal.classList.remove('active');
            modal.style.display = 'none';
        }
    },
    
    handleCurrent: function() {
        this.hideModal();
        const table = document.querySelector('table'); 
        if (!table) {
            if (typeof showPopupMessage === 'function') showPopupMessage('No table found to export.', 'error');
            return;
        }
        
        // Clone and sanitize table for print
        const cloneTable = table.cloneNode(true);
        const headers = Array.from(cloneTable.querySelectorAll('thead th')).map(th => th.innerText.toLowerCase().trim());
        const excludeIndices = headers.map((h, i) => (h.includes('status') || h.includes('action')) ? i : -1).filter(i => i !== -1);
        
        // Remove excluded columns from header and rows
        const rows = cloneTable.querySelectorAll('tr');
        rows.forEach(row => {
            const cells = Array.from(row.children);
            // Reverse order to avoid index shifting problems
            excludeIndices.sort((a,b) => b-a).forEach(idx => {
                if (cells[idx]) row.removeChild(cells[idx]);
            });
        });

        // Ensure first column is S.NO and handle existing index columns
        const theadFirstTh = cloneTable.querySelector('thead tr th');
        if (theadFirstTh) {
            const txt = theadFirstTh.innerText.toLowerCase().trim();
            // Check if existing column is an index (common patterns)
            const isExistingIdx = txt === '#' || txt.includes('s.no') || txt.includes('idx') || txt === 'id' || txt === 'sl.no';
            
            if (isExistingIdx) {
                // Rename existing to S.NO for consistency
                theadFirstTh.innerText = 'S.NO';
            } else {
                // Add new S.NO column before the first one
                const theadRow = cloneTable.querySelector('thead tr');
                const th = document.createElement('th');
                th.innerText = 'S.NO';
                theadRow.insertBefore(th, theadRow.firstChild);
                
                const tbodyRows = cloneTable.querySelectorAll('tbody tr');
                tbodyRows.forEach((tr, i) => {
                    const td = document.createElement('td');
                    td.innerText = i + 1;
                    tr.insertBefore(td, tr.firstChild);
                });
            }
        }

        if (this.currentAction === 'print') {
            this.printTable(cloneTable.outerHTML);
        } else {
            this.downloadCSV(this.tableToCSV(cloneTable), `${this.currentType}_current_page.csv`);
        }
    },
    
    handleComplete: function(customParams = null) {
        this.hideModal();
        if (window.Loader) window.Loader.show(`Fetching complete ${this.currentType} data...`, "This may take a few seconds");

        // Get current filters from the URL/UI if no custom params provided
        let ajaxParams;
        if (customParams) {
            ajaxParams = new URLSearchParams(customParams);
        } else {
            const urlParams = new URLSearchParams(window.location.search);
            const searchQuery = document.querySelector('input[name="search"], #search-fac') ? 
                                (document.querySelector('input[name="search"]') || document.querySelector('#search-fac')).value : 
                                (urlParams.get('search') || '');
                                
            ajaxParams = new URLSearchParams({
                type: this.currentType,
                full_data: 'true',
                search: searchQuery,
                department: urlParams.get('department') || '',
                batch: urlParams.get('batch') || '',
                block: urlParams.get('block') || '',
                room_type: urlParams.get('room_type') || '',
                // Add CourseReg specific filters
                year: urlParams.get('year') || '',
                semester: urlParams.get('semester') || '',
                student_id: urlParams.get('student_id') || ''
            });
        }
        
        fetch(`/masters/ajax/?${ajaxParams.toString()}`)
            .then(resp => resp.json())
            .then(data => {
                if (window.Loader) window.Loader.hide();
                if (data.results) {
                    if (this.currentAction === 'print') {
                        this.printData(data.results);
                    } else {
                        this.downloadCSV(this.jsonToCSV(data.results), `${this.currentType}_complete_data.csv`);
                    }
                } else {
                    if (typeof showPopupMessage === 'function') showPopupMessage('No data received from server.', 'error');
                }
            })
            .catch(err => {
                console.error('Export failed:', err);
                if (window.Loader) window.Loader.hide();
                if (typeof showPopupMessage === 'function') showPopupMessage('Export failed. Please check console.', 'error');
            });
    },
    
    printTable: function(html) {
        const win = window.open('', '_blank', 'width=1100,height=800');
        const actionLabel = this.currentAction === 'print' ? 'Print' : 'Download';
        const typeLabel = this.currentType.charAt(0).toUpperCase() + this.currentType.slice(1);
        
        win.document.write(`
        <html>
        <head>
            <title>${typeLabel} Data Export</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                
                body { 
                    font-family: 'Inter', system-ui, -apple-system, sans-serif; 
                    color: #1e293b; 
                    margin: 40px; 
                    line-height: 1.5;
                }
                
                .print-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-end;
                    border-bottom: 2px solid #2563eb;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }
                
                .brand-info h1 { margin: 0; color: #1e3a8a; font-size: 24px; font-weight: 700; }
                .brand-info p { margin: 5px 0 0; color: #64748b; font-size: 14px; }
                
                .export-meta { text-align: right; }
                .export-meta div { font-size: 12px; color: #64748b; }
                .export-meta strong { color: #1e293b; display: block; font-size: 16px; margin-bottom: 4px; }
                
                table { width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: auto; }
                th { 
                    background-color: #f8fafc; 
                    color: #475569; 
                    font-weight: 600; 
                    font-size: 12px; 
                    text-transform: uppercase; 
                    letter-spacing: 0.05em;
                    padding: 12px 15px;
                    border: 1px solid #e2e8f0;
                    text-align: left;
                }
                td { 
                    padding: 12px 15px; 
                    border: 1px solid #e2e8f0; 
                    font-size: 13px; 
                    color: #1e293b;
                }
                tr:nth-child(even) { background-color: #fcfcfd; }
                
                @media print {
                    body { margin: 20px; }
                    .no-print { display: none; }
                    table { page-break-inside: auto; }
                    tr { page-break-inside: avoid; page-break-after: auto; }
                    thead { display: table-header-group; }
                    footer { display: table-footer-group; position: fixed; bottom: 0; }
                }
                
                .footer {
                    margin-top: 40px;
                    font-size: 11px;
                    color: #94a3b8;
                    text-align: center;
                    border-top: 1px solid #e2e8f0;
                    padding-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="print-header">
                <div class="brand-info">
                    <h1>Administrative Dashboard</h1>
                    <p>Digital Examination Administration System</p>
                </div>
                <div class="export-meta">
                    <strong>${typeLabel} Records Report</strong>
                    <div>Generated on: ${new Date().toLocaleString('en-IN')}</div>
                    <div>Source: System Central Database</div>
                </div>
            </div>
            
            ${html}
            
            <div class="footer">
                This is a system-generated report. All data is subject to institutional privacy policies.
                <br>Page 1 of 1
            </div>
            
            <script>
                window.onload = function() {
                    // Small delay to ensure styles are applied before print dialog
                    setTimeout(() => {
                        window.print();
                    }, 500);
                }
            </script>
        </body>
        </html>
        `);
        win.document.close();
    },
    
    printData: function(results) {
        if (!results.length) return;
        
        // Define columns to skip
        const skipKeys = ['status', 'is_active', 'id', 'user_id', 'dept_id', 'batch_id', 'idx', '#', 's_no', 's.no'];
        
        // Filter headers
        const rawHeaders = Object.keys(results[0]).filter(k => !skipKeys.includes(k.toLowerCase()));
        
        let html = '<table><thead><tr><th>S.NO</th>';
        rawHeaders.forEach(h => html += `<th>${h.replace(/_/g, ' ').toUpperCase()}</th>`);
        html += '</tr></thead><tbody>';
        
        results.forEach((row, index) => {
            html += `<tr><td>${index + 1}</td>`;
            rawHeaders.forEach(key => {
                const val = row[key];
                html += `<td>${val === null || val === undefined ? '-' : val}</td>`;
            });
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        this.printTable(html);
    },
    
    tableToCSV: function(table) {
        const rows = Array.from(table.querySelectorAll('tr'));
        return rows.map(row => {
            const cols = Array.from(row.querySelectorAll('th, td'));
            // Remove cells with action buttons/icons
            const filteredCols = cols.filter(col => !col.querySelector('img, button, a.student-action-link[href*="edit"]'));
            return filteredCols.map(col => {
                let text = col.innerText.trim().replace(/"/g, '""');
                return `"${text}"`;
            }).join(',');
        }).filter(line => line.length > 2).join('\n');
    },
    
    jsonToCSV: function(json) {
        if (!json.length) return '';
        
        const skipKeys = ['status', 'is_active', 'id', 'user_id', 'dept_id', 'batch_id', 'idx', '#', 's_no', 's.no'];
        const headers = Object.keys(json[0]).filter(k => !skipKeys.includes(k.toLowerCase()));
        
        const headerRow = ['"S.NO"', ...headers.map(h => `"${h.replace(/_/g, ' ').toUpperCase()}"`)].join(',');
        
        const rows = json.map((item, index) => {
            const rowData = [index + 1];
            headers.forEach(h => {
                let text = String(item[h] === null || item[h] === undefined ? '-' : item[h]).replace(/"/g, '""');
                rowData.push(`"${text}"`);
            });
            return rowData.join(',');
        }).join('\n');
        
        return headerRow + '\n' + rows;
    },
    
    downloadCSV: function(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.setAttribute('download', filename);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};

// Specialized Course Registration Download Logic
const SpecialDownloadManager = {
    init: function() {
        const openBtn = document.getElementById('openSpecializedDownloadBtn');
        const modal = document.getElementById('specializedDownloadModal');
        const closeBtn = document.getElementById('closeSpecModal');
        const cancelBtn = document.getElementById('cancelSpecBtn');
        const triggerBtn = document.getElementById('triggerSpecializedDownload');
        const studentInput = document.getElementById('spec_student_id');

        if (openBtn && modal) {
            openBtn.addEventListener('click', () => {
                modal.style.display = 'block';
                modal.classList.add('active');
            });
        }

        const hide = () => {
            if (modal) {
                modal.style.display = 'none';
                modal.classList.remove('active');
            }
        };

        if (closeBtn) closeBtn.addEventListener('click', hide);
        if (cancelBtn) cancelBtn.addEventListener('click', hide);
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) hide();
            });
        }

        // Autocomplete for Student ID in Modal
        if (studentInput) {
            studentInput.addEventListener('input', (e) => {
                const val = e.target.value;
                this.fetchAutocomplete(val);
            });
        }

        // Trigger Download
        if (triggerBtn) {
            triggerBtn.addEventListener('click', () => {
                const studentIdRaw = studentInput.value.trim();
                const studentId = studentIdRaw.includes(' - ') ? studentIdRaw.split(' - ')[0].trim() : studentIdRaw;
                const year = document.getElementById('spec_academic_year').value;
                const sem = document.getElementById('spec_semester').value;
                const type = document.getElementById('spec_registration_type').value;

                toggleGlobalModal('specializedDownloadModal', false);
                
                // Use ExportManager to handle the data fetching and CSV generation
                ExportManager.currentType = 'coursereg';
                ExportManager.currentAction = 'download';
                ExportManager.handleComplete({
                    type: 'coursereg',
                    full_data: 'true',
                    student_id: studentId,
                    year: year,
                    semester: sem,
                    registration_type: type
                });
            });
        }
    },

    fetchAutocomplete: function(val) {
        if (val.length < 2) {
            this.closeAllLists();
            return;
        }
        fetch(`/masters/ajax/?type=student-id-autocomplete&q=${val}`)
            .then(r => r.json())
            .then(data => {
                this.closeAllLists();
                if (!data.results || !data.results.length) return;
                
                const list = document.getElementById('spec_autocomplete_list');
                list.style.display = 'block';
                data.results.forEach(item => {
                    const div = document.createElement('div');
                    div.innerHTML = `<strong>${item.id}</strong> - ${item.name}`;
                    div.style.backgroundColor = '#fff';
                    div.style.padding = '10px';
                    div.style.cursor = 'pointer';
                    div.style.borderBottom = '1px solid #e2e8f0';
                    div.addEventListener('click', () => {
                        document.getElementById('spec_student_id').value = `${item.id} - ${item.name}`;
                        this.closeAllLists();
                    });
                    list.appendChild(div);
                });
            });
    },

    closeAllLists: function() {
        const list = document.getElementById('spec_autocomplete_list');
        if (list) {
            list.innerHTML = '';
            toggleGlobalModal('specializedDownloadModal', false); // Ensure entire modal is handled
        }
    }
};

// ==========================================================================
// Exam Lock & Publish Workflow Handlers
// ==========================================================================
function initExamWorkflowHandlers() {
    document.addEventListener('click', function (e) {
        // 1. Lock Toggle Handler (Updated for Confirmation Modal)
        const lockBtn = e.target.closest('.lock-toggle-btn');
        if (lockBtn) {
            e.preventDefault();
            const examId = lockBtn.dataset.examId;
            const isLocked = lockBtn.dataset.isLocked === 'true'; // Current state
            
            document.getElementById('lockModalExamId').value = examId;
            document.getElementById('lockModalIsLocked').value = isLocked;
            
            const title = isLocked ? 'Unlock Examination' : 'Lock Examination';
            const text = isLocked 
                ? 'Are you sure you want to <strong>Unlock</strong> this examination? This will allow modifications to scheduling and allocations. Please enter your password to confirm.' 
                : 'Are you sure you want to <strong>Lock</strong> this examination? This will freeze all data and prevent any further modifications.';
            const icon = isLocked ? '🔓' : '🔒';
            const btnText = isLocked ? 'Confirm Unlock' : 'Confirm Lock';
            
            document.getElementById('lockModalTitle').textContent = title;
            document.getElementById('lockModalText').innerHTML = text;
            document.getElementById('lockModalIcon').textContent = icon;
            document.getElementById('confirmLockBtn').textContent = btnText;
            
            // Show password field only for unlocking
            document.getElementById('passwordFieldContainer').style.display = isLocked ? 'block' : 'none';
            document.getElementById('lockAdminPassword').value = ''; // Reset password
            
            toggleGlobalModal('lockConfirmModal', true);
            return;
        }

        // 2. Publish Trigger
        const pubTrigger = e.target.closest('.publish-exam-btn-trigger');
        if (pubTrigger) {
            e.preventDefault();
            if (pubTrigger.dataset.locked === 'true') {
                showLockAlert('Publishing is disabled for locked examinations.', 'Admin');
                return;
            }
            document.getElementById('publishExamId').value = pubTrigger.dataset.examId;
            document.getElementById('publishActionType').value = 'PUBLISH';
            document.getElementById('publishModalTitle').textContent = 'Confirm Publication';
            document.getElementById('publishModalText').innerHTML = 'Are you sure you want to <strong>Publish</strong> this examination? The schedule will become visible to all students.';
            document.getElementById('publishModalIcon').textContent = '📢';
            toggleGlobalModal('publishConfirmModal', true);
            return;
        }

        // 3. Unpublish Trigger
        const unpubTrigger = e.target.closest('.unpublish-exam-btn');
        if (unpubTrigger) {
            e.preventDefault();
            if (unpubTrigger.dataset.locked === 'true') {
                showLockAlert('Unpublishing is disabled for locked examinations.', 'Admin');
                return;
            }
            document.getElementById('publishExamId').value = unpubTrigger.dataset.examId;
            document.getElementById('publishActionType').value = 'UNPUBLISH';
            document.getElementById('publishModalTitle').textContent = 'Unpublish Examination';
            document.getElementById('publishModalText').innerHTML = 'Are you sure you want to <strong>Unpublish</strong> this examination? It will no longer be visible to students.';
            document.getElementById('publishModalIcon').textContent = '🛑';
            toggleGlobalModal('publishConfirmModal', true);
            return;
        }

        // 4. Edit/Delete Lock Override
        const editTrigger = e.target.closest('.edit-exam-link-trigger');
        const deleteTrigger = e.target.closest('.delete-exam-link-trigger');
        if ((editTrigger || deleteTrigger) && (editTrigger?.dataset.locked === 'true' || deleteTrigger?.dataset.locked === 'true')) {
            e.preventDefault();
            e.stopPropagation();
            showLockAlert('This examination is locked. No edits or deletions are permitted.', 'Admin');
            return;
        }
    }, true);

    const confirmPublishBtn = document.getElementById('confirmPublishBtn');
    if (confirmPublishBtn) {
        confirmPublishBtn.addEventListener('click', function() {
            const examId = document.getElementById('publishExamId').value;
            const actionType = document.getElementById('publishActionType').value;
            const endpoint = actionType === 'PUBLISH' ? '/ops/ajax/publish_exam/' : '/ops/ajax/unpublish_exam/';
            
            this.textContent = 'Processing...';
            this.disabled = true;

            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
                },
                body: JSON.stringify({ exam_id: examId })
            })
            .then(resp => resp.json())
            .then(data => {
                if (data.success) {
                    showPopupMessage(`Exam ${actionType === 'PUBLISH' ? 'published' : 'unpublished'} successfully.`, 'success');
                    toggleGlobalModal('publishConfirmModal', false);
                    fetchExaminations();
                } else {
                    showPopupMessage(data.error || 'Action failed.', 'error');
                }
            })
            .finally(() => {
                this.textContent = 'Confirm';
                this.disabled = false;
            });
        });
    }

    // Lock/Unlock Confirmation Handler
    const confirmLockBtn = document.getElementById('confirmLockBtn');
    if (confirmLockBtn) {
        confirmLockBtn.addEventListener('click', function() {
            const examId = document.getElementById('lockModalExamId').value;
            const isLocked = document.getElementById('lockModalIsLocked').value === 'true';
            const password = document.getElementById('lockAdminPassword').value;
            const endpoint = isLocked ? '/ops/ajax/unlock_exam/' : '/ops/ajax/lock_exam/';
            
            if (isLocked && !password) {
                showPopupMessage('Password is required to unlock.', 'error');
                return;
            }

            this.textContent = 'Processing...';
            this.disabled = true;

            const payload = { exam_id: examId };
            if (isLocked) payload.password = password;

            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
                },
                body: JSON.stringify(payload)
            })
            .then(resp => resp.json())
            .then(data => {
                this.textContent = 'Confirm Action';
                this.disabled = false;
                if (data.success) {
                    toggleGlobalModal('lockConfirmModal', false);
                    showPopupMessage(`Examination ${isLocked ? 'Unlocked' : 'Locked'} successfully.`, 'success');
                    fetchExaminations();
                } else {
                    showPopupMessage(data.error || 'Action failed.', 'error');
                }
            })
            .catch(() => {
                this.textContent = 'Confirm Action';
                this.disabled = false;
                showPopupMessage('Network error.', 'error');
            });
        });
    }

    function showLockAlert(reason, adminName) {
        document.getElementById('lockAlertText').textContent = reason;
        const auditInfo = document.getElementById('lockAuditInfo');
        if (auditInfo) auditInfo.textContent = `Locked by administrative authority. Please contact DB Admin for assistance.`;
        toggleGlobalModal('lockAlertModal', true);
    }
}

// Initialize Managers
document.addEventListener('DOMContentLoaded', () => {
    ExportManager.init();
    SpecialDownloadManager.init();
    initExamWorkflowHandlers();
});
