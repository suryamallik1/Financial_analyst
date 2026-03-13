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

    const agentMap = {
        'ValueAnalystAgent': 'status-value',
        'TechnicalAnalystAgent': 'status-technical',
        'RiskComplianceAgent': 'status-risk',
        'FinancialAnalystAgent': 'status-financial'
    };

    function setAgentActive(agentName, active) {
        const id = agentMap[agentName];
        if (id) {
            const el = document.getElementById(id);
            if (active) el.classList.add('active');
            else el.classList.remove('active');
        }
    }

    async function handleAnalysis() {
        const query = userInput.value.trim();
        if (!query) return;

        userInput.value = '';
        addLog('USER', query, 'tech');
        addLog('SYSTEM', 'Initializing swarm...', 'tech');
        
        // Reset UI
        const header = proposalsPanel.firstElementChild;
        proposalsPanel.innerHTML = '';
        proposalsPanel.appendChild(header);
        Object.values(agentMap).forEach(id => document.getElementById(id).classList.remove('active'));

        try {
            const response = await fetch('/api/v1/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_request: query })
            });

            if (!response.ok) throw new Error('API Error');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let activeAgent = null;

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const event = JSON.parse(line.substring(6));
                        
                        if (event.type === 'agent_start') {
                            if (activeAgent) setAgentActive(activeAgent, false);
                            activeAgent = event.agent;
                            setAgentActive(activeAgent, true);
                            addLog(activeAgent.replace('Agent', ''), 'Thinking...', 'tech');
                        } 
                        else if (event.type === 'tool_start') {
                            addLog('SYSTEM', `Calling tool: <span style="color:#f2cc60">${event.tool}</span>`, 'tech');
                        }
                        else if (event.type === 'final_result') {
                            if (activeAgent) setAgentActive(activeAgent, false);
                            if (event.proposals && event.proposals.length > 0) {
                                event.proposals.forEach(prop => renderProposal(prop, event.is_validated));
                                addLog('SYSTEM', 'Analysis complete.', 'tech');
                            } else {
                                addLog('SYSTEM', 'No suitable assets found.', 'risk');
                            }
                        }
                        else if (event.type === 'error') {
                            addLog('ERROR', event.detail, 'risk');
                        }
                    }
                }
            }

        } catch (err) {
            addLog('ERROR', 'Connection lost or server failed.', 'risk');
            console.error(err);
        } finally {
            Object.values(agentMap).forEach(id => document.getElementById(id).classList.remove('active'));
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
