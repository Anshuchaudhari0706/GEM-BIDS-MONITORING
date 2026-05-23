let mockBids = [];
let currentTab = 'published';
let currentCategory = 'ALL';
let currentStateFilter = 'Gujarat';
let currentEmpFilter = 'all';
let filteredBids = [];
let pollTimer = null;
let totalFromGeM = 0; // raw total returned by API before any filtering
let lastScanDate = null;  // YYYY-MM-DD of the date that was actually scanned

// Returns today's date in yyyy-mm-dd (local time)
function getTodayDateStr() {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm   = String(now.getMonth() + 1).padStart(2, '0');
    const dd   = String(now.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

// ─── API Integration ─────────────────────────────────────────────────────

async function loadBidsFromAPI() {
    try {
        const response = await fetch('/api/bids');
        const result = await response.json();
        if (result.status === 'success') {
            mockBids = result.data || [];
            lastScanDate = result.scan_date || null;
            updateScanBadge(result);
            applyFilters();
        }
    } catch (error) {
        console.error("Error loading from API:", error);
        setScanStatus('⚠️ Cannot reach server. Is server.py running?', 'error');
    }
}

async function triggerScan() {
    if (isCurrentlyScanning()) return;

    const btn = document.getElementById('scan-now-btn');
    btn.disabled = true;

    const stateFilter = document.getElementById('state-filter')?.value;
    const scanDate = document.getElementById('scan-date-picker')?.value;

    setScanStatus('⏳ Launching Chrome... scanning live GeM portal...', 'scanning');

    try {
        await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: currentTab,
                state: stateFilter !== 'ALL' ? stateFilter : null,
                date: scanDate
            })
        });

        // Poll status every 3 seconds until done
        pollTimer = setInterval(async () => {
            const status = await fetch('/api/status').then(r => r.json());
            if (!status.is_scanning) {
                clearInterval(pollTimer);
                await loadBidsFromAPI();
                btn.disabled = false;
            } else {
                setScanStatus(`⏳ Scanning GeM... (${status.total_bids} found so far)`, 'scanning');
            }
        }, 3000);

    } catch (e) {
        setScanStatus('❌ Scan failed. Check server.py is running.', 'error');
        btn.disabled = false;
    }
}

function isCurrentlyScanning() {
    return document.getElementById('scan-now-btn')?.disabled;
}

function setScanStatus(msg, type) {
    const el = document.getElementById('scan-status');
    if (!el) return;
    el.textContent = msg;
    el.className = `scan-status scan-${type}`;
}

function updateScanBadge(result) {
    const el = document.getElementById('last-scan-time');
    if (el && result.last_scan) {
        el.textContent = result.last_scan;
    }
    if (result.is_scanning) {
        setScanStatus('⏳ Scanning in progress...', 'scanning');
        updateSidebarCount(null, null);
    } else if (result.scan_error) {
        setScanStatus(`❌ Last scan error: ${result.scan_error}`, 'error');
        updateSidebarCount(null, null);
    } else if (result.last_scan) {
        totalFromGeM = result.total || 0;
        setScanStatus(`✅ Last scan: ${result.last_scan}`, 'success');
        // sidebar count updated by applyFilters after data loads
    } else {
        setScanStatus('🔍 No scan yet. Click "Scan GeM Now" to fetch live data.', 'idle');
        updateSidebarCount(null, null);
    }
}

function updateSidebarCount(filtered, total) {
    const el = document.getElementById('sidebar-count');
    if (!el) return;
    if (filtered === null) {
        el.style.display = 'none';
        return;
    }
    el.style.display = 'flex';
    el.innerHTML = `
        <span class="sc-label">Showing</span>
        <span class="sc-filtered">${filtered}</span>
        <span class="sc-label">of</span>
        <span class="sc-total">${total}</span>
        <span class="sc-label">from GeM</span>
    `;
}

// ─── Tab Switching ────────────────────────────────────────────────────────

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');
    if (tab === 'published') {
        pageTitle.textContent = "Published Bids";
        pageSubtitle.innerHTML = `Bids published on the official <strong>GeM Portal</strong>`;
    } else {
        updateFinishedSubtitle();
    }
    applyFilters();
}

// ─── Finished subtitle helper ────────────────────────────────────────────

