// Global variables
let tools = [];
let choices = {};
let searchTerm = '';

// Debug function for editor alignment
function debugEditorAlignment() {
    const editor = document.getElementById('yaml-editor');
    const highlight = document.getElementById('yaml-highlight');
    
    console.log('=== EDITOR DEBUG ===');
    console.log('Editor computed styles:', window.getComputedStyle(editor));
    console.log('Highlight computed styles:', window.getComputedStyle(highlight));
    
    const editorStyles = window.getComputedStyle(editor);
    const highlightStyles = window.getComputedStyle(highlight);
    
    console.log('Font comparison:');
    console.log('  Editor font-family:', editorStyles.fontFamily);
    console.log('  Highlight font-family:', highlightStyles.fontFamily);
    console.log('  Editor font-size:', editorStyles.fontSize);
    console.log('  Highlight font-size:', highlightStyles.fontSize);
    console.log('  Editor line-height:', editorStyles.lineHeight);
    console.log('  Highlight line-height:', highlightStyles.lineHeight);
    console.log('  Editor letter-spacing:', editorStyles.letterSpacing);
    console.log('  Highlight letter-spacing:', highlightStyles.letterSpacing);
    
    console.log('Box model comparison:');
    console.log('  Editor padding:', editorStyles.padding);
    console.log('  Highlight padding:', highlightStyles.padding);
    console.log('  Editor border:', editorStyles.border);
    console.log('  Highlight border:', highlightStyles.border);
    console.log('  Editor margin:', editorStyles.margin);
    console.log('  Highlight margin:', highlightStyles.margin);
}

// Add to window for console access
window.debugEditorAlignment = debugEditorAlignment;

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    loadTools();
}

function setupEventListeners() {
    // Navigation between review, compare and edit modes
    document.getElementById('review-mode').addEventListener('click', switchToReviewMode);
    document.getElementById('compare-mode').addEventListener('click', switchToCompareMode);
    document.getElementById('edit-mode').addEventListener('click', switchToEditMode);
    document.getElementById('about-mode').addEventListener('click', switchToAboutMode);

    // Preview configuration
    document.getElementById('preview-config').addEventListener('click', previewConfiguration);

    // Back to review
    document.getElementById('back-to-review').addEventListener('click', backToReview);

    // Save configuration
    document.getElementById('save-config').addEventListener('click', saveConfiguration);

    // File upload handling
    document.getElementById('config-file').addEventListener('change', handleFileUpload);

    // Run comparison
    document.getElementById('run-compare').addEventListener('click', runComparison);

    // Edit mode functionality
    document.getElementById('load-template').addEventListener('click', loadTemplate);
    document.getElementById('load-from-file').addEventListener('click', () => {
        document.getElementById('yaml-file-input').click();
    });
    document.getElementById('yaml-file-input').addEventListener('change', handleYamlFileUpload);
    document.getElementById('validate-yaml').addEventListener('click', validateYaml);
    document.getElementById('save-manual-config').addEventListener('click', saveManualConfig);
    
    // Reset functionality
    document.getElementById('reset-review').addEventListener('click', resetReview);
    document.getElementById('reset-compare').addEventListener('click', resetCompare);
    document.getElementById('reset-edit').addEventListener('click', resetEdit);
    
    // Allow all unset functionality
    document.getElementById('allow-all-unset').addEventListener('click', allowAllUnset);
    
    // Sort functionality
    document.getElementById('sort-select').addEventListener('change', handleSortChange);
    
    // Search functionality
    document.getElementById('search-input').addEventListener('input', handleSearchChange);
    document.getElementById('clear-search').addEventListener('click', clearSearch);
    
    // YAML editor - no syntax highlighting needed
    // document.getElementById('yaml-editor').addEventListener('input', updateYamlHighlighting);
    // document.getElementById('yaml-editor').addEventListener('scroll', syncHighlightScroll);
}

