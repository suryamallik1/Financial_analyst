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

    function updateStatus(agent, isActive) {
        // Map backend node names to frontend ID suffixes
        const mapping = {
            'value_analyst': 'value',
            'technical_analyst': 'tech',
            'risk_compliance': 'risk',
            'financial_analyst': 'financial',
            // Also handle generic or specific mappings if needed
            'Value_Analyst': 'value',
            'Technical_Analyst': 'tech',
            'Risk_Compliance': 'risk',
            'Financial_Analyst': 'financial'
        };
        const id = mapping[agent];
        if (id) {
            const dot = document.querySelector(`.dot-${id}`);
            if (dot) {
                if (isActive) dot.classList.add('pulse');
                else dot.classList.remove('pulse');
            }
        }
    }

    async function handleAnalysis() {
        const query = userInput.value.trim();
        if (!query) return;

        userInput.value = '';
        addLog('USER', query, 'tech');
        addLog('SYSTEM', 'Spinning up swarm...', 'tech');
        
        // Clear old proposals and report
        document.getElementById('synthesis-report').innerHTML = '';
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

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedData = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                accumulatedData += decoder.decode(value, { stream: true });
                const lines = accumulatedData.split('\n\n');
                accumulatedData = lines.pop(); // Keep incomplete line

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            processEvent(data);
                        } catch (e) {
                            console.error('Error parsing SSE event:', e);
                        }
                    }
                }
            }
        } catch (err) {
            addLog('ERROR', 'Workflow execution failed. Check server logs.', 'risk');
            console.error(err);
        }
    }

    function processEvent(data) {
        switch (data.type) {
            case 'agent_start':
                const agentName = data.agent || 'Agent';
                addLog(agentName, 'Thinking...', getAgentType(agentName));
                updateStatus(agentName, true);
                break;
            case 'tool_start':
                addLog('SYSTEM', `Calling tool: ${data.tool} (${data.input || ''})`, 'tech');
                break;
            case 'tool_end':
                // Optional: add tool finish log
                break;
            case 'final_result':
                // Reset all dots
                document.querySelectorAll('.status-dot').forEach(d => d.classList.remove('pulse'));
                
                // Render Synthesis Report
                const reportContainer = document.getElementById('synthesis-report');
                if (data.final_report) {
                    reportContainer.innerHTML = `
                        <div class="synthesis-card">
                            <div class="synthesis-header">STRATEGIC SYNTHESIS</div>
                            <div class="synthesis-body">${data.final_report}</div>
                        </div>
                    `;
                }

                if (data.proposals && data.proposals.length > 0) {
                    data.proposals.forEach(prop => {
                        renderProposal(prop, data.is_validated);
                    });
                    addLog('SYSTEM', 'Analysis complete. Final report generated.', 'tech');
                } else {
                    addLog('SYSTEM', 'No suitable assets found meeting criteria.', 'risk');
                }
                break;
            case 'error':
                addLog('ERROR', data.detail, 'risk');
                break;
        }
    }

    function getAgentType(name) {
        const n = name.toLowerCase();
        if (n.includes('value')) return 'value';
        if (n.includes('tech')) return 'tech';
        if (n.includes('risk')) return 'risk';
        if (n.includes('financial')) return 'financial';
        return 'tech';
    }

    function renderProposal(prop, isValidated) {
        const card = document.createElement('div');
        card.className = 'proposal-card';
        
        const sharpe = prop.metrics ? prop.metrics.Sharpe_Ratio : 'N/A';
        const drawdown = prop.metrics ? (prop.metrics.Max_Drawdown * 100).toFixed(1) : 'N/A';

        card.innerHTML = `
            <div class="token-header">
                <span class="symbol">${prop.symbol}</span>
                <span class="badge ${isValidated ? 'badge-validated' : ''}">${isValidated ? 'VALIDATED' : 'REVIEW'}</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.4; margin-bottom: 0.8rem;">
                ${prop.rationale}
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
