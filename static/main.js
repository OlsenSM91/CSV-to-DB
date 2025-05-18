function updateField(id, field, value) {
    fetch("/update", {
        method: "POST",
        body: new URLSearchParams({ id, field, value })
    }).then(res => res.json());
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
        search: document.getElementById('textSearch').value.trim().toLowerCase()
    };
}

function filterTable() {
    let filters = getFilters();
    let filteringActive = (
        filters.client ||
        filters.ram ||
        filters.technician ||
        filters.status ||
        filters.search
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

            let show = true;
            // Partial, case-insensitive matching for all filters
            if (filters.client && !groupName.includes(filters.client)) show = false;
            if (filters.ram && !ram.includes(filters.ram)) show = false;
            if (filters.technician && !technician.includes(filters.technician)) show = false;
            if (filters.status && !status.includes(filters.status)) show = false;
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

window.onload = function () {
    // Set up instant filter listeners
    ['clientFilter', 'ramFilter', 'technicianFilter', 'statusFilter', 'textSearch'].forEach(id => {
        let el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', filterTable);
        }
    });

    setupClearXs();
    filterTable();

    let clearBtn = document.getElementById('clearFilters');
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            ['clientFilter', 'ramFilter', 'technicianFilter', 'statusFilter', 'textSearch'].forEach(id => {
                let el = document.getElementById(id);
                if (el) el.value = '';
            });
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
