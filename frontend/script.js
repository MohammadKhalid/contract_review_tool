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

            const response = await fetch('http://localhost:5001/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
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

        // Display potential issues
        const issuesDiv = document.getElementById('issues');
        if (stats.issues.length > 0) {
            issuesDiv.innerHTML = stats.issues.map(issue =>
                `<div class="issue-item">${issue}</div>`
            ).join('');
        } else {
            issuesDiv.innerHTML = '<p>No potential issues detected.</p>';
        }

        results.style.display = 'block';
    }

    function showError(message) {
        error.textContent = message;
        error.style.display = 'block';
        results.style.display = 'none';
        loading.style.display = 'none';
    }
});