/**
 * Control Mapping Updater - Google Apps Script
 * Syncs Suggested Mappings from a Master Google Sheet to a target CSV file in Google Drive.
 * Only adds missing mappings - never removes or alters existing ones.
 *
 * SETUP:
 * 1. Create a new Apps Script project at script.google.com
 * 2. Paste this entire script
 * 3. Set MASTER_SPREADSHEET_ID below to your master spreadsheet ID
 * 4. Deploy as web app (Deploy > New deployment > Web app)
 *    - Execute as: Me
 *    - Who has access: Anyone (or your organization)
 * 5. Open the deployed web app URL to use the file picker
 */

// ============ CONFIGURATION ============
// Paste your Master spreadsheet ID here (from the URL)
const MASTER_SPREADSHEET_ID = '1sU7GiyExI_wfV1Qq4JzWh_7WCVSZ2EB764XERWCpTFk';

// Master sheet column names
const MASTER_TITLE_COLUMN = '3.5 Title';        // Primary match (Column A)
const MASTER_LEGACY_COLUMN = 'Legacy Title';     // Fallback match (Column B)
const MASTER_MAPPINGS_COLUMN = 'Suggested Mappings'; // Column C

// Target file column names
const TARGET_CAPABILITY_COLUMN = 'Solution Capability';
const TARGET_MAPPINGS_COLUMN = 'Suggested Mappings';
// ========================================

/**
 * Serves the HTML file picker interface
 */
function doGet() {
  return HtmlService.createHtmlOutput(getPickerHtml())
    .setTitle('Control Mapping Updater')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * Called from the HTML when user uploads a file
 */
function processUploadedFile(csvContent, fileName, dryRun) {
  // Validate master spreadsheet ID
  if (MASTER_SPREADSHEET_ID === 'YOUR_MASTER_SPREADSHEET_ID_HERE') {
    return {
      success: false,
      error: 'Please edit the script and set MASTER_SPREADSHEET_ID to your master spreadsheet ID.'
    };
  }

  try {
    const result = syncMappingsFromContent(MASTER_SPREADSHEET_ID, csvContent, fileName, dryRun);
    return { success: true, result: result, dryRun: dryRun };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Core sync logic - processes CSV content and returns updated content
 */
function syncMappingsFromContent(masterId, csvContent, fileName, dryRun) {
  // Load master spreadsheet (Google Sheet)
  const masterSs = SpreadsheetApp.openById(masterId);
  const masterSheet = masterSs.getSheets()[0];
  const masterData = masterSheet.getDataRange().getValues();

  // Parse target CSV content
  const targetData = parseCsv(csvContent);

  // Find column indices
  const masterHeaders = masterData[0];
  const targetHeaders = targetData[0];

  const masterTitleIdx = findColumnIndex(masterHeaders, MASTER_TITLE_COLUMN);
  const masterLegacyIdx = findColumnIndex(masterHeaders, MASTER_LEGACY_COLUMN);
  const masterMapIdx = findColumnIndex(masterHeaders, MASTER_MAPPINGS_COLUMN);
  const targetCapIdx = findColumnIndex(targetHeaders, TARGET_CAPABILITY_COLUMN);
  const targetMapIdx = findColumnIndex(targetHeaders, TARGET_MAPPINGS_COLUMN);

  // Build master lookups (primary by 3.5 Title, fallback by Legacy Title)
  const { titleLookup, legacyLookup } = buildMasterLookups(masterData, masterTitleIdx, masterLegacyIdx, masterMapIdx);

  // Track changes
  const stats = {
    fileName: fileName,
    capabilitiesUpdated: 0,
    mappingsAdded: 0,
    notInMaster: [],
    updates: []
  };

  // Process target rows (skip header)
  for (let i = 1; i < targetData.length; i++) {
    const row = targetData[i];

    // Ensure row has enough columns
    while (row.length <= targetMapIdx) {
      row.push('');
    }

    const capNameRaw = row[targetCapIdx];

    if (!capNameRaw || !String(capNameRaw).trim()) {
      continue;
    }

    const capName = normalizeCapabilityName(String(capNameRaw));

    // Try to find in 3.5 Title first, then Legacy Title
    let masterMappings = null;
    let matchedVia = null;

    if (titleLookup.hasOwnProperty(capName)) {
      masterMappings = titleLookup[capName];
      matchedVia = '3.5 Title';
    } else if (legacyLookup.hasOwnProperty(capName)) {
      masterMappings = legacyLookup[capName];
      matchedVia = 'Legacy Title';
    } else {
      if (stats.notInMaster.indexOf(capName) === -1) {
        stats.notInMaster.push(capName);
      }
      continue;
    }

    const currentMappings = parseMappings(String(row[targetMapIdx] || ''));
    const missingMappings = difference(masterMappings, currentMappings);

    if (missingMappings.size > 0) {
      const allMappings = union(currentMappings, missingMappings);
      const newValue = Array.from(allMappings).sort().join('\n');

      row[targetMapIdx] = newValue;

      stats.capabilitiesUpdated++;
      stats.mappingsAdded += missingMappings.size;
      stats.updates.push({
        row: i + 1,
        capability: capName,
        added: missingMappings.size
      });
    }
  }

  // Generate updated CSV content if not dry run and there were changes
  if (!dryRun && stats.capabilitiesUpdated > 0) {
    const newContent = arrayToCsv(targetData);
    const newFileName = 'UPDATED_' + fileName;
    stats.newFileName = newFileName;
    stats.updatedContent = newContent;
  }

  return stats;
}

/**
 * Parse CSV content into 2D array
 * Handles quoted fields with commas and newlines
 */
function parseCsv(content) {
  const rows = [];
  let currentRow = [];
  let currentField = '';
  let inQuotes = false;

  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    const nextChar = content[i + 1];

    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          // Escaped quote
          currentField += '"';
          i++;
        } else {
          // End of quoted field
          inQuotes = false;
        }
      } else {
        currentField += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === ',') {
        currentRow.push(currentField);
        currentField = '';
      } else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
        currentRow.push(currentField);
        rows.push(currentRow);
        currentRow = [];
        currentField = '';
        if (char === '\r') i++; // Skip \n after \r
      } else if (char !== '\r') {
        currentField += char;
      }
    }
  }

  // Don't forget the last field/row
  if (currentField || currentRow.length > 0) {
    currentRow.push(currentField);
    rows.push(currentRow);
  }

  return rows;
}