function switchToReviewMode() {
    // Remove active from all nav items first
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    
    // Switch to review mode
    document.getElementById('review-mode').classList.add('active');
    
    // Update page title
    document.getElementById('page-title').textContent = 'Review Tools';
    document.getElementById('page-subtitle').textContent = 'Review MCP server tools for your MCP client';
    
    hideAllSections();
    document.getElementById('content').style.display = 'block';
}

function switchToCompareMode() {
    // Remove active from all nav items first
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    
    // Switch to compare mode
    document.getElementById('compare-mode').classList.add('active');
    
    // Update page title
    document.getElementById('page-title').textContent = 'Compare Configuration';
    document.getElementById('page-subtitle').textContent = 'Compare existing configuration files against the server';
    
    hideAllSections();
    document.getElementById('compare').style.display = 'block';
    
    // Load server info for compare mode
    loadServerInfo();
}

function switchToEditMode() {
    // Remove active from all nav items first
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    
    // Switch to edit mode
    document.getElementById('edit-mode').classList.add('active');
    
    // Update page title
    document.getElementById('page-title').textContent = 'Edit Configuration';
    document.getElementById('page-subtitle').textContent = 'Manually create or edit YAML configuration files';
    
    hideAllSections();
    document.getElementById('edit').style.display = 'block';
    
    // No syntax highlighting needed
}

function switchToAboutMode() {
    // Remove active from all nav items first
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    
    // Switch to about mode
    document.getElementById('about-mode').classList.add('active');
    
    // Update page title
    document.getElementById('page-title').textContent = 'About RailLock';
    document.getElementById('page-subtitle').textContent = 'Information about the RailLock project';
    
    hideAllSections();
    document.getElementById('about').style.display = 'block';
}

function hideAllSections() {
    const sections = ['loading', 'content', 'preview', 'compare', 'edit', 'about', 'success'];
    sections.forEach(section => {
        document.getElementById(section).style.display = 'none';
    });
}

async function loadTools() {
    try {
        const response = await fetch('/api/tools');
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        tools = data.tools;
        document.getElementById('server-name').textContent = data.server_name;
        document.getElementById('server-type').textContent = data.server_type;
        document.getElementById('tool-count').textContent = tools.length;
        
        renderTools();
        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').style.display = 'block';
        updateProgress();
    } catch (error) {
        showError('Error Loading Tools', error.message);
    }
}

function sortTools(sortBy) {
    let filteredTools = [...tools]; // Create a copy to avoid mutating original
    
    // Apply search filter first
    if (searchTerm.trim()) {
        const searchLower = searchTerm.toLowerCase().trim();
        
        // Parse search syntax
        let searchText, searchTarget;
        
        if (searchLower.startsWith('title:')) {
            searchText = searchLower.substring(6).trim();
            searchTarget = 'title';
        } else if (searchLower.startsWith('desc:')) {
            searchText = searchLower.substring(5).trim();
            searchTarget = 'desc';
        } else {
            // Default: search title/name only
            searchText = searchLower;
            searchTarget = 'title';
        }
        
        // Apply the filter based on search target
        if (searchText) {
            filteredTools = filteredTools.filter(tool => {
                switch (searchTarget) {
                    case 'title':
                        return tool.name.toLowerCase().includes(searchText);
                    case 'desc':
                        return tool.description.toLowerCase().includes(searchText);
                    default:
                        return tool.name.toLowerCase().includes(searchText);
                }
            });
        }
    }
    
    // Then apply sorting
    switch (sortBy) {
        case 'name':
            filteredTools.sort((a, b) => a.name.localeCompare(b.name));
            break;
        case 'description-length':
            filteredTools.sort((a, b) => b.description.length - a.description.length);
            break;
        default:
            // Default to name sorting
            filteredTools.sort((a, b) => a.name.localeCompare(b.name));
    }
    
    return filteredTools;
}

function handleSortChange() {
    const sortBy = document.getElementById('sort-select').value;
    renderTools(sortBy);
}

function handleSearchChange() {
    const searchInput = document.getElementById('search-input');
    const clearButton = document.getElementById('clear-search');
    
    searchTerm = searchInput.value;
    
    // Update clear button state
    clearButton.disabled = !searchTerm.trim();
    
    // Re-render tools with current sort and search
    const sortBy = document.getElementById('sort-select').value;
    renderTools(sortBy);
}

