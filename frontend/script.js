document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const error = document.getElementById('error');

    analyzeBtn.addEventListener('click', async function() {
        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file first.');
            return;
        }

        // Show loading state
        loading.style.display = 'block';
        results.style.display = 'none';
        error.style.display = 'none';
        analyzeBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('http://localhost:5001/contracts/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(
                    errorData?.detail || `HTTP error! status: ${response.status}`
                );
            }

            const data = await response.json();
            displayResults(data);

        } catch (err) {
            showError('Error analyzing contract: ' + err.message);
        } finally {
            loading.style.display = 'none';
            analyzeBtn.disabled = false;
        }
    });

    function displayResults(data) {
        // Display filename
        document.getElementById('filename').textContent = `File: ${data.filename}`;

        // Display processing information
        const processingInfo = document.getElementById('processingInfo');
        let ocrText = '';
        if (data.ocr_used === 'primary') {
            ocrText = ' (OCR used for scanned document)';
        } else if (data.ocr_used === 'fallback') {
            ocrText = ' (OCR used as fallback)';
        } else {
            ocrText = ' (Direct text extraction)';
        }

        processingInfo.innerHTML = `
            <strong>Contract ID:</strong> ${data.contract_id} |
            <strong>Processing Method:</strong> ${data.processing_method}${ocrText} |
            <strong>Processing Time:</strong> ${data.processing_time_seconds}s
        `;

        // Display basic statistics
        const stats = data.analysis;
        document.getElementById('stats').innerHTML = `
            <p><strong>Word Count:</strong> ${stats.word_count}</p>
            <p><strong>Sentences:</strong> ${stats.sentences}</p>
        `;

        // Display key terms
        const keyTermsDiv = document.getElementById('keyTerms');
        if (stats.key_terms.length > 0) {
            keyTermsDiv.innerHTML = stats.key_terms.map(term =>
                `<span class="term-tag">${term}</span>`
            ).join('');
        } else {
            keyTermsDiv.innerHTML = '<p>No key rental terms found.</p>';
        }

        // Display named entities
        const entitiesDiv = document.getElementById('entities');
        if (stats.entities.length > 0) {
            entitiesDiv.innerHTML = stats.entities.map(entity =>
                `<span class="entity-tag">${entity.text} (${entity.label})</span>`
            ).join('');
        } else {
            entitiesDiv.innerHTML = '<p>No named entities found.</p>';
        }

        // Display potential issues with rich formatting
        const issuesDiv = document.getElementById('issues');
        const issueCount = document.getElementById('issueCount');
        const noIssues = document.getElementById('noIssues');

        if (stats.issues.length > 0) {
            issueCount.textContent = `Found ${stats.issues.length} potential issue(s):`;
            issueCount.style.display = 'block';
            noIssues.style.display = 'none';

            issuesDiv.innerHTML = stats.issues.map((issue, index) => {
                // Determine risk level badge
                const riskLevel = (issue.risk_level || 'unknown').toLowerCase();
                const riskLabel = riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1);
                const riskBadge = `<span class="risk-badge risk-${riskLevel}">${riskLabel}</span>`;

                // Build issue card content
                let cardHtml = `
                    <div class="issue-item">
                        <div class="issue-header">
                            ${riskBadge}
                            <span class="issue-number">Issue #${index + 1}</span>
                        </div>
                        <div class="issue-description">${escapeHtml(issue.description)}</div>
                `;

                // Legal basis
                if (issue.legal_basis) {
                    cardHtml += `
                        <div class="issue-detail">
                            <span class="detail-label">Legal Basis:</span>
                            <span class="legal-basis">${escapeHtml(issue.legal_basis)}</span>
                        </div>
                    `;
                }

                // Clause snippet (if available)
                if (issue.clause_snippet) {
                    cardHtml += `
                        <div class="issue-detail">
                            <span class="detail-label">Clause:</span>
                            <span class="clause-snippet">${escapeHtml(issue.clause_snippet)}</span>
                        </div>
                    `;
                }

                // Similarity score (if available)
                if (issue.similarity != null) {
                    const simPercent = (issue.similarity * 100).toFixed(0);
                    cardHtml += `
                        <div class="issue-detail">
                            <span class="detail-label">Match Confidence:</span>
                            <span class="similarity">${simPercent}%</span>
                        </div>
                    `;
                }

                cardHtml += `</div>`;
                return cardHtml;
            }).join('');
        } else {
            issueCount.style.display = 'none';
            noIssues.style.display = 'block';
            issuesDiv.innerHTML = '';
        }

        results.style.display = 'block';
    }

    function showError(message) {
        error.textContent = message;
        error.style.display = 'block';
        results.style.display = 'none';
        loading.style.display = 'none';
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});