/**
 * Convert 2D array back to CSV string
 */
function arrayToCsv(data) {
  return data.map(row => {
    return row.map(field => {
      const str = String(field);
      // Quote field if it contains comma, newline, or quote
      if (str.includes(',') || str.includes('\n') || str.includes('"')) {
        return '"' + str.replace(/"/g, '""') + '"';
      }
      return str;
    }).join(',');
  }).join('\n');
}

/**
 * Build two lookup dictionaries:
 * - titleLookup: from "3.5 Title" to set of mappings
 * - legacyLookup: from "Legacy Title" to set of mappings
 */
function buildMasterLookups(data, titleIdx, legacyIdx, mapIdx) {
  const titleLookup = {};
  const legacyLookup = {};

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const titleName = normalizeCapabilityName(String(row[titleIdx] || ''));
    const legacyName = normalizeCapabilityName(String(row[legacyIdx] || ''));
    const mappings = parseMappings(String(row[mapIdx] || ''));

    // Add to title lookup (3.5 Title - Column A)
    if (titleName) {
      if (titleLookup.hasOwnProperty(titleName)) {
        mappings.forEach(m => titleLookup[titleName].add(m));
      } else {
        titleLookup[titleName] = new Set(mappings);
      }
    }

    // Add to legacy lookup (Legacy Title - Column B)
    if (legacyName) {
      if (legacyLookup.hasOwnProperty(legacyName)) {
        mappings.forEach(m => legacyLookup[legacyName].add(m));
      } else {
        legacyLookup[legacyName] = new Set(mappings);
      }
    }
  }

  return { titleLookup, legacyLookup };
}

/**
 * Normalize capability name for comparison
 */
function normalizeCapabilityName(name) {
  return name.trim().replace(/:$/, '').trim();
}

/**
 * Parse mappings string into a Set
 */