function clearSearch() {
    const searchInput = document.getElementById('search-input');
    const clearButton = document.getElementById('clear-search');
    
    searchInput.value = '';
    searchTerm = '';
    clearButton.disabled = true;
    
    // Re-render tools with current sort but no search
    const sortBy = document.getElementById('sort-select').value;
    renderTools(sortBy);
}

function updateYamlHighlighting() {
    // Simplified - no syntax highlighting overlay
}

function syncHighlightScroll() {
    // No longer needed - no overlay highlighting
}

// No longer needed - syntax highlighting is always visible

function renderTools(sortBy = 'name') {
    const container = document.getElementById('tools-container');
    container.innerHTML = '';

    const filteredTools = sortTools(sortBy);

    // Show message if no tools match search
    if (filteredTools.length === 0 && searchTerm.trim()) {
        container.innerHTML = `
            <div class="no-results">
                <p>No tools found matching "${escapeHtml(searchTerm)}"</p>
                <p>Try adjusting your search terms or <button onclick="clearSearch()" class="btn btn-secondary">clear search</button></p>
            </div>
        `;
        updateProgress();
        return;
    }

    filteredTools.forEach((tool, index) => {
        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-card';
        // SECURITY: escapeHtml() prevents XSS by converting any HTML/script tags 
        // in tool names and descriptions to safe text entities
        toolDiv.innerHTML = `
            <div class="tool-name">${escapeHtml(tool.name)}</div>
            <div class="tool-description">${escapeHtml(tool.description)}</div>
            <div class="button-group">
                <button class="btn btn-allow" onclick="setChoice('${escapeHtml(tool.name)}', 'allow')">
                    <i data-lucide="check" class="btn-icon"></i> Allow
                </button>
                <button class="btn btn-deny" onclick="setChoice('${escapeHtml(tool.name)}', 'deny')">
                    <i data-lucide="x" class="btn-icon"></i> Deny
                </button>
                <button class="btn btn-malicious" onclick="setChoice('${escapeHtml(tool.name)}', 'malicious')">
                    <i data-lucide="alert-triangle" class="btn-icon"></i> Malicious
                </button>
                <button class="btn btn-ignore" onclick="setChoice('${escapeHtml(tool.name)}', 'ignore')">
                    <i data-lucide="minus" class="btn-icon"></i> Ignore
                </button>
            </div>
        `;
        container.appendChild(toolDiv);
        
        // Restore existing selection if it exists
        const existingChoice = choices[tool.name];
        if (existingChoice) {
            // Apply the appropriate button active state and card background
            const buttons = toolDiv.querySelectorAll('.btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            
            // Find and activate the correct button
            let activeButton;
            switch (existingChoice) {
                case 'allow':
                    activeButton = toolDiv.querySelector('.btn-allow');
                    toolDiv.classList.add('allowed');
                    break;
                case 'deny':
                    activeButton = toolDiv.querySelector('.btn-deny');
                    toolDiv.classList.add('denied');
                    break;
                case 'malicious':
                    activeButton = toolDiv.querySelector('.btn-malicious');
                    toolDiv.classList.add('malicious');
                    break;
                case 'ignore':
                    activeButton = toolDiv.querySelector('.btn-ignore');
                    toolDiv.classList.add('ignored');
                    break;
            }
            
            if (activeButton) {
                activeButton.classList.add('active');
            }
        }
    });
    
    // Reinitialize Lucide icons for new content
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function setChoice(toolName, choice) {
    // Check if this choice is already selected - if so, unselect it
    if (choices[toolName] === choice) {
        delete choices[toolName];
        
        // Update button states - remove all active states
        const toolCard = event.target.closest('.tool-card');
        const buttons = toolCard.querySelectorAll('.btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        
        // Remove tool card background
        toolCard.classList.remove('allowed', 'denied', 'malicious', 'ignored');
    } else {
        // Set new choice
        choices[toolName] = choice;
        
        // Update button states
        const toolCard = event.target.closest('.tool-card');
        const buttons = toolCard.querySelectorAll('.btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        
        // Update tool card background based on choice
        toolCard.classList.remove('allowed', 'denied', 'malicious', 'ignored');
        if (choice === 'allow') {
            toolCard.classList.add('allowed');
        } else if (choice === 'deny') {
            toolCard.classList.add('denied');
        } else if (choice === 'malicious') {
            toolCard.classList.add('malicious');
        } else if (choice === 'ignore') {
            toolCard.classList.add('ignored');
        }
    }
    
    updateProgress();
}

function updateProgress() {
    const reviewed = Object.keys(choices).length;
    const total = tools.length;
    
    // Defensive check - make sure elements exist
    const sortSelect = document.getElementById('sort-select');
    const allowAllUnsetButton = document.getElementById('allow-all-unset');
    const progressText = document.getElementById('progress-text');
    const previewButton = document.getElementById('preview-config');
    
    if (!sortSelect || !allowAllUnsetButton || !progressText || !previewButton) {
        console.log('[DEBUG] updateProgress: Some elements not ready yet');
        return;
    }
    
    // Show filtered results if search is active
    const filteredTools = sortTools(sortSelect.value);
    const filteredCount = filteredTools.length;
    
    console.log(`[DEBUG] updateProgress: reviewed=${reviewed}, total=${total}, filtered=${filteredCount}, searchTerm="${searchTerm}"`);
    
    let progressTextValue;
    if (searchTerm.trim() && filteredCount < total) {
        progressTextValue = `${reviewed} of ${total} tools reviewed (showing ${filteredCount} filtered)`;
    } else {
        progressTextValue = `${reviewed} of ${total} tools reviewed`;
    }
    
    progressText.textContent = progressTextValue;
    
    if (reviewed === total && total > 0) {
        previewButton.disabled = false;
        previewButton.innerHTML = '<i data-lucide="eye" class="btn-icon"></i> Preview';
    } else {
        previewButton.disabled = true;
        previewButton.innerHTML = `<i data-lucide="eye" class="btn-icon"></i> Preview`;
    }
    
    // Update Allow All Unset button state - only count unset tools that are currently visible
    const visibleUnsetTools = filteredTools.filter(tool => !(tool.name in choices));
    const unsetCount = visibleUnsetTools.length;
    
    console.log(`[DEBUG] updateProgress: unsetCount=${unsetCount}, visibleUnsetTools=`, visibleUnsetTools.map(t => t.name));
    
    if (unsetCount > 0) {
        allowAllUnsetButton.disabled = false;
        if (searchTerm.trim() && filteredCount < total) {
            allowAllUnsetButton.innerHTML = `<i data-lucide="check-square" class="btn-icon"></i> Allow Rest (${unsetCount} visible)`;
        } else {
            allowAllUnsetButton.innerHTML = `<i data-lucide="check-square" class="btn-icon"></i> Allow Rest (${unsetCount})`;
        }
    } else {
        allowAllUnsetButton.disabled = true;
        allowAllUnsetButton.innerHTML = '<i data-lucide="check-square" class="btn-icon"></i> Allow Rest';
    }
    
    // Reinitialize Lucide icons for updated button
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

async function previewConfiguration() {
    const button = document.getElementById('preview-config');
    button.disabled = true;
    button.innerHTML = '<i data-lucide="loader-2" class="btn-icon"></i> Loading...';
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    try {
        const response = await fetch('/api/preview-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ choices })
        });

        const result = await response.json();
        
        if (result.success) {
            // Update summary stats
            document.getElementById('allowed-count').textContent = result.summary.allowed;
            document.getElementById('denied-count').textContent = result.summary.denied;
            document.getElementById('malicious-count').textContent = result.summary.malicious;
            document.getElementById('ignored-count').textContent = result.summary.ignored || 0;
            
            // Show YAML preview with Prism.js syntax highlighting
            const yamlElement = document.getElementById('config-yaml');
            yamlElement.textContent = result.yaml_content;
            Prism.highlightElement(yamlElement);
            
            // Switch to preview view
            hideAllSections();
            document.getElementById('preview').style.display = 'block';
        } else {
            throw new Error(result.error || 'Failed to generate preview');
        }
    } catch (error) {
        alert('Error generating preview: ' + error.message);
    }
    
    button.disabled = false;
    button.innerHTML = '<i data-lucide="eye" class="btn-icon"></i> Preview';
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function backToReview() {
    hideAllSections();
    document.getElementById('content').style.display = 'block';
}

async function saveConfiguration() {
    const button = document.getElementById('save-config');
    const filename = document.getElementById('config-filename').value.trim();
    
    if (!filename) {
        alert('Please enter a filename');
        return;
    }
    
    button.disabled = true;
    button.innerHTML = '<i data-lucide="loader-2" class="btn-icon"></i> Saving...';
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    try {
        const response = await fetch('/api/save-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                choices: choices,
                filename: filename
            })
        });

        const result = await response.json();
        
        if (result.success) {
            document.getElementById('config-path').textContent = result.config_path;
            hideAllSections();
            document.getElementById('success').style.display = 'block';
        } else {
            throw new Error(result.error || 'Failed to save configuration');
        }
    } catch (error) {
        alert('Error saving configuration: ' + error.message);
    } finally {
        // Always reset button state
        button.disabled = false;
        button.innerHTML = '<i data-lucide="save" class="btn-icon"></i> Save';
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

function handleFileUpload(e) {
    const file = e.target.files[0];
    const fileName = document.getElementById('file-name');
    const compareButton = document.getElementById('run-compare');
    const resetButton = document.getElementById('reset-compare');
    
    if (file) {
        fileName.textContent = file.name;
        compareButton.disabled = false;
        resetButton.disabled = false;
    } else {
        fileName.textContent = '';
        compareButton.disabled = true;
        resetButton.disabled = true;
    }
}

async function runComparison() {
    const fileInput = document.getElementById('config-file');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a config file first');
        return;
    }
    
    const button = document.getElementById('run-compare');
    button.disabled = true;
    button.textContent = 'Comparing...';
    
    try {
        const fileContent = await file.text();
        
        const response = await fetch('/api/compare-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                config_content: fileContent
            })
        });

        const result = await response.json();
        
        if (result.success) {
            displayComparisonResults(result);
            document.getElementById('compare-results').style.display = 'block';
        } else {
            throw new Error(result.error || 'Failed to compare configuration');
        }
    } catch (error) {
        alert('Error comparing configuration: ' + error.message);
    }
    
    button.disabled = false;
    button.textContent = 'Compare';
}

