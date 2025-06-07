function applyFieldUpdate(id, field, value) {
    const row = document.querySelector(`tr[data-wsid="${id}"]`);
    if (!row) return;
    if (field === "status") {
        const select = row.querySelector('td:nth-child(5) select');
        if (select) select.value = value;
        setRowCompleted(id, value === "Completed");
        const automateCheckbox = document.getElementById(`automate-${id}`);
        if (automateCheckbox) {
            if (value === "Completed") {
                automateCheckbox.disabled = false;
            } else {
                automateCheckbox.disabled = true;
                automateCheckbox.checked = false;
            }
        }
    } else if (field === "technician") {
        const select = row.querySelector('td:nth-child(6) select');
        if (select) select.value = value;
    } else if (field === "notes") {
        const input = row.querySelector('td:nth-child(7) input');
        if (input) input.value = value;
    } else if (field === "updated_in_automate") {
        const checkbox = document.getElementById(`automate-${id}`);
        if (checkbox) {
            checkbox.checked = !!value;
            row.setAttribute('data-automate', value ? 'updated' : 'not-updated');
        }
    }
}

function updateField(id, field, value) {
    fetch("/update", {
        method: "POST",
        body: new URLSearchParams({ id, field, value })
    }).then(res => res.json())
      .then(data => {
        applyFieldUpdate(id, field, value);
        checkProjectTicketReadiness();
      });
}

function updateAutomateStatus(id, checked) {
    fetch("/update", {
        method: "POST",
        body: new URLSearchParams({
            id: id,
            field: 'updated_in_automate',
            value: checked
        })
    }).then(res => res.json())
      .then(data => {
        if (data.ok) {
            // Update the data attribute for filtering
            const row = document.querySelector(`tr[data-wsid="${id}"]`);
            if (row) {
                row.setAttribute('data-automate', checked ? 'updated' : 'not-updated');
            }
        }
      });
}

// --- WebSocket setup for real-time updates ---
const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const socket = new WebSocket(wsProtocol + '://' + window.location.host + '/ws');

socket.addEventListener('message', function(event) {
    try {
        const data = JSON.parse(event.data);
        if (data.action === 'field_update') {
            applyFieldUpdate(data.id, data.field, data.value);
            checkProjectTicketReadiness();
        } else if (data.action === 'refresh') {
            refreshDashboard();
        }
    } catch (e) {
        console.error('Bad WS message', e);
    }
});