function parseMappings(mappingStr) {
  const result = new Set();
  if (!mappingStr || !mappingStr.trim()) {
    return result;
  }

  mappingStr.split('\n').forEach(m => {
    const trimmed = m.trim();
    if (trimmed) {
      result.add(trimmed);
    }
  });

  return result;
}

/**
 * Find column index by header name
 */
function findColumnIndex(headers, columnName) {
  for (let i = 0; i < headers.length; i++) {
    if (String(headers[i]).trim() === columnName) {
      return i;
    }
  }
  throw new Error(`Column "${columnName}" not found. Available columns: ${headers.join(', ')}`);
}

/**
 * Set difference: elements in setA but not in setB
 */
function difference(setA, setB) {
  const result = new Set();
  setA.forEach(item => {
    if (!setB.has(item)) {
      result.add(item);
    }
  });
  return result;
}

/**
 * Set union: elements in either setA or setB
 */
function union(setA, setB) {
  const result = new Set(setA);
  setB.forEach(item => result.add(item));
  return result;
}

/**
 * HTML for the file upload interface
 */
function getPickerHtml() {
  return `
<!DOCTYPE html>
<html>
<head>
  <base target="_top">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      margin: 0;
      padding: 20px;
      background: #f8fafc;
      min-height: 100vh;
    }
    .container {
      max-width: 500px;
      margin: 0 auto;
    }
    h1 {
      color: #1e293b;
      font-size: 24px;
      font-weight: 600;
      margin: 0 0 8px 0;
    }
    .subtitle {
      color: #64748b;
      margin: 0 0 24px 0;
    }
    .card {
      background: white;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      margin-bottom: 16px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      width: 100%;
      margin-bottom: 12px;
    }
    .btn:last-child { margin-bottom: 0; }
    .btn-primary {
      background: #3b82f6;
      color: white;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary {
      background: #f1f5f9;
      color: #475569;
    }
    .btn-secondary:hover { background: #e2e8f0; }
    .btn-success {
      background: #10b981;
      color: white;
    }
    .btn-success:hover { background: #059669; }
    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .file-upload {
      border: 2px dashed #cbd5e1;
      border-radius: 8px;
      padding: 24px;
      text-align: center;
      margin-bottom: 16px;
      transition: all 0.2s;
      cursor: pointer;
    }
    .file-upload:hover {
      border-color: #3b82f6;
      background: #f8fafc;
    }
    .file-upload.dragover {
      border-color: #3b82f6;
      background: #eff6ff;
    }
    .file-upload input {
      display: none;
    }
    .file-upload-icon {
      font-size: 32px;
      margin-bottom: 8px;
    }
    .file-upload-text {
      color: #64748b;
      font-size: 14px;
    }
    .file-upload-text strong {
      color: #3b82f6;
    }
    .selected-file {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 16px;
      display: none;
    }
    .selected-file.show { display: block; }
    .selected-file .label {
      font-size: 12px;
      color: #15803d;
      font-weight: 500;
      margin-bottom: 4px;
    }
    .selected-file .name {
      color: #166534;
      font-weight: 500;
      word-break: break-all;
    }
    .results {
      display: none;
    }
    .results.show { display: block; }
    .results h3 {
      margin: 0 0 12px 0;
      color: #1e293b;
      font-size: 16px;
    }
    .stat {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid #f1f5f9;
    }
    .stat:last-child { border-bottom: none; }
    .stat-label { color: #64748b; }
    .stat-value { font-weight: 600; color: #1e293b; }
    .warning {
      background: #fef3c7;
      border: 1px solid #fcd34d;
      border-radius: 8px;
      padding: 12px 16px;
      margin-top: 16px;
      font-size: 13px;
      color: #92400e;
    }
    .success {
      background: #d1fae5;
      border: 1px solid #6ee7b7;
      border-radius: 8px;
      padding: 12px 16px;
      margin-top: 16px;
      font-size: 13px;
      color: #065f46;
    }
    .error {
      background: #fee2e2;
      border: 1px solid #fca5a5;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 13px;
      color: #991b1b;
    }
    .loading {
      text-align: center;
      padding: 20px;
      color: #64748b;
    }
    .not-in-master {
      background: #fef3c7;
      border: 1px solid #fcd34d;
      border-radius: 8px;
      padding: 16px;
      margin-top: 16px;
    }
    .not-in-master h4 {
      margin: 0 0 8px 0;
      color: #92400e;
      font-size: 14px;
      font-weight: 600;
    }
    .not-in-master ul {
      margin: 0;
      padding-left: 20px;
      font-size: 13px;
      color: #78350f;
      max-height: 200px;
      overflow-y: auto;
    }
    .not-in-master li {
      margin-bottom: 4px;
    }
    .updates-list {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 16px;
      margin-top: 16px;
    }
    .updates-list h4 {
      margin: 0 0 12px 0;
      color: #1e40af;
      font-size: 14px;
      font-weight: 600;
    }
    .updates-list-inner {
      max-height: 300px;
      overflow-y: auto;
    }
    .update-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: white;
      border-radius: 6px;
      margin-bottom: 6px;
      font-size: 13px;
    }
    .update-item:last-child {
      margin-bottom: 0;
    }
    .update-item .cap-name {
      color: #1e293b;
      flex: 1;
      margin-right: 12px;
      word-break: break-word;
    }
    .update-item .cap-count {
      background: #3b82f6;
      color: white;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
      white-space: nowrap;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Control Mapping Updater</h1>
    <p class="subtitle">Sync suggested mappings from master to target CSV</p>

    <div class="card">
      <div class="file-upload" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <input type="file" id="fileInput" accept=".csv" onchange="handleFileSelect(event)">
        <div class="file-upload-icon">📄</div>
        <div class="file-upload-text">
          <strong>Click to upload</strong> or drag and drop<br>
          CSV files only
        </div>
      </div>

      <div id="selectedFile" class="selected-file">
        <div class="label">Selected File</div>
        <div class="name" id="fileName"></div>
      </div>

      <button class="btn btn-secondary" id="dryRunBtn" onclick="runProcess(true)" disabled>
        Dry Run (Preview Changes)
      </button>

      <button class="btn btn-primary" id="updateBtn" onclick="runProcess(false)" disabled>
        Update File
      </button>
    </div>

    <div id="loading" class="card loading" style="display:none">
      Processing...
    </div>

    <div id="error" class="card error" style="display:none"></div>

    <div id="results" class="card results">
      <h3 id="resultsTitle">Results</h3>
      <div class="stat">
        <span class="stat-label">File</span>
        <span class="stat-value" id="resultFile">-</span>
      </div>
      <div class="stat">
        <span class="stat-label">Capabilities Updated</span>
        <span class="stat-value" id="resultCaps">-</span>
      </div>
      <div class="stat">
        <span class="stat-label">Mappings Added</span>
        <span class="stat-value" id="resultMappings">-</span>
      </div>
      <div id="resultMessage"></div>
      <div id="downloadSection" style="display:none; margin-top: 16px;">
        <button class="btn btn-success" id="downloadBtn" onclick="downloadFile()">
          ⬇️ Download Updated CSV
        </button>
      </div>
      <div id="updatesList" class="updates-list" style="display:none">
        <h4>📝 Solution Capabilities Updated</h4>
        <div class="updates-list-inner" id="updatesListInner"></div>
      </div>
      <div id="notInMaster" class="not-in-master" style="display:none">
        <h4>⚠️ <span id="notInMasterCount">0</span> Solution Capabilities Not Found in Master</h4>
        <ul id="notInMasterList"></ul>
      </div>
    </div>
  </div>

  <script>
    let selectedFileName = null;
    let csvContent = null;
    let updatedContent = null;
    let updatedFileName = null;

    // Drag and drop handlers
    const dropZone = document.getElementById('dropZone');

    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFile(files[0]);
      }
    });

    function handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        handleFile(file);
      }
    }

    function handleFile(file) {
      if (!file.name.endsWith('.csv')) {
        document.getElementById('error').textContent = 'Please select a CSV file.';
        document.getElementById('error').style.display = 'block';
        return;
      }

      selectedFileName = file.name;

      const reader = new FileReader();
      reader.onload = function(e) {
        csvContent = e.target.result;

        document.getElementById('fileName').textContent = selectedFileName;
        document.getElementById('selectedFile').classList.add('show');
        document.getElementById('dryRunBtn').disabled = false;
        document.getElementById('updateBtn').disabled = false;
        document.getElementById('results').classList.remove('show');
        document.getElementById('error').style.display = 'none';
        document.getElementById('downloadSection').style.display = 'none';
      };
      reader.readAsText(file);
    }

    function runProcess(dryRun) {
      if (!csvContent) return;

      document.getElementById('loading').style.display = 'block';
      document.getElementById('error').style.display = 'none';
      document.getElementById('results').classList.remove('show');
      document.getElementById('dryRunBtn').disabled = true;
      document.getElementById('updateBtn').disabled = true;
      document.getElementById('downloadSection').style.display = 'none';

      google.script.run
        .withSuccessHandler(response => {
          document.getElementById('loading').style.display = 'none';
          document.getElementById('dryRunBtn').disabled = false;
          document.getElementById('updateBtn').disabled = false;

          if (response.success) {
            showResults(response.result, response.dryRun);
          } else {
            document.getElementById('error').textContent = response.error;
            document.getElementById('error').style.display = 'block';
          }
        })
        .withFailureHandler(err => {
          document.getElementById('loading').style.display = 'none';
          document.getElementById('dryRunBtn').disabled = false;
          document.getElementById('updateBtn').disabled = false;
          document.getElementById('error').textContent = err.message;
          document.getElementById('error').style.display = 'block';
        })
        .processUploadedFile(csvContent, selectedFileName, dryRun);
    }

    function showResults(stats, dryRun) {
      document.getElementById('resultsTitle').textContent = dryRun ? 'Dry Run Results' : 'Update Complete';
      document.getElementById('resultFile').textContent = stats.fileName;
      document.getElementById('resultCaps').textContent = stats.capabilitiesUpdated;
      document.getElementById('resultMappings').textContent = stats.mappingsAdded;

      const msgDiv = document.getElementById('resultMessage');
      if (stats.capabilitiesUpdated === 0) {
        msgDiv.innerHTML = '<div class="success">All mappings are already in sync!</div>';
        document.getElementById('downloadSection').style.display = 'none';
      } else if (dryRun) {
        msgDiv.innerHTML = '<div class="warning">This was a preview. Click "Update File" to apply changes.</div>';
        document.getElementById('downloadSection').style.display = 'none';
      } else {
        msgDiv.innerHTML = '<div class="success">File updated! Click the button below to download.</div>';
        updatedContent = stats.updatedContent;
        updatedFileName = stats.newFileName;
        document.getElementById('downloadSection').style.display = 'block';
      }

      // Show updates list (capabilities that were edited)
      const updatesListDiv = document.getElementById('updatesList');
      if (stats.updates && stats.updates.length > 0) {
        const listInner = document.getElementById('updatesListInner');
        listInner.innerHTML = stats.updates.map(u =>
          '<div class="update-item">' +
            '<span class="cap-name">' + escapeHtml(u.capability) + '</span>' +
            '<span class="cap-count">+' + u.added + ' mapping' + (u.added !== 1 ? 's' : '') + '</span>' +
          '</div>'
        ).join('');
        updatesListDiv.style.display = 'block';
      } else {
        updatesListDiv.style.display = 'none';
      }

      // Show not in master
      const notInMasterDiv = document.getElementById('notInMaster');
      if (stats.notInMaster && stats.notInMaster.length > 0) {
        document.getElementById('notInMasterCount').textContent = stats.notInMaster.length;
        const list = document.getElementById('notInMasterList');
        list.innerHTML = stats.notInMaster.map(c => '<li>' + escapeHtml(c) + '</li>').join('');
        notInMasterDiv.style.display = 'block';
      } else {
        notInMasterDiv.style.display = 'none';
      }

      document.getElementById('results').classList.add('show');
    }

    function downloadFile() {
      if (!updatedContent || !updatedFileName) return;

      const blob = new Blob([updatedContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = updatedFileName;
      link.click();
      URL.revokeObjectURL(link.href);
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  </script>
</body>
</html>
`;
}