async function loadServerInfo() {
    try {
        const response = await fetch('/api/tools');
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        document.getElementById('compare-server-name').textContent = data.server_name;
        document.getElementById('compare-server-type').textContent = data.server_type;
    } catch (error) {
        console.error('Error loading server info:', error);
    }
}

async function loadServerInfoForEdit() {
    try {
        const response = await fetch('/api/tools');
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        document.getElementById('edit-server-name').textContent = data.server_name;
        document.getElementById('edit-server-type').textContent = data.server_type;
    } catch (error) {
        console.error('Error loading server info:', error);
    }
}

function loadTemplate() {
    const template = `config_version: 1
server:
  name: YOUR_SERVER_NAME
  type: sse  # or stdio, http
allowed_tools:
  # Add allowed tools here
  # tool_name:
  #   description: "Tool description"
  #   server: YOUR_SERVER_NAME
  #   checksum: "tool_checksum"
malicious_tools:
  # Add malicious tools here
denied_tools:
  # Add denied tools here
`;
    document.getElementById('yaml-editor').value = template;
    updateYamlHighlighting();
    showValidationMessage('Template loaded successfully!', 'success');
}

async function handleYamlFileUpload(e) {
    const file = e.target.files[0];
    if (file) {
        try {
            const content = await file.text();
            document.getElementById('yaml-editor').value = content;
            document.getElementById('edit-config-filename').value = file.name;
            updateYamlHighlighting();
            showValidationMessage(`File "${file.name}" loaded successfully!`, 'success');
        } catch (error) {
            showValidationMessage(`Error loading file: ${error.message}`, 'error');
        }
    }
}