function updateFinishedSubtitle() {
    const pageTitle    = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');
    if (!pageTitle || !pageSubtitle) return;

    const pickerVal = document.getElementById('scan-date-picker')?.value;
    let dateLabel = 'selected date';
    if (pickerVal) {
        const [yyyy, mm, dd] = pickerVal.split('-');
        const d = new Date(parseInt(yyyy), parseInt(mm) - 1, parseInt(dd));
        dateLabel = d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
    }
    pageTitle.textContent = 'Finished Bids';
    pageSubtitle.innerHTML =
        `Bids whose <strong>End Date = ${dateLabel}</strong> — change the date picker above to browse any day`;
}

// ─── Filters ──────────────────────────────────────────────────────────────

function applyFilters() {
    currentCategory = document.getElementById('category-filter').value;
    currentStateFilter = document.getElementById('state-filter')?.value || 'ALL';
    currentEmpFilter = document.querySelector('input[name="emp-count"]:checked').value;

    // Show/hide manpower sub-filter for all staff categories
    const manpowerCats = ['SECURITY','HOUSEKEEPING','DATA_ENTRY','DRIVER','IT_MANPOWER','ELECTRICIAN','HELPER','FACILITY_MGMT','OUTSOURCING','MANPOWER'];
    const manpowerFilters = document.getElementById('manpower-filters');
    if (manpowerFilters) {
        manpowerFilters.style.display = manpowerCats.includes(currentCategory) ? 'block' : 'none';
    }

    // Date picker value used as the reference date for Finished tab
    const pickerDate = document.getElementById('scan-date-picker')?.value || getTodayDateStr();

    // Refresh the finished subtitle whenever filters run
    if (currentTab === 'finished') updateFinishedSubtitle();

    // Show stale-data warning if the selected date doesn't match the last scan date
    const staleWarn = document.getElementById('stale-date-warn');
    if (staleWarn) {
        if (currentTab === 'finished' && lastScanDate && pickerDate !== lastScanDate) {
            const [sy, sm, sd] = lastScanDate.split('-');
            const [py, pm, pd] = pickerDate.split('-');
            staleWarn.style.display = 'flex';
            staleWarn.innerHTML = `⚠️ Data shown is from <strong>${sd}/${sm}/${sy}</strong>. 
                Click <strong>Scan GeM Now</strong> to fetch bids for <strong>${pd}/${pm}/${py}</strong>.`;
        } else {
            staleWarn.style.display = 'none';
        }
    }

    filteredBids = mockBids.filter(bid => {
        // ── Tab matching ──────────────────────────────────────────────
        if (currentTab === 'finished') {
            // Show bid if its End Date (deadline) matches the SELECTED date in the picker
            // Works for today, tomorrow, or any past/future date the user chooses
            const bidEndDate = (bid.deadline || bid.rawEndDate || '').substring(0, 10);
            if (bidEndDate !== pickerDate) return false;
        } else {
            // Published tab: only show bids marked as published or ongoing
            if (bid.status !== 'published' && bid.status !== 'ongoing') return false;
        }

        // ── State filter ──────────────────────────────────────────────
        // If ALL, show everything.
        // If a specific state is selected, show bids that match OR are tagged
        // as 'Pan India' (since GeM already filtered by state server-side)
        if (currentStateFilter !== 'ALL') {
            const bidState   = (bid.state || '').toLowerCase();
            const filterState = currentStateFilter.toLowerCase();
            if (bidState !== filterState && bidState !== 'pan india') return false;
        }

        // ── Category filter ───────────────────────────────────────────
        if (currentCategory !== 'ALL' && bid.category !== currentCategory) return false;
        if (currentCategory === 'MANPOWER') {
            if (currentEmpFilter === 'lt50'  && bid.employees >= 50)  return false;
            if (currentEmpFilter === 'gt50'  && bid.employees <= 50)  return false;
            if (currentEmpFilter === 'gt100' && bid.employees <= 100) return false;
        }
        return true;
    });

    // Update stat counter (right side card)
    const statTotal = document.getElementById('stat-total');
    if (statTotal) statTotal.textContent = filteredBids.length;

    // Update sidebar count (left side)
    updateSidebarCount(filteredBids.length, totalFromGeM || mockBids.length);

    renderTable();
}

// ─── Render Table ─────────────────────────────────────────────────────────

function formatCurrency(value) {
    if (!value) return '—';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
}