function refreshDashboard() {
    const filters = getFilters();
    const q = Object.entries(filters)
        .filter(([k,v]) => v)
        .map(([k,v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
    fetch('/fragment?' + q)
        .then(res => res.text())
        .then(html => {
            const tmp = document.createElement('div');
            tmp.innerHTML = html;
            const newStats = tmp.querySelector('.stats-container');
            const oldStats = document.querySelector('.stats-container');
            if (newStats && oldStats) oldStats.innerHTML = newStats.innerHTML;
            ['clientList','ramList','technicianList','statusList'].forEach(id => {
                const newList = tmp.querySelector(`#${id}`);
                const oldList = document.querySelector(`#${id}`);
                if (newList && oldList) oldList.innerHTML = newList.innerHTML;
            });
            const newGroups = tmp.querySelector('#clientGroups');
            const oldGroups = document.getElementById('clientGroups');
        if (newGroups && oldGroups) {
            oldGroups.innerHTML = newGroups.innerHTML;
        }
        setupDeleteForms();
        setupSorting();
        checkProjectTicketReadiness();
        filterTable();
    });
}

function setRowCompleted(wsid, completed) {
    const row = document.querySelector('tr[data-wsid="' + wsid + '"]');
    if (!row) return;
    if (completed) {
        row.classList.add('completed-row');
        // Disable all inputs except the automate checkbox and buttons
        row.querySelectorAll('select, input[type="text"], textarea').forEach(el => {
            el.disabled = true;
        });
    } else {
        row.classList.remove('completed-row');
        row.querySelectorAll('select, input[type="text"], textarea').forEach(el => {
            el.disabled = false;
        });
    }
}

function toggleClient(clientId) {
    let el = document.getElementById('client-' + clientId);
    let toggle = document.getElementById('toggle-' + clientId);
    if (el.style.display === "none") {
        el.style.display = "";
        if (toggle) toggle.innerText = "[-]";
    } else {
        el.style.display = "none";
        if (toggle) toggle.innerText = "[+]";
    }
}

// Get filter values
function getFilters() {
    return {
        client: document.getElementById('clientFilter').value.trim().toLowerCase(),
        ram: document.getElementById('ramFilter').value.trim().toLowerCase(),
        technician: document.getElementById('technicianFilter').value.trim().toLowerCase(),
        status: document.getElementById('statusFilter').value.trim().toLowerCase(),
        search: document.getElementById('textSearch').value.trim().toLowerCase(),
        automate: document.getElementById('automateFilter').value
    };
}

function filterTable() {
    let filters = getFilters();
    let filteringActive = (
        filters.client ||
        filters.ram ||
        filters.technician ||
        filters.status ||
        filters.search ||
        filters.automate
    );

    document.querySelectorAll('.client-group').forEach(group => {
        let groupName = group.querySelector('.client-header strong').textContent.toLowerCase();
        let groupVisible = false;
        let table = group.querySelector('table');
        let rows = Array.from(table.querySelectorAll('tr')).slice(1); // skip header
        rows.forEach(row => {
            let cells = row.cells;
            let computer = cells[0].textContent.trim().toLowerCase();
            let processor = cells[1].textContent.trim().toLowerCase();
            let ram = cells[2].textContent.replace(/gb/i, "").trim().toLowerCase();
            let disk = cells[3].textContent.replace(/gb/i, "").trim().toLowerCase();
            let status = cells[4].querySelector('select').value.trim().toLowerCase();
            let technician = cells[5].querySelector('select').value.trim().toLowerCase();
            let notes = cells[6].querySelector('input').value.trim().toLowerCase();
            let automateStatus = row.getAttribute('data-automate');

            let show = true;
            // Partial, case-insensitive matching for all filters
            if (filters.client && !groupName.includes(filters.client)) show = false;
            if (filters.ram && !ram.includes(filters.ram)) show = false;
            if (filters.technician && !technician.includes(filters.technician)) show = false;
            if (filters.status && !status.includes(filters.status)) show = false;
            if (filters.automate && automateStatus !== filters.automate) show = false;
            if (filters.search && !(
                computer.includes(filters.search) ||
                processor.includes(filters.search) ||
                ram.includes(filters.search) ||
                disk.includes(filters.search) ||
                status.includes(filters.search) ||
                technician.includes(filters.search) ||
                notes.includes(filters.search) ||
                groupName.includes(filters.search)
            )) show = false;

            row.style.display = show ? "" : "none";
            if (show) groupVisible = true;
        });

        group.style.display = groupVisible ? "" : "none";

        // Expand matching groups by default when a filter is active
        let workstationsDiv = group.querySelector('.workstations');
        let toggle = group.querySelector('.collapse-toggle');
        if (groupVisible && filteringActive) {
            if (workstationsDiv) workstationsDiv.style.display = "";
            if (toggle) toggle.innerText = "[-]";
        } else if (groupVisible && !filteringActive) {
            if (workstationsDiv) workstationsDiv.style.display = "none";
            if (toggle) toggle.innerText = "[+]";
        }
    });
}

// Add 'X' buttons and logic for each filter
function setupClearXs() {
    [
        {id: 'clientFilter', x: 'clientClearX'},
        {id: 'ramFilter', x: 'ramClearX'},
        {id: 'technicianFilter', x: 'technicianClearX'},
        {id: 'statusFilter', x: 'statusClearX'},
        {id: 'textSearch', x: 'searchClearX'}
    ].forEach(item => {
        let inp = document.getElementById(item.id);
        let xBtn = document.getElementById(item.x);
        if (inp && xBtn) {
            xBtn.onclick = function() {
                inp.value = '';
                filterTable();
            };
            inp.addEventListener('input', function() {
                xBtn.style.display = inp.value ? 'inline' : 'none';
            });
            // Set initial state
            xBtn.style.display = inp.value ? 'inline' : 'none';
        }
    });
}

// Create Project Ticket function
function createProjectTicket(clientId, clientName) {
    if (!confirm(`Create a ConnectWise project ticket for "${clientName}" Windows 11 upgrades?`)) {
        return;
    }
    
    // Show loading state
    const btn = event.target;
    const originalText = btn.innerText;
    btn.disabled = true;
    btn.innerText = 'Creating...';
    
    fetch(`/create-project-ticket/${clientId}`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(`Project ticket #${data.ticket_id} created successfully for ${data.cw_company_name}!`);
            // Hide the button after successful creation
            btn.style.display = 'none';
        } else {
            alert(`Failed to create ticket: ${data.error}`);
            btn.disabled = false;
            btn.innerText = originalText;
        }
    })
    .catch(err => {
        alert(`Error creating ticket: ${err}`);
        btn.disabled = false;
        btn.innerText = originalText;
    });
}

// Check project ticket readiness for all clients
function checkProjectTicketReadiness() {
    document.querySelectorAll('.client-group').forEach(group => {
        const clientHeader = group.querySelector('.client-header');
        const clientId = clientHeader.querySelector('button[onclick*="showAddModal"]')
            ?.getAttribute('onclick')
            ?.match(/showAddModal\((\d+)/)?.[1];
        
        if (!clientId) return;
        
        // Check all workstations in this client
        const rows = group.querySelectorAll('table tr:not(:first-child)');
        let allReady = rows.length > 0;
        
        rows.forEach(row => {
            const statusSelect = row.querySelector('td:nth-child(5) select');
            const techSelect = row.querySelector('td:nth-child(6) select');
            
            if (!statusSelect || !techSelect) {
                allReady = false;
                return;
            }
            
            const status = statusSelect.value;
            const tech = techSelect.value;
            
            if (!status || status === '- Select Status -' || !tech || tech === '') {
                allReady = false;
            }
        });
        
        // Show/hide the project ticket button
        let projectBtn = clientHeader.querySelector('.project-ticket-btn');
        if (allReady && !projectBtn) {
            // Add the button
            const addBtn = clientHeader.querySelector('button[onclick*="showAddModal"]');
            if (addBtn) {
                const newBtn = document.createElement('button');
                newBtn.className = 'import-btn project-ticket-btn';
                newBtn.type = 'button';
                newBtn.innerText = 'Create Project Ticket';
                newBtn.onclick = (e) => {
                    e.stopPropagation();
                    const clientName = clientHeader.querySelector('strong').textContent;
                    createProjectTicket(clientId, clientName);
                };
                addBtn.parentNode.insertBefore(newBtn, addBtn.nextSibling);
                addBtn.parentNode.insertBefore(document.createTextNode(' '), addBtn.nextSibling);
            }
        } else if (!allReady && projectBtn) {
            // Remove the button
            projectBtn.remove();
        }
    });
}

function setupDeleteForms() {
    document.querySelectorAll('form[action$="/delete"]').forEach(form => {
        if (form.dataset.ajax) return;
        form.dataset.ajax = '1';
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!confirm('Delete this workstation?')) return;
            fetch(form.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            }).then(() => refreshDashboard());
        });
    });
}

