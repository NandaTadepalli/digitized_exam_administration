// ========== Utility: Format Date as DD-MMM-YYYY ========== 
function formatDateDMY(dateStr) {
    if (!dateStr) return '';
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const d = new Date(dateStr);
    if (isNaN(d)) return dateStr;
    return `${d.getDate().toString().padStart(2, '0')}-${months[d.getMonth()]}-${d.getFullYear()}`;
}
// ========== Delete Exam Modal Logic ========== 
document.addEventListener('DOMContentLoaded', function() {
    var deleteExamModal = document.getElementById('deleteExamModal');
    if (deleteExamModal) {
        deleteExamModal.style.display = 'none';
    }
});
document.addEventListener('click', function(e) {
    var deleteExamModal = document.getElementById('deleteExamModal');
    if (!deleteExamModal) return;
    // Only show modal if delete button is clicked
    if (e.target && e.target.id === 'confirmDeleteExamLink') {
        deleteExamModal.style.display = 'flex';
    } else if (deleteExamModal.style.display === 'flex' && (!e.target || (e.target.id !== 'confirmDeleteExamLink' && e.target.id !== 'closeDeleteExamModal' && e.target.id !== 'cancelDeleteExamBtn'))) {
        // Hide modal if visible and not triggered by delete/cancel/close
        deleteExamModal.style.display = 'none';
    }
    if (e.target && (e.target.id === 'closeDeleteExamModal' || e.target.id === 'cancelDeleteExamBtn')) {
        deleteExamModal.style.display = 'none';
    }
});
document.addEventListener('click', function(e) {
    var deleteExamModal = document.getElementById('deleteExamModal');
    if (!deleteExamModal) return;
    if (e.target && e.target.id === 'confirmDeleteExamLink') {
        deleteExamModal.style.display = 'flex';
    }
    if (e.target && (e.target.id === 'closeDeleteExamModal' || e.target.id === 'cancelDeleteExamBtn')) {
        deleteExamModal.style.display = 'none';
    }
});
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
function showPopupMessage(text, type) {
    let popup = document.getElementById('popup-messages');
    if (!popup) {
        popup = document.createElement('div');
        popup.id = 'popup-messages';
        popup.style.position = 'fixed';
        popup.style.top = '20px';
        popup.style.right = '30px';
        popup.style.zIndex = '9999';
        document.body.appendChild(popup);
    }
    let msgDiv = document.createElement('div');
    msgDiv.className = 'popup-message popup-' + (type || 'error');
    msgDiv.tabIndex = 0;
    msgDiv.innerHTML = text;
    popup.appendChild(msgDiv);
    // Dismiss only when clicking outside
    function dismissPopup(e) {
        if (!popup.contains(e.target)) {
            popup.remove();
            document.removeEventListener('mousedown', dismissPopup);
        }
    }
    document.addEventListener('mousedown', dismissPopup);
}
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
            // Helper to show popup message at top right
            function showPopupMessage(text, type) {
                let popup = document.getElementById('popup-messages');
                if (!popup) {
                    popup = document.createElement('div');
                    popup.id = 'popup-messages';
                    popup.style.position = 'fixed';
                    popup.style.top = '20px';
                    popup.style.right = '30px';
                    popup.style.zIndex = '9999';
                    document.body.appendChild(popup);
                }
                let msgDiv = document.createElement('div');
                msgDiv.className = 'popup-message popup-' + (type || 'error');
                msgDiv.tabIndex = 0;
                msgDiv.innerHTML = text;
                popup.appendChild(msgDiv);
                // Dismiss only when clicking outside
                function dismissPopup(e) {
                    if (!popup.contains(e.target)) {
                        popup.remove();
                        document.removeEventListener('mousedown', dismissPopup);
                    }
                }
                document.addEventListener('mousedown', dismissPopup);
            }
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
    var allocationForm = document.querySelector('.faculty-assigned form');
    var requiredFac = document.getElementById('required-faculty-display');
    var allocatedFac = document.getElementById('allocated-faculty-display');
    var facultyCheckboxes = document.querySelectorAll('input[name="selected_faculty"]');
    function showPopupMessage(text, type) {
        let popup = document.getElementById('popup-messages');
        if (!popup) {
            popup = document.createElement('div');
            popup.id = 'popup-messages';
            popup.style.position = 'fixed';
            popup.style.top = '20px';
            popup.style.right = '30px';
            popup.style.zIndex = '9999';
            document.body.appendChild(popup);
        }
        let msgDiv = document.createElement('div');
        msgDiv.className = 'popup-message popup-' + (type || 'error');
        msgDiv.tabIndex = 0;
        msgDiv.innerHTML = text;
        popup.appendChild(msgDiv);
        // Dismiss only when clicking outside
        function dismissPopup(e) {
            if (!popup.contains(e.target)) {
                popup.remove();
                document.removeEventListener('mousedown', dismissPopup);
            }
        }
        document.addEventListener('mousedown', dismissPopup);
    }
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
            document.getElementById('courseregTableContainer').style.display = 'block';
            // Hide old containers if present
            if (document.getElementById('courseregActions')) document.getElementById('courseregActions').style.display = 'none';
            if (document.getElementById('courseregPaginationBar')) document.getElementById('courseregPaginationBar').style.display = 'none';
            // Show new flex container
            if (document.getElementById('courseregActionsBar')) document.getElementById('courseregActionsBar').style.display = 'flex';
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
var printCourseRegBtnElem = document.getElementById('printCourseRegBtn');
var downloadCourseRegBtnElem = document.getElementById('downloadCourseRegBtn');
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
        document.getElementById('courseregTableContainer').style.display = 'none';
        if (document.getElementById('courseregActionsBar')) document.getElementById('courseregActionsBar').style.display = 'none';
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
if (printCourseRegBtnElem) {
    printCourseRegBtnElem.addEventListener('click', function () {
        const table = document.getElementById('coursereg-table').outerHTML;
        const win = window.open('', '', 'width=900,height=700');
        win.document.write('<html><head><title>Print Course Registrations</title>');
        win.document.write('<link rel="stylesheet" href="/static/css/style.css">');
        win.document.write('</head><body>');
        win.document.write(table);
        win.document.write('</body></html>');
        win.document.close();
        win.print();
    });
}
if (downloadCourseRegBtnElem) {
    downloadCourseRegBtnElem.addEventListener('click', function () {
        let csv = 'Student ID,Student Name,Course Code,Course Name,Academic Year,Semester\n';
        document.querySelectorAll('#coursereg-list tr').forEach(row => {
            let cols = Array.from(row.querySelectorAll('td')).slice(1, 7).map(td => '"' + td.innerText.replace(/"/g, '""') + '"');
            if (cols.length) csv += cols.join(',') + '\n';
        });
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'course_registrations.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
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
// Save Examination Edit AJAX
var saveEditExamBtn = document.getElementById('saveEditExamBtn');
if (saveEditExamBtn) {
    saveEditExamBtn.onclick = function (e) {
        e.preventDefault();
        const examId = document.getElementById('editExamId').value;
        const examName = document.getElementById('edit_examname').value.trim();
        const academicYear = document.getElementById('edit_academic_year').value;
        const semester = document.getElementById('edit_semester').value;
        const startDate = document.getElementById('edit_start_date').value;
        const endDate = document.getElementById('edit_end_date').value;
        // Validate fields
        if (!examName || !academicYear || !semester || !startDate || !endDate) {
            alert('Please fill all fields.');
            return;
        }
        // Send AJAX request to update exam
        fetch('/ops/ajax/edit-examination/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                exam_id: examId,
                examname: examName,
                academic_year: academicYear,
                semester: semester,
                start_date: startDate,
                end_date: endDate
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert('Examination updated successfully.');
                    document.getElementById('editExamModal').style.display = 'none';
                    fetchExaminations();
                } else {
                    alert(data.error || 'Failed to update examination.');
                }
            })
            .catch(() => {
                alert('Network error. Please try again.');
            });
    };
}
// --- Student ID Autocomplete and Search ---
var studentIdList = [];
var selectedStudentId = '';

function fetchStudentIdAutocomplete(query) {
    if (!query) {
        document.getElementById('studentIdAutocomplete').style.display = 'none';
        return;
    }
    fetch(`/masters/ajax/?type=student-id-autocomplete&q=${encodeURIComponent(query)}`)
        .then(resp => resp.json())
        .then(data => {
            studentIdList = data.results || [];
            const listDiv = document.getElementById('studentIdAutocomplete');
            if (!studentIdList.length) {
                listDiv.style.display = 'none';
                return;
            }
            listDiv.innerHTML = studentIdList.map((item, idx) => `<div class="autocomplete-item" data-id="${item.id}" data-idx="${idx}" tabindex="0">${item.id} - ${item.name}</div>`).join('');
            listDiv.style.display = 'block';
        });
}

var searchStudentIdElem = document.getElementById('searchStudentId');
if (searchStudentIdElem) {
    searchStudentIdElem.addEventListener('input', function (e) {
        fetchStudentIdAutocomplete(this.value);
        selectedStudentId = '';
    });
    searchStudentIdElem.addEventListener('keydown', function (e) {
        const listDiv = document.getElementById('studentIdAutocomplete');
        if (listDiv.style.display !== 'block') return;
        const items = Array.from(listDiv.querySelectorAll('.autocomplete-item'));
        let idx = items.findIndex(item => item.classList.contains('selected'));
        if (e.key === 'ArrowDown') {
            if (idx < items.length - 1) idx++;
            else idx = 0;
            items.forEach(item => item.classList.remove('selected'));
            items[idx].classList.add('selected');
            items[idx].focus();
            e.preventDefault();
        } else if (e.key === 'ArrowUp') {
            if (idx > 0) idx--;
            else idx = items.length - 1;
            items.forEach(item => item.classList.remove('selected'));
            items[idx].classList.add('selected');
            items[idx].focus();
            e.preventDefault();
        } else if (e.key === 'Enter') {
            if (idx >= 0) {
                selectedStudentId = items[idx].dataset.id;
                this.value = items[idx].textContent.split(' - ')[0];
                listDiv.style.display = 'none';
                e.preventDefault();
            }
        }
    });

}

var studentIdAutocompleteElem = document.getElementById('studentIdAutocomplete');
if (studentIdAutocompleteElem) {
    studentIdAutocompleteElem.addEventListener('mousedown', function (e) {
        if (e.target.classList.contains('autocomplete-item')) {
            selectedStudentId = e.target.dataset.id;
            if (searchStudentIdElem) {
                searchStudentIdElem.value = e.target.textContent.split(' - ')[0];
            }
            this.style.display = 'none';
        }
    });
}

var searchStudentBtnElem = document.getElementById('searchStudentBtn');
if (searchStudentBtnElem) {
    searchStudentBtnElem.addEventListener('click', function () {
        const studentId = selectedStudentId || (searchStudentIdElem ? searchStudentIdElem.value.trim() : '');
        if (!studentId) {
            alert('Please enter or select a student ID.');
            return;
        }
        fetch(`/masters/ajax/?type=coursereg&student_id=${encodeURIComponent(studentId)}`)
            .then(resp => resp.json())
            .then(data => {
                document.getElementById('coursereg-list').innerHTML = data.table_html;
                document.getElementById('courseregTableContainer').style.display = '';
            });
    });
}

var resetStudentSearchBtnElem = document.getElementById('resetStudentSearchBtn');
if (resetStudentSearchBtnElem) {
    resetStudentSearchBtnElem.addEventListener('click', function () {
        if (searchStudentIdElem) searchStudentIdElem.value = '';
        if (studentIdAutocompleteElem) studentIdAutocompleteElem.style.display = 'none';
        selectedStudentId = '';
        var courseregTableContainerElem = document.getElementById('courseregTableContainer');
        if (courseregTableContainerElem) courseregTableContainerElem.style.display = 'none';
    });
}
// Fix ReferenceError: define startDateRaw and endDateRaw before using them
var startDateRaw = '';
var endDateRaw = '';
// Optionally, fetch values from a triggering element or another source
var editStartDateElem = document.getElementById('edit_start_date');
var editEndDateElem = document.getElementById('edit_end_date');
if (editStartDateElem) {
    editStartDateElem.value = startDateRaw.match(/^\d{4}-\d{2}-\d{2}$/) ? startDateRaw : '';
}
if (editEndDateElem) {
    editEndDateElem.value = endDateRaw.match(/^\d{4}-\d{2}-\d{2}$/) ? endDateRaw : '';
}
var closeEditExamModal = document.getElementById('closeEditExamModal');
if (closeEditExamModal) {
    closeEditExamModal.onclick = function () {
        document.getElementById('editExamModal').style.display = 'none';
    };
}
var cancelEditExamBtn = document.getElementById('cancelEditExamBtn');
if (cancelEditExamBtn) {
    cancelEditExamBtn.onclick = function (e) {
        e.preventDefault();
        document.getElementById('editExamModal').style.display = 'none';
    };
}
var editExamModal = document.getElementById('editExamModal');
if (editExamModal) {
    editExamModal.onclick = function (e) {
        if (e.target === this) this.style.display = 'none';
    };
}
// Delete Exam AJAX submit
var deleteExamForm = document.getElementById('deleteExamForm');
if (deleteExamForm) {
    deleteExamForm.onsubmit = function (e) {
        e.preventDefault();
        const examId = document.getElementById('deleteExamId').value;
        fetch('/ops/ajax/delete-examination/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ exam_id: examId })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('deleteExamModal').style.display = 'none';
                    // Optionally show notification
                    alert('Examination and all related slots and exams deleted successfully.');
                    fetchExaminations();
                } else {
                    alert('Failed to delete examination: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(() => {
                document.getElementById('deleteExamModal').style.display = 'none';
                alert('Failed to delete examination due to network error.');
            });
    };
}
// ============ EXAM SLOT TABLE AJAX (operations/exams.html) ============
function fetchExamSlotsAjax() {
        // Room Assignment badge AJAX modal logic
        document.addEventListener('click', function(e) {
            const roomBadge = e.target.closest('.room-assignment-badge');
            if (roomBadge) {
                e.preventDefault();
                const slotId = roomBadge.getAttribute('data-slot-id');
                // Modal elements (reuse or create if not present)
                let modal = document.getElementById('roomAllocModal');
                let modalContent = document.getElementById('roomAllocModalContent');
                if (!modal) {
                    modal = document.createElement('div');
                    modal.id = 'roomAllocModal';
                    modal.className = 'modal';
                    modal.style.display = 'none';
                    modal.innerHTML = `<div class="modal-content">
                        <span id="closeRoomAllocModal">&times;</span>
                        <div id="roomAllocModalContent"><h2>Allocated Rooms</h2><div>Loading...</div></div>
                    </div>`;
                    document.body.appendChild(modal);
                    modalContent = document.getElementById('roomAllocModalContent');
                }
                modal.style.display = 'flex';
                modalContent.innerHTML = '<h2>Allocated Rooms</h2><div>Loading...</div>';
                fetch(`/ops/ajax/slot-rooms/?slot_id=${slotId}`)
                    .then(resp => resp.json())
                    .then(data => {
                        if (!data.success) {
                            modalContent.innerHTML = `<div class='popup-message popup-error'>${data.error || 'No allocated rooms found.'}</div>`;
                            return;
                        }
                        let html = '';
                        // Slot info
                        html += `<div class='mb-1em popup-slot-info'>`;
                        html += `<span class='popup-slot-label'>Exam Type:</span> <span class='popup-slot-value'>${data.slot.exam_type || ''}</span>`;
                        html += `<span class='popup-slot-label'>Mode:</span> <span class='popup-slot-value'>${data.slot.mode || ''}</span>`;
                        html += `<span class='popup-slot-label'>Date:</span> <span class='popup-slot-value'>${data.slot.exam_date}</span>`;
                        html += `<span class='popup-slot-label'>Time:</span> <span class='popup-slot-value'>${data.slot.start_time}-${data.slot.end_time}</span>`;
                        html += `<span class='popup-slot-label'>Slot Code:</span> <span class='popup-slot-value'>${data.slot.slot_code || ''}</span>`;
                        html += `</div>`;
                        // Show required and allocated summary
                        html += `<div class='room-capacity-summary-wrapper' style='margin-bottom:1em;'>`;
                        html += `<span class='room-capacity-summary-item room-capacity-summary-flex'><span class='room-capacity-summary-label'>Required Rooms | Capacity:</span> <span class='room-capacity-summary-value required'>${data.required_room_count} | ${data.required_capacity}</span></span>`;
                        html += `<span class='room-capacity-summary-item room-capacity-summary-flex'><span class='room-capacity-summary-label'>Allocated Rooms | Capacity:</span> <span class='room-capacity-summary-value selected'>${data.allocated_room_count} | ${data.allocated_capacity}</span></span>`;
                        html += `</div>`;
                        // Edit buttons
                        html += `<div class="popup-edit-btn-container">`;
                        html += `<a href=\"/ops/exam_rooms_alloc/?slot_id=${slotId}\" class="popup-edit-btn badge" style="background:#2563eb;color:#fff;text-decoration:none;">Edit Rooms</a>`;
                        html += `</div>`;
                        // Rooms table
                        if (!data.rooms || data.rooms.length === 0) {
                            html += `<div>No rooms allocated for this slot.</div>`;
                        } else {
                            html += `<div class='dashboard-popup-table-wrapper'><table class='dashboard-popup-table'>`;
                            html += `<thead><tr><th>Room No</th><th>Type</th><th>Capacity</th><th>Block</th></tr></thead><tbody>`;
                            data.rooms.forEach(function (room) {
                                html += `<tr>`;
                                html += `<td>${room.room_no ? room.room_no : 'N/A'}</td>`;
                                html += `<td>${room.room_type ? room.room_type : 'N/A'}</td>`;
                                html += `<td>${room.capacity !== undefined && room.capacity !== null && room.capacity !== '' ? room.capacity : 'N/A'}</td>`;
                                html += `<td>${room.block ? room.block : 'N/A'}</td>`;
                                html += `</tr>`;
                            });
                            html += `</tbody></table></div>`;
                        }
                        modalContent.innerHTML = html;
                    })
                    .catch(() => {
                        modalContent.innerHTML = `<div class='popup-message popup-error'>Failed to load room details (network error).</div>`;
                    });
                // Close logic
                document.getElementById('closeRoomAllocModal').onclick = function () {
                    modal.style.display = 'none';
                };
                modal.onclick = function (evt) {
                    if (evt.target === modal) modal.style.display = 'none';
                };
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
        // Ensure preventDefault is called before navigation
        if (e.defaultPrevented) return;
        const badge = e.target.closest('.slot-courses-badge');
        if (badge) {
            e.preventDefault();
            const slotId = badge.getAttribute('data-slot-id');
            if (!slotId) return;
            const modal = document.getElementById('slotCoursesModal');
            const modalContent = document.getElementById('slotCoursesModalContent');
            modal.style.display = 'flex';
            modalContent.innerHTML = '<h2>Slot Courses</h2><div>Loading...</div>';
            fetch(`/ops/ajax/slot-courses/?slot_id=${slotId}`)
                .then(resp => resp.json())
                .then(data => {
                    if (!data.success) {
                        modalContent.innerHTML = `<div class='popup-message popup-error'>${data.error || 'Failed to load course details.'}</div>`;
                        return;
                    }
                    let html = '';
                    // Slot info
                    html += `<div class='mb-1em popup-slot-info'>`;
                    html += `<span class='popup-slot-label'>Exam Type:</span> <span class='popup-slot-value'>${data.slot.exam_type || ''}</span>`;
                    html += `<span class='popup-slot-label'>Mode:</span> <span class='popup-slot-value'>${data.slot.mode || ''}</span>`;
                    html += `<span class='popup-slot-label'>Date:</span> <span class='popup-slot-value'>${data.slot.exam_date}</span>`;
                    html += `<span class='popup-slot-label'>Time:</span> <span class='popup-slot-value'>${data.slot.start_time}-${data.slot.end_time}</span>`;
                    html += `<span class='popup-slot-label'>Slot Code:</span> <span class='popup-slot-value'>${data.slot.slot_code || ''}</span>`;
                    html += `</div>`;
                    // Courses table
                    if (data.courses.length === 0) {
                        html += `<div>No courses assigned to this slot.</div>`;
                    } else {
                        html += `<table class='dashboard-popup-table'>`;
                        html += `<thead><tr><th>Course Code</th><th>Course Name</th><th>Regulation</th><th>Academic Year</th><th>Semester</th><th>Student Count</th></tr></thead><tbody>`;
                        data.courses.forEach(function (course) {
                            html += `<tr>`;
                            html += `<td>${course.course_code}</td>`;
                            html += `<td>${course.course_name}</td>`;
                            html += `<td>${course.regulation || ''}</td>`;
                            html += `<td>${course.academic_year || ''}</td>`;
                            html += `<td>${course.semester || ''}</td>`;
                            html += `<td>${course.student_count}</td>`;
                            html += `</tr>`;
                        });
                        html += `</tbody></table>`;
                    }
                    modalContent.innerHTML = html;
                })
                .catch(() => {
                    modalContent.innerHTML = `<div class='popup-message popup-error'>Failed to load course details (network error).</div>`;
                });
            return;
        }

        // Room allocation badge modal logic
                // Faculty assignment badge modal logic
                const facultyAllocLink = e.target.closest('a[href*="/ops/exam_faculty_alloc/"]');
                if (facultyAllocLink) {
                    // Only trigger modal if badge is 'Assigned'
                    const badge = facultyAllocLink.querySelector('.exam-status.exam-status-available');
                    if (badge) {
                        e.preventDefault();
                        const row = facultyAllocLink.closest('tr');
                        const slotId = row ? row.querySelector('.slot-courses-badge')?.getAttribute('data-slot-id') : null;
                        // Fallback: try to extract slotId from URL
                        let slotIdUrl = null;
                        if (!slotId) {
                            const urlParams = new URLSearchParams(facultyAllocLink.href.split('?')[1]);
                            slotIdUrl = urlParams.get('slot_id');
                        }
                        const finalSlotId = slotId || slotIdUrl;
                        // Modal elements (reuse or create if not present)
                        let modal = document.getElementById('facultyAllocModal');
                        let modalContent = document.getElementById('facultyAllocModalContent');
                        if (!modal) {
                            modal = document.createElement('div');
                            modal.id = 'facultyAllocModal';
                            modal.className = 'modal';
                            modal.style.display = 'none';
                            modal.innerHTML = `<div class="modal-content">
                                <span id="closeFacultyAllocModal">&times;</span>
                                <div id="facultyAllocModalContent"><h2>Assigned Faculty</h2><div>Loading...</div></div>
                            </div>`;
                            document.body.appendChild(modal);
                            modalContent = document.getElementById('facultyAllocModalContent');
                        }
                        modal.style.display = 'flex';
                        modalContent.innerHTML = '<h2>Assigned Faculty</h2><div>Loading...</div>';
                        fetch(`/ops/ajax/slot-faculty/?slot_id=${finalSlotId}`)
                            .then(resp => resp.json())
                            .then(data => {
                                if (!data.success) {
                                    modalContent.innerHTML = `<div class='popup-message popup-error'>${data.error || 'No assigned faculty found.'}</div>`;
                                    return;
                                }
                                let html = '';
                                // Slot info with extra margin below
                                html += `<div class='mb-1em popup-slot-info'>`;
                                html += `<span class='popup-slot-label'>Exam Type:</span> <span class='popup-slot-value'>${data.slot.exam_type || 'N/A'}</span>`;
                                html += `<span class='popup-slot-label'>Mode:</span> <span class='popup-slot-value'>${data.slot.mode || 'N/A'}</span>`;
                                html += `<span class='popup-slot-label'>Date:</span> <span class='popup-slot-value'>${data.slot.exam_date || 'N/A'}</span>`;
                                html += `<span class='popup-slot-label'>Time:</span> <span class='popup-slot-value'>${data.slot.start_time || 'N/A'}-${data.slot.end_time || 'N/A'}</span>`;
                                html += `<span class='popup-slot-label'>Slot Code:</span> <span class='popup-slot-value'>${data.slot.slot_code || 'N/A'}</span>`;
                                html += `</div>`;
                                // Edit buttons
                                html += `<div class="popup-edit-btn-container">`;
                                html += `<a href=\"/ops/exam_faculty_alloc/?slot_id=${finalSlotId}\" class="popup-edit-btn badge" style="background:#2563eb;color:#fff;text-decoration:none;">Edit Faculty</a>`;
                                html += `</div>`;
                                // Faculty table
                                if (!data.faculty || data.faculty.length === 0) {
                                    html += `<div>No faculty assigned for this slot.</div>`;
                                } else {
                                    html += `<div class='dashboard-popup-table-wrapper'><table class='dashboard-popup-table'>`;
                                    html += `<thead><tr><th>Faculty ID</th><th>Name</th><th>Email</th><th>Department</th></tr></thead><tbody>`;
                                    data.faculty.forEach(function (fac) {
                                        html += `<tr>`;
                                        html += `<td>${fac.faculty_id ? fac.faculty_id : 'N/A'}</td>`;
                                        html += `<td>${fac.faculty_name ? fac.faculty_name : 'N/A'}</td>`;
                                        html += `<td>${fac.email ? fac.email : 'N/A'}</td>`;
                                        html += `<td>${fac.dept ? fac.dept : 'N/A'}</td>`;
                                        html += `</tr>`;
                                    });
                                    html += `</tbody></table></div>`;
                                }
                                modalContent.innerHTML = html;
                            })
                            .catch(() => {
                                modalContent.innerHTML = `<div class='popup-message popup-error'>Failed to load faculty details (network error).</div>`;
                            });
                        // Close logic
                        document.getElementById('closeFacultyAllocModal').onclick = function () {
                            modal.style.display = 'none';
                        };
                        modal.onclick = function (evt) {
                            if (evt.target === modal) modal.style.display = 'none';
                        };
                    }
                }
        const roomAllocLink = e.target.closest('a[href*="/ops/exam_rooms_alloc/"]');
        if (roomAllocLink) {
            // Only trigger modal if badge is 'Assigned'
            const badge = roomAllocLink.querySelector('.exam-status.exam-status-available');
            if (badge) {
                e.preventDefault();
                const row = roomAllocLink.closest('tr');
                const slotId = row ? row.querySelector('.slot-courses-badge')?.getAttribute('data-slot-id') : null;
                // Fallback: try to extract slotId from URL
                let slotIdUrl = null;
                if (!slotId) {
                    const urlParams = new URLSearchParams(roomAllocLink.href.split('?')[1]);
                    slotIdUrl = urlParams.get('slot_id');
                }
                const finalSlotId = slotId || slotIdUrl;
                // Modal elements (reuse or create if not present)
                let modal = document.getElementById('roomAllocModal');
                let modalContent = document.getElementById('roomAllocModalContent');
                if (!modal) {
                    modal = document.createElement('div');
                    modal.id = 'roomAllocModal';
                    modal.className = 'modal';
                    modal.style.display = 'none';
                    modal.innerHTML = `<div class="modal-content">
                        <span id="closeRoomAllocModal">&times;</span>
                        <div id="roomAllocModalContent"><h2>Allocated Rooms</h2><div>Loading...</div></div>
                    </div>`;
                    document.body.appendChild(modal);
                    modalContent = document.getElementById('roomAllocModalContent');
                }
                modal.style.display = 'flex';
                modalContent.innerHTML = '<h2>Allocated Rooms</h2><div>Loading...</div>';
                fetch(`/ops/ajax/slot-rooms/?slot_id=${finalSlotId}`)
                    .then(resp => resp.json())
                    .then(data => {
                        if (!data.success) {
                            modalContent.innerHTML = `<div class='popup-message popup-error'>${data.error || 'No allocated rooms found.'}</div>`;
                            return;
                        }
                        let html = '';
                        // Slot info
                        html += `<div class='mb-1em popup-slot-info'>`;
                        html += `<span class='popup-slot-label'>Exam Type:</span> <span class='popup-slot-value'>${data.slot.exam_type || ''}</span>`;
                        html += `<span class='popup-slot-label'>Mode:</span> <span class='popup-slot-value'>${data.slot.mode || ''}</span>`;
                        html += `<span class='popup-slot-label'>Date:</span> <span class='popup-slot-value'>${data.slot.exam_date}</span>`;
                        html += `<span class='popup-slot-label'>Time:</span> <span class='popup-slot-value'>${data.slot.start_time}-${data.slot.end_time}</span>`;
                        html += `<span class='popup-slot-label'>Slot Code:</span> <span class='popup-slot-value'>${data.slot.slot_code || ''}</span>`;
                        html += `</div>`;
                        // Show required and allocated summary
                        html += `<div class='room-capacity-summary-wrapper' style='margin-bottom:1em;'>`;
                        html += `<span class='room-capacity-summary-item room-capacity-summary-flex'><span class='room-capacity-summary-label'>Required Rooms | Capacity:</span> <span class='room-capacity-summary-value required'>${data.required_room_count} | ${data.required_capacity}</span></span>`;
                        html += `<span class='room-capacity-summary-item room-capacity-summary-flex'><span class='room-capacity-summary-label'>Allocated Rooms | Capacity:</span> <span class='room-capacity-summary-value selected'>${data.allocated_room_count} | ${data.allocated_capacity}</span></span>`;
                        html += `</div>`;
                        // Edit buttons
                        html += `<div class="popup-edit-btn-container">`;
                        html += `<a href=\"/ops/exam_rooms_alloc/?slot_id=${finalSlotId}\" class="popup-edit-btn badge" style="background:#2563eb;color:#fff;text-decoration:none;">Edit Rooms</a>`;
                        html += `</div>`;
                        // Rooms table
                        if (!data.rooms || data.rooms.length === 0) {
                            html += `<div>No rooms allocated for this slot.</div>`;
                        } else {
                            html += `<div class='dashboard-popup-table-wrapper'><table class='dashboard-popup-table'>`;
                            html += `<thead><tr><th>Room No</th><th>Type</th><th>Capacity</th><th>Block</th></tr></thead><tbody>`;
                            data.rooms.forEach(function (room) {
                                html += `<tr>`;
                                html += `<td>${room.room_no ? room.room_no : 'N/A'}</td>`;
                                html += `<td>${room.room_type ? room.room_type : 'N/A'}</td>`;
                                html += `<td>${room.capacity !== undefined && room.capacity !== null && room.capacity !== '' ? room.capacity : 'N/A'}</td>`;
                                html += `<td>${room.block ? room.block : 'N/A'}</td>`;
                                html += `</tr>`;
                            });
                            html += `</tbody></table></div>`;
                        }
                        modalContent.innerHTML = html;
                    })
                    .catch(() => {
                        modalContent.innerHTML = `<div class='popup-message popup-error'>Failed to load room details (network error).</div>`;
                    });
                // Close logic
                document.getElementById('closeRoomAllocModal').onclick = function () {
                    modal.style.display = 'none';
                };
                modal.onclick = function (evt) {
                    if (evt.target === modal) modal.style.display = 'none';
                };
            }
        }
    });
    // Close modal logic
    document.getElementById('closeSlotCoursesModal').onclick = function () {
        document.getElementById('slotCoursesModal').style.display = 'none';
    };
    document.getElementById('slotCoursesModal').onclick = function (e) {
        if (e.target === this) this.style.display = 'none';
    };
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
            document.getElementById('editSlotModal').style.display = 'flex';
        }
    });
    document.getElementById('closeEditSlotModal').onclick = function () {
        document.getElementById('editSlotModal').style.display = 'none';
    };
    document.getElementById('cancelEditSlotBtn').onclick = function (e) {
        e.preventDefault();
        document.getElementById('editSlotModal').style.display = 'none';
    };
    document.getElementById('editSlotModal').onclick = function (e) {
        if (e.target === this) this.style.display = 'none';
    };
    var examId = window.examIdForSlots || '';
    var tbody = document.getElementById('exam-slots-list');
    if (!tbody) return;
    if (!examId) {
        tbody.innerHTML = '<tr><td colspan="12" class="text-center">No exam selected.</td></tr>';
        return;
    }
    fetch('/ops/ajax_exam_slots/?exam_id=' + encodeURIComponent(examId))
        .then(response => response.json())
        .then(data => {
            if (data.slots.length === 0) {
                tbody.innerHTML = '<tr><td colspan="12" class="text-center">No exam slots created yet.</td></tr>';
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
                    if (slot.assignment_status === 'Assigned') {
                        statusCell = `<td><a href="${schedUrl}" class="slot-schedule-link" title="Go to scheduling"><span class="exam-status exam-status-available">Assigned <img src='https://img.icons8.com/?size=100&id=79211&format=png&color=000000' alt='Assigned' class='status-icon'></span></a></td>`;
                    } else {
                        statusCell = `<td><a href="${schedUrl}" class="slot-schedule-link" title="Go to scheduling"><span class="exam-status exam-status-pending">Pending <img src='https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000' alt='Pending' class='status-icon'></span></a></td>`;
                    }
                    // Add edit and delete links
                    const editLink = `<a href="#" class="edit-slot-btn" data-slot-id="${slot.id}" title="Edit"><img src="https://img.icons8.com/?size=100&id=kzmsQM0bM3Bl&format=png&color=000000" alt="Edit Slot" class="icon-edit"></a>`;
                    const deleteLink = `<a href="#" class="delete-slot-btn" data-slot-id="${slot.id}" data-slot-date="${slot.exam_date}" data-slot-time="${slot.start_time}-${slot.end_time}" data-slot-code="${slot.slot_code}"><img src="https://img.icons8.com/?size=100&id=99971&format=png&color=000000" alt="Delete Slot" class="icon-delete"></a>`;
                    // Badge for courses
                    // Show badge as 'count : X', but use red for 0, green for >0
                    let badgeClass = slot.course_count > 0 ? 'badge-courses badge-courses-positive' : 'badge-courses badge-courses-zero';
                    courseBadge = `<a href="#" class="slot-courses-badge" data-slot-id="${slot.id}">
                        <span class="${badgeClass}">count : ${slot.course_count}</span>
                    </a>`;
                    // Room allocation badge
                    let roomBadge = '';
                    if (slot.assigned_room_count > 0) {
                        roomBadge = `<span class="exam-status exam-status-available">Assigned : ${slot.assigned_room_count}</span>`;
                    } else {
                        roomBadge = `<span class="exam-status exam-status-pending">Pending <img src='https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000' alt='Pending' class='status-icon'></span>`;
                    }
                    // Faculty assignment badge
                    let facultyBadge = '';
                    if (slot.assigned_faculty_count > 0) {
                        facultyBadge = `<span class="exam-status exam-status-available">Assigned : ${slot.assigned_faculty_count}</span>`;
                    } else {
                        facultyBadge = `<span class="exam-status exam-status-pending">Pending <img src='https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000' alt='Pending' class='status-icon'></span>`;
                    }
                    // Determine status for new column
                    let newStatusCell = '';
                    // Show Completed if generated and all assigned
                    if (slot.is_generated && slot.all_assigned) {
                        newStatusCell = `<td><span class="exam-status exam-status-available">Completed <span class='status-icon status-tick' aria-label='Completed'><svg viewBox="0 0 16 16" width="17" height="17" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="8" cy="8" r="8" fill="#e6f9e6"/><path d="M4.5 8.5L7 11L11.5 6.5" stroke="#1a7f1a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></span></span></td>`;
                    } else if (slot.is_generated) {
                        // If generated but not all assigned, show Update
                        newStatusCell = `<td><a href="#" class="slot-status-link" title="Status"><span class="exam-status exam-status-available">Update <img src='https://img.icons8.com/?size=100&id=11841&format=png&color=ff9900' alt='Update' class='status-icon'></span></a></td>`;
                    } else if (
                        roomBadge.includes('exam-status-available') &&
                        facultyBadge.includes('exam-status-available') &&
                        badgeClass.includes('badge-courses-positive')
                        && !slot.is_generated
                    ) {
                        // Only show Generate if all assigned and no backend data
                        newStatusCell = `<td><a href="#" class="slot-status-link" title="Status"><span class="exam-status exam-status-generate">Generate <img src='https://img.icons8.com/?size=100&id=11841&format=png&color=ff9900' alt='Generate' class='status-icon'></span></a></td>`;
                    } else {
                        newStatusCell = `<td><a href="#" class="slot-status-link" title="Status"><span class="exam-status exam-status-pending">Pending <img src='https://img.icons8.com/?size=100&id=rKEYSosGdrkP&format=png&color=000000' alt='Pending' class='status-icon'></span></a></td>`;
                    }
                    var row = `<tr data-slot-id="${slot.id}">
                        <td>${slot.exam_type || ''}</td>
                        <td>${slot.mode || ''}</td>
                        <td>${slot.exam_date || ''}</td>
                        <td>${to12Hour(slot.start_time) || ''}</td>
                        <td>${to12Hour(slot.end_time) || ''}</td>
                        <td>${slot.slot_code || ''}</td>
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
            tbody.innerHTML = '<tr><td colspan="10" class="text-center">Error loading slots.</td></tr>';
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
                        // Check room assignment
                        const roomCell = row.children[9];
                        if (roomCell && roomCell.textContent.includes('Pending')) missing.push('Room Assignment');
                        // Check faculty assignment
                        const facultyCell = row.children[10];
                        if (facultyCell && facultyCell.textContent.includes('Pending')) missing.push('Faculty Assignment');
                        // Check course count
                        const courseCountCell = row.children[7];
                        if (courseCountCell && courseCountCell.textContent.trim() === 'count : 0') missing.push('Course Assignment');
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
                // Spinner Modal Functions
                function showSpinnerModal(message) {
                    let modal = document.getElementById('spinner-modal');
                    if (!modal) {
                        modal = document.createElement('div');
                        modal.id = 'spinner-modal';
                        modal.innerHTML = `
                            <div class="spinner-modal-content">
                                <span class="spinner"></span>
                                <div class="spinner-modal-text">${message}</div>
                            </div>
                        `;
                        document.body.appendChild(modal);
                    } else {
                        modal.querySelector('.spinner-modal-text').innerHTML = message;
                        modal.style.display = 'flex';
                    }
                }
                function closeSpinnerModal() {
                    let modal = document.getElementById('spinner-modal');
                    if (modal) modal.style.display = 'none';
                }
                // Spinner Modal CSS
                const spinnerModalStyle = document.createElement('style');
                spinnerModalStyle.innerHTML = `
                #spinner-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    background: rgba(30,58,95,0.18);
                    z-index: 99999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .spinner-modal-content {
                    background: #fff;
                    border-radius: 16px;
                    box-shadow: 0 8px 32px rgba(30,58,95,0.18);
                    padding: 2.5em 2em;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    min-width: 340px;
                    max-width: 90vw;
                }
                .spinner-modal-text {
                    margin-top: 1.2em;
                    font-size: 1.18em;
                    color: #1E3A5F;
                    text-align: center;
                    font-family: 'Poppins', sans-serif;
                }
                `;
                document.head.appendChild(spinnerModalStyle);
                }
            }
        // Spinner CSS
        const spinnerStyle = document.createElement('style');
        spinnerStyle.innerHTML = `
        .spinner {
            width: 22px;
            height: 22px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #2563eb;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            display: inline-block;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        `;
        document.head.appendChild(spinnerStyle);
        });
    function showPopupMessage(msg, type = 'error') {
        let popup = document.getElementById('popup-messages');
        if (!popup) {
            popup = document.createElement('div');
            popup.id = 'popup-messages';
            document.body.appendChild(popup);
        }
        const div = document.createElement('div');
        div.className = 'popup-message popup-' + type;
        div.tabIndex = 0;
        div.innerHTML = msg;
        popup.appendChild(div);
        // Remove on outside click
        function outsideClickHandler(e) {
            if (!div.contains(e.target)) {
                div.remove();
                document.removeEventListener('mousedown', outsideClickHandler);
            }
        }
        document.addEventListener('mousedown', outsideClickHandler);
    }

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
            document.getElementById('deleteSlotModal').style.display = 'flex';
        }
    });
    document.getElementById('closeDeleteSlotModal').onclick = function () {
        document.getElementById('deleteSlotModal').style.display = 'none';
    };
    document.getElementById('cancelDeleteSlotBtn').onclick = function (e) {
        e.preventDefault();
        document.getElementById('deleteSlotModal').style.display = 'none';
    };
    document.getElementById('deleteSlotModal').onclick = function (e) {
        if (e.target === this) this.style.display = 'none';
    };
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
                        tbody.innerHTML += `<tr id="${rowId}">
                            <td>${exam.number}</td>
                            <td>${exam.exam_name}</td>
                            <td>${exam.academic_year || ''}</td>
                            <td>${exam.semester || ''}</td>
                            <td data-raw="${exam.start_date}">${formatDateDMY(exam.start_date)}</td>
                            <td data-raw="${exam.end_date}">${formatDateDMY(exam.end_date)}</td>
                            <td id="slot-badge-${exam.exam_id}"><a href="${slotLink}" class="slot-link" data-exam-name="${encodeURIComponent(exam.exam_name)}">${pendingBadge()}</a></td>
                            <td id="status-badge-${exam.exam_id}">${pendingBadge()}</td>
                            <td>
                                <a href="#" class="edit-exam-btn" data-exam-id="${exam.exam_id}" title="Edit"><img src="https://img.icons8.com/?size=100&id=kzmsQM0bM3Bl&format=png&color=000000" alt="Edit Exam" style="width:16px;height:16px;margin-right:6px;"></a>
                                <a href="#" class="delete-exam-btn" data-exam-id="${exam.exam_id}" data-exam-name="${exam.exam_name}"><img src="https://img.icons8.com/?size=100&id=99971&format=png&color=000000" alt="Delete Exam" style="width:16px;height:16px;"></a>
                            </td>
                        </tr>`;
                        fetch(`/ops/ajax_exam_slots/?exam_id=${exam.exam_id}`)
                            .then(resp => resp.json())
                            .then(slotData => {
                                const badgeTd = document.getElementById(`slot-badge-${exam.exam_id}`);
                                const statusTd = document.getElementById(`status-badge-${exam.exam_id}`);
                                if (badgeTd && slotData.slots && slotData.slots.length > 0) {
                                    badgeTd.innerHTML = `<a href="${slotLink}" class="slot-link" data-exam-name="${encodeURIComponent(exam.exam_name)}">${availableBadge(slotData.slots.length)}</a>`;
                                }
                                // Determine if all slots are completed (is_generated and assignments done)
                                let allCompleted = slotData.slots.length > 0 && slotData.slots.every(s => s.status === 'Publish');
                                let anyPending = slotData.slots.some(s => s.status !== 'Publish');
                                if (statusTd) {
                                    if (exam.published && allCompleted) {
                                        statusTd.innerHTML = `<span class="exam-status exam-status-available" style="background:#e6f9e6;color:#1a7f1a;padding:2px 10px 2px 10px;border-radius:6px;display:inline-flex;align-items:center;font-weight:600;">Published <img src="https://img.icons8.com/?size=100&id=79211&format=png&color=22c55e" alt="Published" class="status-icon" style="width:1.2em;height:1.2em;vertical-align:middle;margin-left:6px;"></span>`;
                                    } else if (allCompleted && !exam.published) {
                                        statusTd.innerHTML = `<a href="#" class="publish-exam-btn" data-exam-id="${exam.exam_id}" style="text-decoration:none;"><span class="exam-status exam-status-publish" style="background:#fff3cd;color:#d97706;padding:2px 10px 2px 10px;border-radius:6px;display:inline-flex;align-items:center;font-weight:600;cursor:pointer;">Publish <img src="https://img.icons8.com/?size=100&id=79211&format=png&color=000000" alt="Publish" class="status-icon" style="width:1.2em;height:1.2em;vertical-align:middle;margin-left:6px;"></span></a>`;
                                    } else {
                                        statusTd.innerHTML = pendingBadge();
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
                    document.getElementById('deleteExamWarning').innerHTML = `Are you sure you want to delete <b>\"${examName}\"</b>?<br>This will <b>permanently delete</b> all slots and exams scheduled under this examination.`;
                    document.getElementById('deleteExamDetails').innerHTML = detailsHtml;
                    document.getElementById('deleteExamId').value = examId;
                    document.getElementById('deleteExamModal').style.display = 'flex';
                });
        }
    });
    // Modal close/cancel logic
    document.getElementById('closeDeleteExamModal').onclick = function () {
        document.getElementById('deleteExamModal').style.display = 'none';
    };
    document.getElementById('cancelDeleteExamBtn').onclick = function (e) {
        e.preventDefault();
        document.getElementById('deleteExamModal').style.display = 'none';
    };
    document.getElementById('deleteExamModal').onclick = function (e) {
        if (e.target === this) this.style.display = 'none';
    };
    document.getElementById('confirmDeleteExamLink').onclick = function (e) {
        e.preventDefault();
        const examId = document.getElementById('deleteExamId').value;
        fetch('/ops/ajax/delete-examination/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ exam_id: examId })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // Hide modal and clear its content
                    const modal = document.getElementById('deleteExamModal');
                    modal.style.display = 'none';
                    document.getElementById('deleteExamWarning').innerHTML = '';
                    document.getElementById('deleteExamDetails').innerHTML = '';
                    document.getElementById('deleteExamId').value = '';
                    alert('Examination and all related slots and exams deleted successfully.');
                    fetchExaminations();
                } else {
                    alert('Failed to delete examination: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(() => {
                document.getElementById('deleteExamModal').style.display = 'none';
                alert('Failed to delete examination due to network error.');
            });
    };
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
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No course registrations found for the selected filters.</td></tr>';
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
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No course registrations found for the selected filters.</td></tr>';
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
                const students = row.children[6].dataset.students ? row.children[6].dataset.students.split(',') : [];
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
// ============ STUDENT PAGE EXPORT/PRINT ============
// ============ STUDENT PAGE EXPORT/PRINT ============
function getVisibleStudentRows() {
    return Array.from(document.querySelectorAll('#student-list tr')).filter(row => {
        // Only count rows with at least 6 cells and not the empty row
        return row.style.display !== 'none' && row.querySelectorAll('td').length >= 6 && !row.querySelector('td[colspan]');
    });
}
function printStudentTable() {
    const table = document.getElementById('student-table');
    if (!table) return;
    const visibleRows = getVisibleStudentRows();
    if (!visibleRows.length) return alert('No data to print.');
    const cloneTable = table.cloneNode(true);
    // Remove last column (actions) from header
    const headerRow = cloneTable.querySelector('thead tr');
    if (headerRow && headerRow.children.length > 6) headerRow.removeChild(headerRow.lastElementChild);
    // Remove all rows from tbody
    const tbody = cloneTable.querySelector('tbody');
    tbody.innerHTML = '';
    visibleRows.forEach(row => {
        const cloneRow = row.cloneNode(true);
        if (cloneRow.children.length > 6) cloneRow.removeChild(cloneRow.lastElementChild);
        tbody.appendChild(cloneRow);
    });
    const newWindow = window.open('', '_blank');
    if (!newWindow) return alert('Popup blocked!');
    newWindow.document.write(`
        <html><head><title>Print Student Data</title>
        <style>
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #000; padding: 8px; text-align: left; }
            th { background-color: #1E3A5F; color: white; }
        </style></head><body>
        <h2>Student Data</h2>
        ${cloneTable.outerHTML}
        </body></html>
    `);
    newWindow.document.close();
    newWindow.focus();
    newWindow.print();
}
function downloadStudentCSV() {
    const table = document.getElementById('student-table');
    if (!table) return;
    const rows = getVisibleStudentRows();
    if (!rows.length) return alert('No data to download.');
    const headers = Array.from(table.querySelectorAll('thead th'))
        .slice(0, -1)
        .map(th => `"${th.textContent.trim()}"`)
        .join(',');
    const data = rows.map(row => {
        return Array.from(row.querySelectorAll('td'))
            .slice(0, -1)
            .map(td => `"${td.textContent.trim()}"`)
            .join(',');
    });
    const csvContent = [headers, ...data].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'student_data.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
document.addEventListener('DOMContentLoaded', function () {
    if (typeof initializeStudentFilters === 'function') {
        initializeStudentFilters();
    }
    const printBtn = document.getElementById('printStudentBtn');
    const downloadBtn = document.getElementById('downloadStudentBtn');
    if (printBtn) printBtn.onclick = printStudentTable;
    if (downloadBtn) downloadBtn.onclick = downloadStudentCSV;
});


function printFacultyTable() {
    const table = document.getElementById("faculty-table");
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
        <html><head><title>Print Faculty Data</title>
        <style>
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #000; padding: 8px; text-align: left; }
            th { background-color: #1E3A5F; color: white; }
        </style></head><body>
        <h2>Faculty Data</h2>
        ${cloneTable.outerHTML}
        </body></html>
    `);
    newWindow.document.close();
    newWindow.focus();
    newWindow.print();
}

function downloadFacultyCSV() {
    const table = document.getElementById("faculty-table");
    if (!table) return;

    const rows = Array.from(document.querySelectorAll("#faculty-list tr"))
        .filter(row => row.style.display !== "none");

    if (!rows.length) return alert("No data to download.");

    const headers = Array.from(table.querySelectorAll("thead th"))
        .slice(0, -1) // Exclude the last header ("Actions")
        .map(th => `"${th.textContent.trim()}"`)
        .join(",");

    const data = rows.map(row => {
        return Array.from(row.querySelectorAll("td"))
            .slice(0, -1) // Exclude the last cell ("Actions")
            .map(td => `"${td.textContent.trim()}"`)
            .join(",");
    });

    const csvContent = [headers, ...data].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "faculty_data.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ============ FACULTY DELETE MODAL (AJAX, JS-only) ============
document.addEventListener('DOMContentLoaded', function () {
    const facultyDeleteBtns = document.querySelectorAll('.faculty-delete-btn');
    let facultyModal = document.getElementById('facultyDeleteModal');
    if (!facultyModal) {
        facultyModal = document.createElement('div');
        facultyModal.id = 'facultyDeleteModal';
        facultyModal.className = 'modal';
        facultyModal.style.display = 'none';
        facultyModal.style.position = 'fixed';
        facultyModal.style.top = '0';
        facultyModal.style.left = '0';
        facultyModal.style.width = '100vw';
        facultyModal.style.height = '100vh';
        facultyModal.style.background = 'rgba(30,58,95,0.18)';
        facultyModal.style.zIndex = '3000';
        facultyModal.style.alignItems = 'center';
        facultyModal.style.justifyContent = 'center';
        document.body.appendChild(facultyModal);
    }
    let facultyModalContent = document.getElementById('facultyDeleteModalContent');
    if (!facultyModalContent) {
        facultyModalContent = document.createElement('div');
        facultyModalContent.id = 'facultyDeleteModalContent';
        facultyModalContent.className = 'modal-content';
        facultyModalContent.style.background = '#fff';
        facultyModalContent.style.padding = '0';
        facultyModalContent.style.borderRadius = '14px';
        facultyModalContent.style.maxWidth = '480px';
        facultyModalContent.style.width = '100%';
        facultyModalContent.style.boxShadow = '0 2px 12px rgba(30,58,95,0.18)';
        facultyModalContent.style.position = 'relative';
        facultyModal.appendChild(facultyModalContent);
    }
    facultyDeleteBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const facultyId = btn.getAttribute('data-faculty-id');
            const facultyName = btn.getAttribute('data-faculty-name');
            const facultyEmail = btn.getAttribute('data-faculty-email');
            const facultyDept = btn.getAttribute('data-faculty-dept');
            const facultyPhone = btn.getAttribute('data-faculty-phone');
            const facultyDesignation = btn.getAttribute('data-faculty-designation');
            const facultyStatus = btn.getAttribute('data-faculty-status');
            facultyModalContent.innerHTML = `
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
      `;
            facultyModal.style.display = 'flex';
            // Cancel button
            const cancelBtn = document.getElementById('cancelFacultyDeleteBtn');
            if (cancelBtn) {
                cancelBtn.onclick = function () {
                    facultyModal.style.display = 'none';
                };
            }
            // Close modal on outside click
            facultyModal.onclick = function (e) {
                if (e.target === facultyModal) facultyModal.style.display = 'none';
            };
            // Submit form to delete faculty
            const deleteForm = document.getElementById('deleteFacultyForm');
            if (deleteForm) {
                deleteForm.onsubmit = function (e) {
                    e.preventDefault();
                    const url = `/masters/faculty/${facultyId}/delete/`;
                    // Try to get CSRF token from page
                    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
                    const csrfToken = csrfInput ? csrfInput.value : '';
                    fetch(url, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRFToken': csrfToken,
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: `csrfmiddlewaretoken=${csrfToken}`
                    }).then(resp => {
                        if (resp.ok) {
                            showPopup('Faculty deleted successfully.', 'success');
                            setTimeout(() => { window.location.reload(); }, 1200);
                        } else {
                            showPopup('Failed to delete faculty.', 'error');
                            facultyModal.style.display = 'none';
                        }
                    });
                };
            }
        });
    });
});

// ============ STUDENT DELETE MODAL (AJAX) ============
document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('studentDeleteModal');
    // Only the correct delete-exam-btn event handler should be present (see above)
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
    // These functions now handle attaching print/download listeners themselves.
    // They also grab the latest table rows, which is important for filtering.
    // We explicitly call them here based on the URL.

    // Student Management
    if (pageUrl.includes('/students/') && typeof initializeStudentFilters === 'function') {
        initializeStudentFilters();
    }
    // Faculty Management
    if (pageUrl.includes('/faculty/') && typeof initializeFacultyFilters === 'function') {
        initializeFacultyFilters();
    }
    // Room Management
    if (pageUrl.includes('/rooms/') && typeof initializeRoomFilters === 'function') {
        initializeRoomFilters();
    }
    // Add more conditions for other pages if they have unique JS initialization
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
                // Re-initialize delete modal and other listeners if needed
                if (typeof initializeContentScripts === 'function') {
                    initializeContentScripts(window.location.pathname);
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

// Add event handler for edit-exam-btn
$(document).on('click', '.edit-exam-btn', function (e) {
    e.preventDefault();
    var row = $(this).closest('tr');
    var examId = $(this).data('exam-id');
    var examName = row.find('td').eq(1).text().trim();
    var academicYear = row.find('td').eq(2).text().trim();
    var semester = row.find('td').eq(3).text().trim();
    var startDateRaw = row.find('td[data-raw]').eq(0).data('raw') || '';
    var endDateRaw = row.find('td[data-raw]').eq(1).data('raw') || '';

    // Fill modal fields
    $('#editExamId').val(examId);
    $('#edit_examname').val(examName);
    $('#edit_academic_year').val(academicYear);
    $('#edit_semester').val(semester);
    $('#edit_start_date').val(startDateRaw.match(/^\d{4}-\d{2}-\d{2}$/) ? startDateRaw : '');
    $('#edit_end_date').val(endDateRaw.match(/^\d{4}-\d{2}-\d{2}$/) ? endDateRaw : '');
    // Set date constraints
    var todayStr = (function () {
        var d = new Date();
        var m = (d.getMonth() + 1).toString().padStart(2, '0');
        var day = d.getDate().toString().padStart(2, '0');
        return d.getFullYear() + '-' + m + '-' + day;
    })();
    var editStartDateElem = document.getElementById('edit_start_date');
    var editEndDateElem = document.getElementById('edit_end_date');
    if (editStartDateElem) editStartDateElem.min = todayStr;
    if (editEndDateElem && editStartDateElem) editEndDateElem.min = editStartDateElem.value;
    // Remove previous event listeners to avoid stacking
    if (editStartDateElem && editEndDateElem) {
        editStartDateElem.onchange = function () {
            editEndDateElem.min = editStartDateElem.value;
            if (editEndDateElem.value && editEndDateElem.value < editStartDateElem.value) {
                editEndDateElem.value = '';
            }
        };
    }
    $('#editExamModal').css('display', 'flex');
});

// Add missing closing brace for file