function renderTable() {
    const tbody = document.getElementById('bids-tbody');
    const noDataMsg = document.getElementById('no-data-msg');
    let totalValue = 0;
    tbody.innerHTML = '';

    if (filteredBids.length === 0) {
        tbody.style.display = 'none';
        noDataMsg.style.display = 'flex';
    } else {
        tbody.style.display = 'table-row-group';
        noDataMsg.style.display = 'none';

        filteredBids.forEach(bid => {
            totalValue += bid.value || 0;
            const tr = document.createElement('tr');

            // Badge uses category as CSS class directly
            const manpowerTypes = ['SECURITY','HOUSEKEEPING','DATA_ENTRY','DRIVER','IT_MANPOWER','ELECTRICIAN','HELPER','FACILITY_MGMT','OUTSOURCING','MANPOWER'];
            let empDetails = manpowerTypes.includes(bid.category) && bid.employees > 0
                ? `<div class="emp-req">Min. staff: ${bid.employees}</div>` : '';
            let statusClass = 'status-finished';
            let statusText = 'Finished';
            if (bid.status === 'published') {
                statusClass = 'status-published';
                statusText = 'Published';
            } else if (bid.status === 'ongoing') {
                statusClass = 'status-ongoing';
                statusText = 'Ongoing';
            }
            let cityHtml = bid.city ? `<div class="city">${bid.city}</div>` : '';
            let valueHtml = bid.value > 0 ? formatCurrency(bid.value) : '<span style="color:#64748b;font-size:0.8rem;">In Document</span>';
            const catLabel = (bid.category || 'OTHER').replace('_', ' ');

            tr.innerHTML = `
                <td>
                    <div class="bid-id">
                        <a href="${bid.gemLink}" target="_blank" style="color:var(--accent-color);text-decoration:none;">${bid.id}</a>
                    </div>
                </td>
                <td>
                    <div class="bid-title">${bid.title}</div>
                    <div class="bid-dept">${bid.department}</div>
                </td>
                <td>
                    <span class="badge ${bid.category}">${catLabel}</span>
                    ${empDetails}
                    ${bid.quantity ? `<div class="emp-req">Qty: ${bid.quantity}</div>` : ''}
                </td>
                <td>
                    <div class="location">${bid.state}</div>
                    ${cityHtml}
                </td>
                <td><div class="val-est">${valueHtml}</div></td>
                <td>
                    <div class="date-group"><span class="date-label">Start:</span> <span style="white-space:nowrap">${bid.rawStartDate || bid.publishedDate}</span></div>
                    <div class="date-group"><span class="date-label">End:</span> <span style="white-space:nowrap">${bid.rawEndDate || bid.deadline}</span></div>
                </td>
                <td>
                    <div class="status-badge ${statusClass}">${statusText}</div>
                    <div style="margin-top:0.4rem;">
                        <a href="${bid.gemLink}" target="_blank" class="gem-link-btn">View on GeM →</a>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    document.getElementById('stat-total').textContent = filteredBids.length;
    document.getElementById('stat-value').textContent =
        totalValue > 0 ? formatCurrency(totalValue) : `${filteredBids.length} Bids`;
}

// ─── PDF Generation ───────────────────────────────────────────────────────

function generateAdvancedPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF('portrait');
    const reportType = document.getElementById('report-type').value;
    const dateStr = new Date().toLocaleDateString('en-IN');

    let reportTitle = "GeM Intelligence Report";
    let bidsToExport = [];

    switch (reportType) {
        case 'daily':
            reportTitle = `Daily Report — ${currentTab === 'published' ? 'Published' : 'Finished'} Today`;
            bidsToExport = filteredBids;
            break;
        case 'state':
            reportTitle = `State-wise Report: ${currentStateFilter}`;
            bidsToExport = mockBids.filter(b => currentStateFilter === 'ALL' || b.state === currentStateFilter);
            break;
        case 'category':
            reportTitle = `Category Report: ${currentCategory === 'ALL' ? 'All Categories' : currentCategory}`;
            bidsToExport = mockBids.filter(b => currentCategory === 'ALL' || b.category === currentCategory);
            break;
        case 'high-value':
            reportTitle = "High-Value Bids (> ₹50 Lakhs)";
            bidsToExport = mockBids.filter(b => b.value > 5000000);
            break;
        case 'custom':
            reportTitle = "Custom Client Report — Manpower Bids";
            bidsToExport = mockBids.filter(b => b.category === 'MANPOWER');
            break;
    }

    // Header
    doc.setFontSize(22);
    doc.setTextColor(15, 23, 42);
    doc.text("GeM Intelligence", 14, 20);
    doc.setFontSize(13);
    doc.setTextColor(59, 130, 246);
    doc.text(reportTitle, 14, 28);
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139);
    doc.text(`Generated: ${dateStr}  |  Source: bidplus.gem.gov.in  |  Total: ${bidsToExport.length} bids`, 14, 34);

    // Separator line
    doc.setDrawColor(59, 130, 246);
    doc.setLineWidth(0.5);
    doc.line(14, 37, 196, 37);

    let yPos = 44;

    if (bidsToExport.length === 0) {
        doc.setFontSize(11);
        doc.setTextColor(100, 116, 139);
        doc.text("No bids match the current filter criteria.", 14, yPos);
    }

    bidsToExport.forEach((bid, idx) => {
        // Calculate card height dynamically
        const baseHeight = 80;
        if (yPos + baseHeight > 275) {
            doc.addPage();
            yPos = 20;
        }

        const cardH = baseHeight;

        // Card background
        doc.setFillColor(248, 250, 252);
        doc.setDrawColor(226, 232, 240);
        doc.roundedRect(14, yPos, 182, cardH, 2, 2, 'FD');

        // Left accent bar — color by category
        const catColors = {
            'SECURITY':      [239, 68, 68],
            'HOUSEKEEPING':  [16, 185, 129],
            'DATA_ENTRY':    [245, 158, 11],
            'DRIVER':        [59, 130, 246],
            'IT_MANPOWER':   [99, 102, 241],
            'ELECTRICIAN':   [234, 179, 8],
            'HELPER':        [107, 114, 128],
            'FACILITY_MGMT': [20, 184, 166],
            'OUTSOURCING':   [236, 72, 153],
            'MANPOWER':      [139, 92, 246],
            'IT':            [59, 130, 246],
            'OTHER':         [100, 116, 139],
        };
        const accentColor = catColors[bid.category] || [100, 116, 139];
        doc.setFillColor(...accentColor);
        doc.rect(14, yPos, 3, cardH, 'F');

        // Serial number
        doc.setFont("helvetica", "bold");
        doc.setFontSize(7);
        doc.setTextColor(100, 116, 139);
        doc.text(`#${idx + 1}`, 19, yPos + 5);

        // Bid ID
        doc.setFont("helvetica", "bold");
        doc.setFontSize(9);
        doc.setTextColor(...accentColor);
        doc.text(bid.id || 'N/A', 28, yPos + 5);

        // Category badge
        doc.setFillColor(...accentColor);
        doc.roundedRect(148, yPos + 1.5, 44, 6, 1, 1, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(6.5);
        doc.text((bid.category || 'OTHER').replace('_', ' '), 170, yPos + 5.5, { align: 'center' });

        // Title
        doc.setFont("helvetica", "bold");
        doc.setFontSize(9.5);
        doc.setTextColor(15, 23, 42);
        const titleLines = doc.splitTextToSize(bid.title || '', 166);
        doc.text(titleLines.slice(0, 2), 19, yPos + 12);

        // Department
        doc.setFont("helvetica", "normal");
        doc.setFontSize(7.5);
        doc.setTextColor(71, 85, 105);
        const deptTxt = doc.splitTextToSize(`Dept: ${bid.department || 'N/A'}`, 166);
        doc.text(deptTxt.slice(0, 1), 19, yPos + 20);

        // ── Left column details ──
        const col1X = 19, col2X = 105, row1Y = yPos + 27;
        doc.setFontSize(7.5);

        // Row 1
        doc.setFont("helvetica", "bold"); doc.setTextColor(71, 85, 105);
        doc.text("Location:", col1X, row1Y);
        doc.setFont("helvetica", "normal"); doc.setTextColor(15, 23, 42);
        doc.text(`${bid.city ? bid.city + ', ' : ''}${bid.state || 'N/A'}`, col1X + 18, row1Y);

        doc.setFont("helvetica", "bold"); doc.setTextColor(71, 85, 105);
        doc.text("EMD:", col2X, row1Y);
        doc.setFont("helvetica", "normal"); doc.setTextColor(15, 23, 42);
        doc.text(bid.emd || 'As per document', col2X + 11, row1Y);

        // Row 2
        const row2Y = row1Y + 6;
        doc.setFont("helvetica", "bold"); doc.setTextColor(71, 85, 105);
        doc.text("Published:", col1X, row2Y);
        doc.setFont("helvetica", "normal"); doc.setTextColor(15, 23, 42);
        doc.text(bid.rawStartDate || bid.publishedDate || 'N/A', col1X + 21, row2Y);

        doc.setFont("helvetica", "bold"); doc.setTextColor(71, 85, 105);
        doc.text("Value:", col2X, row2Y);
        doc.setFont("helvetica", "normal"); doc.setTextColor(15, 23, 42);
        doc.text(bid.value > 0 ? `₹${bid.value.toLocaleString('en-IN')}` : 'In Document', col2X + 14, row2Y);

        // Row 3
        const row3Y = row2Y + 6;
        doc.setFont("helvetica", "bold"); doc.setTextColor(239, 68, 68);
        doc.text("End Date:", col1X, row3Y);
        doc.setFont("helvetica", "bold"); doc.setTextColor(239, 68, 68);
        doc.text(bid.rawEndDate || bid.deadline || 'N/A', col1X + 20, row3Y);

        doc.setFont("helvetica", "bold"); doc.setTextColor(71, 85, 105);
        doc.text("Min Staff:", col2X, row3Y);
        doc.setFont("helvetica", "normal"); doc.setTextColor(15, 23, 42);
        doc.text(bid.employees > 0 ? `${bid.employees} persons` : 'See document', col2X + 18, row3Y);

        // Row 4
        const row4Y = row3Y + 6;
        doc.setFont("helvetica", "bold"); doc.setTextColor(71, 85, 105);
        doc.text("MSME:", col1X, row4Y);
        doc.setFont("helvetica", "normal"); doc.setTextColor(15, 23, 42);
        doc.text("Exemption applicable (verify in doc)", col1X + 14, row4Y);

        doc.setFont("helvetica", "bold"); doc.setTextColor(71, 85, 105);
        doc.text("Turnover:", col2X, row4Y);
        doc.setFont("helvetica", "normal"); doc.setTextColor(15, 23, 42);
        doc.text("As per bid document", col2X + 19, row4Y);

        // Row 5 — Experience
        const row5Y = row4Y + 6;
        doc.setFont("helvetica", "bold"); doc.setTextColor(71, 85, 105);
        doc.text("Experience:", col1X, row5Y);
        doc.setFont("helvetica", "normal"); doc.setTextColor(15, 23, 42);
        doc.text("Refer to official bid document", col1X + 22, row5Y);

        // AI Insight
        const aiY = row5Y + 6;
        doc.setFont("helvetica", "bolditalic");
        doc.setFontSize(7);
        doc.setTextColor(...accentColor);
        doc.text("AI Insight: ", col1X, aiY);
        doc.setFont("helvetica", "italic");
        doc.setTextColor(100, 116, 139);
        const aiLines = doc.splitTextToSize(bid.aiSummary || '', 150);
        doc.text(aiLines.slice(0, 1), col1X + 19, aiY);

        // GeM Link
        doc.setFont("helvetica", "normal");
        doc.setFontSize(7);
        doc.setTextColor(37, 99, 235);
        doc.text(bid.gemLink || '', col1X, yPos + cardH - 3);

        yPos += cardH + 3;
    });

    const fileName = `GeM_Gujarat_Report_${reportType}_${dateStr.replace(/\//g, '-')}.pdf`;
    doc.save(fileName);
}

// ─── DOMContentLoaded ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Set today's date
    document.getElementById('current-date').textContent =
        new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    // Set today's date in date picker using local clock (IST-safe)
    const datePicker = document.getElementById('scan-date-picker');
    if (datePicker) {
        datePicker.value = getTodayDateStr();
    }

    // Category filter change
    document.getElementById('category-filter').addEventListener('change', applyFilters);
    document.querySelectorAll('input[name="emp-count"]').forEach(r => r.addEventListener('change', applyFilters));
    document.getElementById('state-filter')?.addEventListener('change', applyFilters);

    // When user changes the date picker, re-filter immediately (Finished tab date changes)
    document.getElementById('scan-date-picker')?.addEventListener('change', applyFilters);

    // Load from API
    loadBidsFromAPI();

    // Auto-refresh status every 10 seconds
    setInterval(async () => {
        const status = await fetch('/api/status').then(r => r.json()).catch(() => null);
        if (status) updateScanBadge({ ...status, total: status.total_bids });
    }, 10000);
});
