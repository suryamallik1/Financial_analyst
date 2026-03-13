document.addEventListener('DOMContentLoaded', () => {
    const consoleOutput = document.getElementById('console-output');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const proposalsPanel = document.getElementById('proposals-panel');

    function addLog(agent, message, type = 'tech') {
        const div = document.createElement('div');
        div.className = 'agent-log';
        div.innerHTML = `<span class="agent-name agent-${type}">[${agent}]</span> ${message}`;
        consoleOutput.appendChild(div);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    async function handleAnalysis() {
        const query = userInput.value.trim();
        if (!query) return;

        userInput.value = '';
        addLog('USER', query, 'tech');
        addLog('SYSTEM', 'Spinning up swarm...', 'tech');
        
        // Clear old proposals
        const header = proposalsPanel.firstElementChild;
        proposalsPanel.innerHTML = '';
        proposalsPanel.appendChild(header);

        try {
            const response = await fetch('/api/v1/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_request: query })
            });

            if (!response.ok) throw new Error('API Error');

            const data = await response.json();
            
            // Log agents incrementally (mocking the progression for visual effect)
            addLog('VALUE_ANALYST', 'Scanning SEC 10-K filings for technical moats...', 'value');
            addLog('TECH_ANALYST', 'Calculating RSI and SMA crossover signals...', 'tech');
            addLog('RISK_AGENT', 'Monitoring macro filters and yield curve status...', 'risk');
            addLog('FINANCIAL_ANALYST', 'Running VectorBT backtests on proposed assets...', 'financial');

            if (data.proposals && data.proposals.length > 0) {
                data.proposals.forEach(prop => {
                    renderProposal(prop, data.is_validated);
                });
                addLog('SYSTEM', 'Analysis complete. Final report generated.', 'tech');
            } else {
                addLog('SYSTEM', 'No suitable assets found meeting criteria.', 'risk');
            }

        } catch (err) {
            addLog('ERROR', 'Workflow execution failed. Check server logs.', 'risk');
            console.error(err);
        }
    }

    function renderProposal(prop, isValidated) {
        const card = document.createElement('div');
        card.className = 'proposal-card';
        
        const sharpe = prop.metrics ? prop.metrics.sharpe_ratio : 'N/A';
        const drawdown = prop.metrics ? (prop.metrics.max_drawdown * 100).toFixed(1) : 'N/A';

        card.innerHTML = `
            <div class="token-header">
                <span class="symbol">${prop.symbol}</span>
                <span class="badge ${isValidated ? 'badge-validated' : ''}">${isValidated ? 'VALIDATED' : 'REVIEW'}</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.4;">
                ${prop.rationale.substring(0, 100)}...
            </div>
            <div class="metrics-grid">
                <div class="metric-box">
                    <span class="metric-label">SHARPE</span>
                    <span class="metric-value">${typeof sharpe === 'number' ? sharpe.toFixed(2) : sharpe}</span>
                </div>
                <div class="metric-box">
                    <span class="metric-label">MAX DD</span>
                    <span class="metric-value">${drawdown}%</span>
                </div>
            </div>
        `;
        proposalsPanel.appendChild(card);
    }

    sendBtn.addEventListener('click', handleAnalysis);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAnalysis();
    });
});