function validateYaml() {
    const yamlContent = document.getElementById('yaml-editor').value.trim();
    
    if (!yamlContent) {
        showValidationMessage('Please enter some YAML content to validate.', 'error');
        return false;
    }
    
    try {
        // Parse YAML using js-yaml library
        const parsed = jsyaml.load(yamlContent);
        
        if (!parsed || typeof parsed !== 'object') {
            showValidationMessage('Invalid YAML: Document must be an object.', 'error');
            return false;
        }
        
        // Validate RailLock configuration structure
        const errors = [];
        const warnings = [];
        
        // Check required fields
        if (!parsed.config_version) {
            errors.push('Missing required field: config_version');
        } else if (typeof parsed.config_version !== 'number') {
            errors.push('config_version must be a number');
        }
        
        if (!parsed.server) {
            errors.push('Missing required field: server');
        } else if (typeof parsed.server !== 'object') {
            errors.push('server must be an object');
        } else {
            if (!parsed.server.name) {
                errors.push('Missing required field: server.name');
            }
            if (!parsed.server.type) {
                errors.push('Missing required field: server.type');
            } else if (!['sse', 'stdio', 'http'].includes(parsed.server.type)) {
                warnings.push('server.type should be one of: sse, stdio, http');
            }
        }
        
        // Check optional sections exist and are objects
        const sections = ['allowed_tools', 'malicious_tools', 'denied_tools'];
        sections.forEach(section => {
            if (parsed[section] && typeof parsed[section] !== 'object') {
                errors.push(`${section} must be an object`);
            }
        });
        
        // Validate tool entries
        sections.forEach(section => {
            if (parsed[section]) {
                Object.entries(parsed[section]).forEach(([toolName, toolData]) => {
                    if (typeof toolData !== 'object') {
                        errors.push(`${section}.${toolName} must be an object`);
                    } else {
                        if (!toolData.description) {
                            warnings.push(`${section}.${toolName} missing description`);
                        }
                        if (!toolData.server) {
                            warnings.push(`${section}.${toolName} missing server`);
                        }
                        if (!toolData.checksum) {
                            warnings.push(`${section}.${toolName} missing checksum`);
                        }
                    }
                });
            }
        });
        
        // Display results
        if (errors.length > 0) {
            showValidationMessage(`❌ Validation failed:\n${errors.join('\n')}`, 'error');
            return false;
        } else if (warnings.length > 0) {
            showValidationMessage(`⚠️ YAML is valid but has warnings:\n${warnings.join('\n')}`, 'error');
            return true; // Valid but with warnings
        } else {
            showValidationMessage('✅ YAML is valid and well-formed!', 'success');
            return true;
        }
        
    } catch (error) {
        showValidationMessage(`❌ Invalid YAML syntax: ${error.message}`, 'error');
        return false;
    }
}

