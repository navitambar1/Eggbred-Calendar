let saveTimeout;
function loadLegend() {
    fetch('/get_legend')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('legend-list');
            container.innerHTML = '';
            data.forEach(item => {
                const div = document.createElement('div');
                div.className = 'legend-item d-flex align-items-center mb-2';
                div.innerHTML = `
                    <div class="color-dot" style="background-color: ${item.color};"></div>
                    <input type="text" 
                            class="legend-label flex-grow-1" 
                            value="${item.label}" 
                            data-id="${item.id}"
                            onblur="saveLegendItem(this)"
                            onkeypress="handleKeyPress(event, this)">
                    <div class="edit-buttons ms-2">
                        <button class="btn btn-sm btn-outline-primary" onclick="editLabel(this)" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                    </div>
                    <span class="status-indicator"></span>
                `;
                container.appendChild(div);
            });
        })
        .catch(error => {
            console.error('Error loading legend:', error);
            showError('Failed to load legend data');
        });
}

function editLabel(button) {
    const input = button.closest('.legend-item').querySelector('.legend-label');
    input.focus();
    input.select();
}

function handleKeyPress(event, input) {
    if (event.key === 'Enter') {
        input.blur();
    }
}

function saveLegendItem(input) {
    const id = input.dataset.id;
    const newLabel = input.value.trim();
    const statusIndicator = input.closest('.legend-item').querySelector('.status-indicator');
    
    // Clear any existing timeout
    if (saveTimeout) {
        clearTimeout(saveTimeout);
    }
    
    // Show saving indicator
    statusIndicator.innerHTML = '<i class="fas fa-spinner fa-spin saving-indicator"></i>';
    
    // Debounce the save operation
    saveTimeout = setTimeout(() => {
        fetch('/update_legend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: parseInt(id),
                label: newLabel
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                statusIndicator.innerHTML = '<i class="fas fa-check saving-indicator"></i>';
                setTimeout(() => {
                    statusIndicator.innerHTML = '';
                }, 2000);
            } else {
                throw new Error(data.error || 'Update failed');
            }
        })
        .catch(error => {
            console.error('Error updating legend:', error);
            statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle error-indicator"></i>';
            setTimeout(() => {
                statusIndicator.innerHTML = '';
            }, 3000);
        });
    }, 500); // 500ms debounce
}