function setupAddEditForms() {
    const addForm = document.getElementById('addForm');
    if (addForm) {
        addForm.addEventListener('submit', function(e) {
            e.preventDefault();
            fetch(addForm.action, {
                method: 'POST',
                body: new FormData(addForm),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            }).then(() => { closeModal('addModal'); refreshDashboard(); });
        });
    }
    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            fetch(editForm.action, {
                method: 'POST',
                body: new FormData(editForm),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            }).then(() => { closeModal('editModal'); refreshDashboard(); });
        });
    }
}

function sortTable(table, colIndex, type, asc) {
    const rows = Array.from(table.querySelectorAll('tr')).slice(1);
    rows.sort((a, b) => {
        let aVal = a.children[colIndex].textContent.trim();
        let bVal = b.children[colIndex].textContent.trim();
        if (type === 'number') {
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
        } else {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }
        if (aVal < bVal) return asc ? -1 : 1;
        if (aVal > bVal) return asc ? 1 : -1;
        return 0;
    });
    rows.forEach(row => table.appendChild(row));
}

function setupSorting() {
    document.querySelectorAll('.client-group table th').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', function() {
            const table = th.closest('table');
            const index = Array.prototype.indexOf.call(th.parentNode.children, th);
            const type = th.dataset.type || 'string';
            const asc = !(table.dataset.sortCol == index && table.dataset.sortDir === 'asc');
            sortTable(table, index, type, asc);
            table.dataset.sortCol = index;
            table.dataset.sortDir = asc ? 'asc' : 'desc';
        });
    });
}