async function saveManualConfig() {
    const yamlContent = document.getElementById('yaml-editor').value.trim();
    const filename = document.getElementById('edit-config-filename').value.trim();
    
    if (!yamlContent) {
        showValidationMessage('Please enter YAML content before saving.', 'error');
        return;
    }
    
    if (!filename) {
        showValidationMessage('Please enter a filename.', 'error');
        return;
    }
    
    // Validate before saving
    if (!validateYaml()) {
        return;
    }
    
    const button = document.getElementById('save-manual-config');
    button.disabled = true;
    button.innerHTML = '<i data-lucide="loader-2" class="btn-icon"></i> Saving...';
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    try {
        const response = await fetch('/api/save-manual-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                yaml_content: yamlContent,
                filename: filename
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('config-path').textContent = result.config_path;
            hideAllSections();
            document.getElementById('success').style.display = 'block';
        } else {
            throw new Error(result.error || 'Failed to save configuration');
        }
    } catch (error) {
        showValidationMessage(`Error saving configuration: ${error.message}`, 'error');
    } finally {
        // Always reset button state
        button.disabled = false;
        button.innerHTML = '<i data-lucide="save" class="btn-icon"></i> Save';
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

function showValidationMessage(message, type) {
    const messageEl = document.getElementById('validation-message');
    // SECURITY: Escape HTML in validation messages to prevent XSS
    messageEl.textContent = message; // textContent is safe - it doesn't interpret HTML
    messageEl.className = `validation-message ${type}`;
    messageEl.style.display = 'block';
    
    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(() => {
            messageEl.style.display = 'none';
        }, 3000);
    }
}

function displayComparisonResults(result) {
    // Update summary
    document.getElementById('server-tools-count').textContent = result.summary.server_tools;
    document.getElementById('allowed-tools-count').textContent = result.summary.allowed_tools;
    document.getElementById('malicious-tools-count').textContent = result.summary.malicious_tools;
    document.getElementById('denied-tools-count').textContent = result.summary.denied_tools;
    document.getElementById('checksum-mismatches-count').textContent = result.summary.checksum_mismatches;
    
    // Clear and populate table
    const tbody = document.getElementById('comparison-tbody');
    tbody.innerHTML = '';
    
    result.comparison_data.forEach(row => {
        const tr = document.createElement('tr');
        
        // Highlight rows with checksum mismatches
        const checksumClass = row.checksum_match ? 'check' : 'cross';
        const checksumIcon = row.checksum_match ? '✔' : '✘';
        
        // Add warning class for rows with checksum mismatches
        if (!row.checksum_match && row.on_server) {
            tr.classList.add('checksum-mismatch-warning');
        }
        
        tr.innerHTML = `
            <td><strong>${escapeHtml(row.tool)}</strong></td>
            <td><span class="status-icon ${row.on_server ? 'check' : 'cross'}">${row.on_server ? '✔' : '✘'}</span></td>
            <td><span class="status-icon ${row.allowed ? 'check' : 'cross'}">${row.allowed ? '✔' : '✘'}</span></td>
            <td><span class="status-icon ${checksumClass}">${checksumIcon}</span></td>
            <td><span class="tool-type ${row.type.toLowerCase().replace(/[^a-z0-9]/g, '-')}">${escapeHtml(row.type)}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function showError(title, message) {
    document.getElementById('loading').innerHTML = `
        <div class="error-message">
            <h3>❌ ${escapeHtml(title)}</h3>
            <p>${escapeHtml(message)}</p>
            <button onclick="window.location.reload()" class="btn btn-primary">
                🔄 Retry
            </button>
        </div>
    `;
}

/**
 * Escape HTML to prevent XSS attacks.
 * This function converts potentially dangerous characters to HTML entities,
 * ensuring that any script tags or other HTML in tool descriptions are 
 * displayed as text rather than executed by the browser.
 * 
 * Example: "<script>alert('xss')</script>" becomes "&lt;script&gt;alert('xss')&lt;/script&gt;"
 */
function escapeHtml(text) {
    if (typeof text !== 'string') {
        return text;
    }
    
    const map = {
        '&': '&amp;',   // Must be first to avoid double-encoding
        '<': '&lt;',    // Prevents <script> tags
        '>': '&gt;',    // Prevents <script> tags
        '"': '&quot;',  // Prevents attribute injection
        "'": '&#039;',  // Prevents attribute injection
        '/': '&#x2F;',  // Additional protection for closing tags
        '`': '&#x60;',  // Prevents template literal injection
        '=': '&#x3D;'   // Prevents attribute injection
    };
    
    return text.replace(/[&<>"'`=\/]/g, function(m) { 
        return map[m]; 
    });
}

// Reset Functions
function resetReview() {
    choices = {};
    
    // Clear all active states and backgrounds
    const toolCards = document.querySelectorAll('.tool-card');
    toolCards.forEach(card => {
        const buttons = card.querySelectorAll('.btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        card.classList.remove('allowed', 'denied', 'malicious', 'ignored');
    });
    
    // Reset sort dropdown to default
    document.getElementById('sort-select').value = 'name';
    
    // Reset search
    document.getElementById('search-input').value = '';
    searchTerm = '';
    document.getElementById('clear-search').disabled = true;
    
    // Re-render tools with default sort and no search
    renderTools('name');
    
    updateProgress();
    console.log('Review reset');
}

function resetCompare() {
    // Clear file input
    const fileInput = document.getElementById('config-file');
    fileInput.value = '';
    
    // Clear file name display
    document.getElementById('file-name').textContent = '';
    
    // Disable compare and reset buttons
    document.getElementById('run-compare').disabled = true;
    document.getElementById('reset-compare').disabled = true;
    
    // Hide comparison results
    document.getElementById('compare-results').style.display = 'none';
    
    // Clear comparison table
    const tbody = document.getElementById('comparison-tbody');
    if (tbody) {
        tbody.innerHTML = '';
    }
    
    // Reset summary counts
    const summaryElements = ['server-tools-count', 'allowed-tools-count', 'malicious-tools-count', 'denied-tools-count', 'checksum-mismatches-count'];
    summaryElements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = '0';
        }
    });
}