function showError(message) {
    const container = document.getElementById('legend-list');
    container.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle"></i> ${message}
        </div>
    `;
}
document.addEventListener('DOMContentLoaded', function() {
    loadLegend();
    document.querySelectorAll('.color-preset').forEach(el => {
        el.addEventListener('click', () => {
            const color = el.getAttribute('data-color');
            const input = el.closest('.form-group').querySelector('input[type="color"]');
            input.value = color;
        });
    });
    const editModal = new bootstrap.Modal(document.getElementById('editEventModal'));
    const addModal = new bootstrap.Modal(document.getElementById('addEventModal'));
    const days = document.querySelectorAll('.day[data-date]');
    const selectedDates = new Set();
    const addSelectedDatesInput = document.getElementById('addSelectedDates');
    const addSelectedDatesList = document.getElementById('addSelectedDatesList');
    const noDateMessage = document.getElementById('noDateMessage');
    const addSubmitBtn = document.getElementById('addSubmitBtn');
    const addColorPicker = document.getElementById('addColorPicker');
    const modalColorPicker = document.getElementById('modalColorPicker');
    const colorPresets = document.querySelectorAll('.color-preset');
    colorPresets.forEach(preset => {
        preset.addEventListener('click', function() {
            const color = this.getAttribute('data-color');
            const parentModal = this.closest('.modal');

            if (parentModal.id === 'addEventModal') {
                addColorPicker.value = color;
                updateColorPresetSelection(this, 'addEventModal');
            } else if (parentModal.id === 'editEventModal') {
                modalColorPicker.value = color;
                updateColorPresetSelection(this, 'editEventModal');
            }
        });
    });
    function updateColorPresetSelection(selectedPreset, modalId) {
        const parentModal = document.getElementById(modalId);
        const presets = parentModal.querySelectorAll('.color-preset');

        presets.forEach(preset => {
            preset.classList.remove('selected');
        });
        selectedPreset.classList.add('selected');
    }
    addColorPicker.addEventListener('input', function() {
        updateColorPresetHighlight(this.value, 'addEventModal');
    });
    modalColorPicker.addEventListener('input', function() {
        updateColorPresetHighlight(this.value, 'editEventModal');
    });
    function updateColorPresetHighlight(color, modalId) {
        const parentModal = document.getElementById(modalId);
        const presets = parentModal.querySelectorAll('.color-preset');
        presets.forEach(preset => {
            preset.classList.remove('selected');
        });
        presets.forEach(preset => {
            if (preset.getAttribute('data-color').toLowerCase() === color.toLowerCase()) {
                preset.classList.add('selected');
            }
        });
    }
    function updateSelectedDatesList() {
        addSelectedDatesList.innerHTML = '';
        if (selectedDates.size > 0) {
            noDateMessage.style.display = 'none';
            addSubmitBtn.disabled = false;
            Array.from(selectedDates).sort().forEach(date => {
                const dateChip = document.createElement('span');
                dateChip.classList.add('date-chip');
                dateChip.textContent = date;
                const removeBtn = document.createElement('i');
                removeBtn.classList.add('fas', 'fa-times', 'ml-2');
                removeBtn.style.cursor = 'pointer';
                removeBtn.onclick = function() {
                    selectedDates.delete(date);
                    updateSelectedDatesList();
                    addSelectedDatesInput.value = Array.from(selectedDates).join(',');
                    const dayElement = document.querySelector(`.day[data-date="${date}"]`);
                    if (dayElement) {
                        dayElement.classList.remove('selected');
                    }
                };
                dateChip.appendChild(removeBtn);
                addSelectedDatesList.appendChild(dateChip);
            });
        } else {
            noDateMessage.style.display = 'block';
            addSubmitBtn.disabled = true;
        }
    }
    document.getElementById('addEventBtn').addEventListener('click', function() {
        addSelectedDatesInput.value = Array.from(selectedDates).join(',');
        updateSelectedDatesList();
        updateColorPresetHighlight('#ffc107', 'addEventModal');
        addModal.show();
    });
    days.forEach(day => {
        day.addEventListener('click', function() {
            const date = this.getAttribute('data-date');

            if (selectedDates.has(date)) {
                selectedDates.delete(date);
                this.classList.remove('selected');
            } else {
                selectedDates.add(date);
                this.classList.add('selected');
            }
            addSelectedDatesInput.value = Array.from(selectedDates).join(',');
            updateSelectedDatesList();
        });
    });
    const modalDatesContainer = document.getElementById('modalDates');
    const modalDatesInput = document.getElementById('modalDatesInput');
    const newDateInput = document.getElementById('newDateInput');
    const addDateBtn = document.getElementById('addDateBtn');

    let currentDates = [];

    function renderDates() {
        modalDatesContainer.innerHTML = '';
        currentDates.forEach((date, index) => {
            const chip = document.createElement('span');
            chip.classList.add('badge', 'bg-secondary', 'me-1');
            chip.textContent = new Date(date).toLocaleDateString();
            
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.innerHTML = '&times;';
            removeBtn.classList.add('btn', 'btn-sm', 'btn-light', 'ms-1', 'py-0', 'px-1');
            removeBtn.onclick = () => {
                currentDates.splice(index, 1);
                renderDates();
            };

            chip.appendChild(removeBtn);
            modalDatesContainer.appendChild(chip);
        });

        // Update hidden input for submission
        modalDatesInput.value = JSON.stringify(currentDates);
    }
    addDateBtn.addEventListener('click', () => {
        const dateValue = newDateInput.value;
        if (dateValue && !currentDates.includes(dateValue)) {
            currentDates.push(dateValue);
            renderDates();
            newDateInput.value = '';
        }
    });

    const editButtons = document.querySelectorAll('.edit-btn');
    const modalTitle = document.getElementById('modalTitle');
    const modalEventIndex = document.getElementById('modalEventIndex');
    const modalDates = document.getElementById('modalDates');
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const eventId = this.getAttribute('data-event-index');
            const event = events.find(e => e.id == eventId);
            if (event) {
                modalTitle.value = event.title;
                modalEventIndex.value = event.id;
                modalColorPicker.value = event.color || '#ffc107';
                updateColorPresetHighlight(event.color || '#ffc107', 'editEventModal');

                currentDates = [...event.dates];  // Store dates for editing
                renderDates();  // Render date chips

                editModal.show();
            }
        });
    });
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (confirm('Are you sure you want to delete this event?')) {
                const eventId = this.getAttribute('data-event-index');

                fetch(`/delete_event/${eventId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => {
                    if (response.ok) {
                        location.reload();
                    } else {
                        alert('Failed to delete event');
                    }
                });
            }
        });
    });    
});
const viewModal = new bootstrap.Modal(document.getElementById('viewEventModal'));
const viewEventTitle = document.getElementById('viewEventTitle');
const viewEventColor = document.getElementById('viewEventColor');
const viewEventDates = document.getElementById('viewEventDates');
document.querySelectorAll('.event-day').forEach(eventDay => {
    eventDay.addEventListener('click', function(e) {
        e.preventDefault(); // prevent default anchor behavior
        const parentDiv = this.closest('.day');
        const date = parentDiv.getAttribute('data-date');
        const eventId = parentDiv.getAttribute('data-event-id');

        const event = events.find(e => e.id == eventId);
        if (event) {
            viewEventTitle.textContent = event.title;
            viewEventColor.style.backgroundColor = event.color || '#ffc107';
            populateEventModal(event);
            viewModal.show();
        }
    });
});
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0'); // JS months are 0-based
    const year = date.getFullYear();
    return `${month}/${day}/${year}`;
}

function populateEventModal(event) {
    document.getElementById("viewEventTitle").textContent = event.title;
    document.getElementById("viewEventColor").style.backgroundColor = event.color;

    const datesList = document.getElementById("viewEventDates");
    datesList.innerHTML = ""; // Clear previous
    event.dates.sort().forEach(dateStr => {
        const li = document.createElement("li");
        li.textContent = formatDate(dateStr);
        datesList.appendChild(li);
    });
}