window.onload = function () {
    // Set up instant filter listeners
    ['clientFilter', 'ramFilter', 'technicianFilter', 'statusFilter', 'textSearch', 'automateFilter'].forEach(id => {
        let el = document.getElementById(id);
        if (el) {
            el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', filterTable);
        }
    });

    setupClearXs();
    filterTable();
    checkProjectTicketReadiness();
    setupDeleteForms();
    setupAddEditForms();
    setupSorting();

    let clearBtn = document.getElementById('clearFilters');
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            ['clientFilter', 'ramFilter', 'technicianFilter', 'statusFilter', 'textSearch'].forEach(id => {
                let el = document.getElementById(id);
                if (el) el.value = '';
            });
            document.getElementById('automateFilter').value = '';
            filterTable();
            setupClearXs();
        });
    }

    // Export button: Export what is currently displayed (filters applied)
    let exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function(e) {
            let filters = getFilters();
            let q = Object.entries(filters)
                .filter(([k, v]) => v)
                .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
                .join('&');
            exportBtn.href = '/export?' + q;
        });
    }
};

// ---- Modal logic for Add/Edit Workstation ----

// Show Add Workstation Modal (ALWAYS sets client ID & company name, for debug shows client id)
function showAddModal(clientId, clientName) {
    let form = document.getElementById('addForm');
    form.reset(); // Clear all fields EXCEPT client_id and client_name
    document.getElementById('add_client_id').value = clientId;
    document.getElementById('add_client_name').innerText = clientName;
    // Debug display
    var dbg = document.getElementById('debug_client_id');
    if (dbg) dbg.innerText = clientId;
    document.getElementById('addModal').style.display = 'flex';
}
window.showAddModal = showAddModal;

// Show Edit Workstation Modal (fetch workstation details from DOM)
function showEditModal(wsId) {
    let row = document.querySelector(`tr[data-wsid='${wsId}']`);
    if (!row) row = document.querySelector(`button[onclick='showEditModal(${wsId})']`).closest('tr');
    document.getElementById('editForm').action = `/workstations/${wsId}/edit`;
    document.getElementById('edit_computer_name').value = row.children[0].innerText;
    document.getElementById('edit_processor_name').value = row.children[1].innerText;
    document.getElementById('edit_ram_gb').value = row.children[2].innerText.replace("GB", "");
    document.getElementById('edit_diskspace_remaining_gb').value = row.children[3].innerText.replace("GB", "");
    document.getElementById('edit_status').value = row.children[4].querySelector('select').value;
    document.getElementById('edit_technician').value = row.children[5].querySelector('select').value;
    document.getElementById('edit_notes').value = row.children[6].querySelector('input').value;
    document.getElementById('editModal').style.display = 'flex';
}
window.showEditModal = showEditModal;

// Close Modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}
window.closeModal = closeModal;

// Allow clicking outside modal to close it
document.addEventListener('click', function(e) {
    if (e.target.classList && e.target.classList.contains('modal')) closeModal(e.target.id);
});

// Make functions available globally
window.updateAutomateStatus = updateAutomateStatus;
window.createProjectTicket = createProjectTicket;
window.checkProjectTicketReadiness = checkProjectTicketReadiness;