function resetEdit() {
    // Clear YAML editor
    document.getElementById('yaml-editor').value = '';
    updateYamlHighlighting();
    
    // Reset filename to default
    document.getElementById('edit-config-filename').value = 'raillock_config.yaml';
    
    // Hide validation message
    const validationMessage = document.getElementById('validation-message');
    if (validationMessage) {
        validationMessage.style.display = 'none';
    }
    
    // Clear file input
    const yamlFileInput = document.getElementById('yaml-file-input');
    if (yamlFileInput) {
        yamlFileInput.value = '';
    }
}

// Make functions globally available for onclick handlers
window.setChoice = setChoice; 

function allowAllUnset() {
    // Find all tools that haven't been explicitly reviewed AND are currently visible
    const sortBy = document.getElementById('sort-select').value;
    const filteredTools = sortTools(sortBy);
    const unsetTools = filteredTools.filter(tool => !(tool.name in choices));
    
    if (unsetTools.length === 0) {
        if (searchTerm.trim()) {
            alert('All visible tools have already been reviewed.');
        } else {
            alert('All tools have already been reviewed.');
        }
        return;
    }
    
    // Confirm action with user
    let confirmMessage;
    if (searchTerm.trim() && filteredTools.length < tools.length) {
        confirmMessage = `This will mark ${unsetTools.length} visible unreviewed tool(s) as "Allow". Are you sure?`;
    } else {
        confirmMessage = `This will mark ${unsetTools.length} unreviewed tool(s) as "Allow". Are you sure?`;
    }
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // Mark all unset tools as allow
    unsetTools.forEach(tool => {
        choices[tool.name] = 'allow';
        
        // Find the UI element for this tool by name (not index, since sorting may change order)
        const toolCards = document.querySelectorAll('.tool-card');
        toolCards.forEach(toolCard => {
            const toolNameElement = toolCard.querySelector('.tool-name');
            if (toolNameElement && toolNameElement.textContent === tool.name) {
                const buttons = toolCard.querySelectorAll('.btn');
                
                // Clear all active states
                buttons.forEach(btn => btn.classList.remove('active'));
                
                // Set allow button as active
                const allowButton = toolCard.querySelector('.btn-allow');
                if (allowButton) {
                    allowButton.classList.add('active');
                }
                
                // Update tool card background
                toolCard.classList.remove('denied', 'malicious', 'ignored');
                toolCard.classList.add('allowed');
            }
        });
    });
    
    // Update progress tracking
    updateProgress();
    
    // Show success message
    if (searchTerm.trim() && filteredTools.length < tools.length) {
        alert(`Successfully marked ${unsetTools.length} visible tool(s) as "Allow".`);
    } else {
        alert(`Successfully marked ${unsetTools.length} tool(s) as "Allow".`);
    }
} 