document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('finance-form');
    const input = document.getElementById('question-input');
    const chipBtns = document.querySelectorAll('.chip-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultsPanel = document.getElementById('results-panel');
    const finalAnswerContent = document.getElementById('final-answer-content');
    const groundingBadge = document.getElementById('grounding-badge');
    const groundingIcon = document.getElementById('grounding-icon');
    const groundingText = document.getElementById('grounding-text');
    const toolsList = document.getElementById('tools-list');
    const toolsCount = document.getElementById('tools-count');
    const metricIterations = document.getElementById('metric-iterations');
    const metricObsCount = document.getElementById('metric-obs-count');
    const observationsContainer = document.getElementById('observations-container');
    const auditSummaryText = document.getElementById('audit-summary-text');
    const claimsTableBody = document.getElementById('claims-table-body');

    // Handle Preset Chips
    chipBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const questionText = btn.getAttribute('data-question');
            input.value = questionText;
            form.dispatchEvent(new Event('submit'));
        });
    });

    // Form Submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = input.value.trim();
        if (!question) return;

        // UI Reset & Show Loading
        resultsPanel.classList.add('hidden');
        loadingSpinner.classList.remove('hidden');

        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to fetch agent response');
            }

            const data = await response.json();
            renderResults(data);
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    });

    function renderResults(data) {
        // 1. Final Answer & Grounding Status
        finalAnswerContent.textContent = data.answer;
        
        if (data.grounding_status === 'VERIFIED') {
            groundingBadge.className = 'badge verified';
            groundingIcon.textContent = '✓';
            groundingText.textContent = 'VERIFIED GROUNDING';
        } else {
            groundingBadge.className = 'badge unsupported';
            groundingIcon.textContent = '⚠';
            groundingText.textContent = 'UNSUPPORTED CLAIMS DETECTED';
        }

        // 2. Tools Used Timeline
        toolsList.innerHTML = '';
        toolsCount.textContent = data.tools_used ? data.tools_used.length : 0;
        
        if (data.tools_used && data.tools_used.length > 0) {
            data.tools_used.forEach((tname, idx) => {
                const li = document.createElement('li');
                li.innerHTML = `<span>Step ${idx + 1}:</span> <strong>${tname}</strong>`;
                toolsList.appendChild(li);
            });
        } else {
            toolsList.innerHTML = '<li>No tools required</li>';
        }

        // 3. Metrics
        metricIterations.textContent = data.iterations || 1;
        metricObsCount.textContent = data.observations ? data.observations.length : 0;

        // 4. Observations JSON Cards
        observationsContainer.innerHTML = '';
        if (data.observations && data.observations.length > 0) {
            data.observations.forEach((obs) => {
                const div = document.createElement('div');
                div.className = 'obs-card';
                div.innerHTML = `
                    <div class="obs-title">Iteration ${obs.iteration}: Executed \`${obs.tool_name}\`</div>
                    <div><strong>Arguments:</strong> ${JSON.stringify(obs.arguments, null, 2)}</div>
                    <div><strong>Result:</strong> ${JSON.stringify(obs.result, null, 2)}</div>
                `;
                observationsContainer.appendChild(div);
            });
        } else {
            observationsContainer.innerHTML = '<div>No observations recorded.</div>';
        }

        // 5. Reflection Audit Details
        const refl = data.reflection || {};
        auditSummaryText.textContent = refl.summary || 'Grounding audit complete.';

        claimsTableBody.innerHTML = '';
        if (refl.claims_checked && refl.claims_checked.length > 0) {
            refl.claims_checked.forEach(c => {
                const tr = document.createElement('tr');
                const isPass = c.is_verified;
                tr.innerHTML = `
                    <td><code>${c.claim_type}</code></td>
                    <td>${c.claimed_value}</td>
                    <td class="${isPass ? 'status-pass' : 'status-fail'}">${isPass ? '✓ PASSED' : '✗ REJECTED'}</td>
                    <td>${c.details}</td>
                `;
                claimsTableBody.appendChild(tr);
            });
        } else {
            claimsTableBody.innerHTML = '<tr><td colspan="4">No claims checked.</td></tr>';
        }

        // Reveal Results Panel
        resultsPanel.classList.remove('hidden');
    }
});
