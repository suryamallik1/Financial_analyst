document.addEventListener('DOMContentLoaded', () => {
    const consoleOutput = document.getElementById('console-output');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const proposalsPanel = document.getElementById('proposals-panel');
    const synthesisReport = document.getElementById('synthesis-report');
    const synthesisLoading = document.getElementById('synthesis-loading');

    // Agent to class mapping for visualization
    const agentNodeMapping = {
        'intake_agent': 'intake',
        'Intake_Agent': 'intake',
        'value_analyst': 'value',
        'Value_Analyst': 'value',
        'technical_analyst': 'tech',
        'Technical_Analyst': 'tech',
        'risk_compliance': 'risk',
        'Risk_Compliance': 'risk',
        'financial_analyst': 'fin',
        'Financial_Analyst': 'fin'
    };

    const agentColorMapping = {
        'intake': 'var(--accent-blue)',
        'value': '#facc15',
        'tech': 'var(--accent-green)',
        'risk': 'var(--accent-danger)',
        'fin': 'var(--accent-magenta)',
        'system': 'var(--accent-indigo)',
        'user': '#fff'
    };

    function addLog(agent, message, type = 'tech') {
        const div = document.createElement('div');
        div.className = `agent-log log-type-${type}`;
        
        let color = agentColorMapping[type] || agentColorMapping['tech'];
        if(agent === 'USER') color = agentColorMapping['user'];
        if(agent === 'SYSTEM') color = agentColorMapping['system'];
        if(agent === 'ERROR') color = agentColorMapping['risk'];

        div.innerHTML = `<span class="agent-name" style="color: ${color}">[${agent}]</span><span class="msg-content">${message}</span>`;
        consoleOutput.appendChild(div);
        
        // Smooth scroll to bottom
        consoleOutput.scrollTo({
            top: consoleOutput.scrollHeight,
            behavior: 'smooth'
        });
    }

    function deactivateAllNodes() {
        document.querySelectorAll('.agent-node').forEach(node => {
            node.className = 'agent-node'; // reset to base
        });
        document.querySelectorAll('.conn-line').forEach(line => {
            line.classList.remove('active');
        });
    }

    function activateNode(agentName) {
        deactivateAllNodes();
        
        if (agentName === 'USER') {
            document.getElementById('node-user').classList.add('active-user');
            return;
        }

        const nodeId = agentNodeMapping[agentName];
        if (nodeId) {
            const nodeEl = document.getElementById(`node-${nodeId}`);
            if (nodeEl) {
                nodeEl.classList.add(`active-${nodeId}`);
            }
            if(nodeId === 'intake') {
                document.getElementById('conn-user-intake')?.classList.add('active');
            } else if (nodeId !== 'fin') {
                document.getElementById(`conn-intake-${nodeId}`)?.classList.add('active');
            } else if (nodeId === 'fin') {
                document.getElementById(`conn-value-fin`)?.classList.add('active');
                document.getElementById(`conn-risk-fin`)?.classList.add('active');
                document.getElementById(`conn-tech-fin`)?.classList.add('active');
            }
        }
    }

    async function fetchProactiveState() {
        try {
            const stateRes = await fetch('/api/v1/state');
            if (!stateRes.ok) return;
            const stateData = await stateRes.json();
            
            if (stateData && stateData.final_weights && Object.keys(stateData.final_weights).length > 0) {
                const briefContainer = document.getElementById('daily-brief');
                const content = document.getElementById('daily-brief-content');
                
                let cardsHtml = '';
                for(const [ticker, weight] of Object.entries(stateData.final_weights)) {
                    cardsHtml += `
                        <div class="brief-stock-card">
                            <span class="brief-symbol">${ticker}</span>
                            <span class="brief-weight">${(weight*100).toFixed(2)}% ALLOCATION</span>
                        </div>
                    `;
                }
                content.innerHTML = cardsHtml;
                briefContainer.classList.remove('hidden');
            }
        } catch(e) { console.error('Error fetching proactive state', e); }
    }

    // Call it immediately on load
    fetchProactiveState();

    async function handleAnalysis() {
        const query = userInput.value.trim();
        if (!query) return;

        // UI Reset
        userInput.value = '';
        proposalsPanel.innerHTML = '';
        synthesisReport.innerHTML = `
            <div style="padding-top: 2rem; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
               <p style="color: var(--text-sec)">Analyzing directive...</p>
            </div>
        `;
        synthesisLoading.classList.remove('hidden');

        // Initial Logs & Vis
        addLog('USER', query, 'user');
        activateNode('USER');
        
        setTimeout(() => {
            addLog('SYSTEM', 'Spinning up swarm via distributed task queue (Celery)...', 'system');
        }, 500);

        try {
            // Trigger Celery Task
            const triggerRes = await fetch('/api/v1/trigger', {
                method: 'POST'
            });

            if (!triggerRes.ok) throw new Error('API Error triggering pipeline');
            addLog('SYSTEM', 'Pipeline execution triggered. Monitoring state...', 'tool');

            // Simulated active nodes while polling
            const nodes = ['intake', 'value', 'tech', 'risk', 'fin'];
            let nodeIdx = 0;
            const simInterval = setInterval(() => {
                activateNode(nodes[nodeIdx]);
                addLog('SYSTEM', `Agent [${nodes[nodeIdx].toUpperCase()}] processing data subset...`, 'tech');
                nodeIdx = (nodeIdx + 1) % nodes.length;
            }, 3000);

            // Poll for state
            const pollInterval = setInterval(async () => {
                try {
                    const stateRes = await fetch('/api/v1/state');
                    if (!stateRes.ok) return;
                    
                    const stateData = await stateRes.json();
                    
                    // If it has final_weights, the pipeline is likely done
                    if (stateData && stateData.final_weights && Object.keys(stateData.final_weights).length > 0) {
                        clearInterval(pollInterval);
                        clearInterval(simInterval);
                        
                        // Fake a final result event for the UI processor
                        const finalEvent = {
                            type: 'final_result',
                            final_report: "## Final Allocation\\nPipeline execution stabilized. Asset allocation derived from Hierarchical Risk Parity optimization.\\n\\n" + JSON.stringify(stateData.final_weights, null, 2),
                            proposals: Object.keys(stateData.final_weights).map(ticker => ({
                                symbol: ticker,
                                rationale: `Optimized weight: ${(stateData.final_weights[ticker]*100).toFixed(2)}%`,
                                metrics: stateData.backtest_metrics || { Sharpe_Ratio: 'N/A', Max_Drawdown: 'N/A' }
                            })),
                            is_validated: stateData.is_validated
                        };
                        
                        processEvent(finalEvent);
                    }
                } catch(e) { /* ignore single poll failures */ }
            }, 3000);

        } catch (err) {
            addLog('ERROR', 'Workflow execution failed. Check server logs.', 'risk');
            synthesisLoading.classList.add('hidden');
            synthesisReport.innerHTML = `<div class="empty-state">Error executing workflow.</div>`;
            deactivateAllNodes();
            console.error(err);
        }
    }

    // Basic markdown to html parser
    function parseMarkdown(md) {
        if (!md) return '';
        let html = md.replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*)\*/gim, '<i>$1</i>')
            .replace(/!\[(.*?)\]\((.*?)\)/gim, "<img alt='$1' src='$2' />")
            .replace(/\[(.*?)\]\((.*?)\)/gim, "<a href='$2'>$1</a>")
            .replace(/\n$/gim, '<br />');

        // Very basic list handling
        html = html.replace(/^\- (.*$)/gim, '<ul><li>$1</li></ul>');
        html = html.replace(/<\/ul>\n<ul>/gim, '');
        
        // line breaks
        return html.replace(/\n/g, '<p></p>');
    }

    function processEvent(data) {
        switch (data.type) {
            case 'agent_start':
                const agentName = data.agent || 'Agent';
                const mappedType = agentNodeMapping[agentName] || 'tech';
                addLog(agentName, 'Processing node inputs...', mappedType);
                activateNode(agentName);
                break;

            case 'tool_start':
                addLog('SYSTEM', `Executing tool: ${data.tool} (${data.input || ''})`, 'tool');
                break;

            case 'final_result':
                deactivateAllNodes();
                synthesisLoading.classList.add('hidden');
                
                // Final node glow
                document.getElementById('node-fin')?.classList.add('active-fin');
                
                // Render Synthesis Report with typing effect
                if (data.final_report) {
                    const parsedHtml = parseMarkdown(data.final_report);
                    // Fast insert, an advanced version would stream the typed text
                    synthesisReport.innerHTML = `<div class="typing-container" style="animation: none; border-right: none;">${parsedHtml}</div>`;
                } else {
                    synthesisReport.innerHTML = `<div class="empty-state">Synthesis resulted in no definitive strategy.</div>`;
                }

                // Render Proposals
                if (data.proposals && data.proposals.length > 0) {
                    data.proposals.forEach((prop, i) => {
                        // Stagger animation
                        setTimeout(() => {
                            renderProposal(prop, data.is_validated);
                        }, i * 200);
                    });
                    addLog('SYSTEM', 'Analysis complete. Final report and proposals generated.', 'system');
                } else {
                    addLog('SYSTEM', 'No suitable assets found meeting criteria.', 'risk');
                }
                
                setTimeout(() => deactivateAllNodes(), 3000);
                break;

            case 'error':
                addLog('ERROR', data.detail, 'risk');
                synthesisLoading.classList.add('hidden');
                deactivateAllNodes();
                break;
        }
    }

    function renderProposal(prop, isValidated) {
        const card = document.createElement('div');
        card.className = isValidated ? 'proposal-card validated' : 'proposal-card';
        
        let sharpe = prop.metrics ? prop.metrics.Sharpe_Ratio : 'N/A';
        let drawdown = prop.metrics ? prop.metrics.Max_Drawdown : 'N/A';

        if (typeof sharpe === 'number') sharpe = sharpe.toFixed(2);
        if (typeof drawdown === 'number') {
            const isDanger = drawdown > 0.2 || drawdown < -0.2;
            drawdown = `<span class="m-value ${isDanger ? 'danger' : ''}">${(drawdown * 100).toFixed(1)}%</span>`;
        } else {
            drawdown = `<span class="m-value">${drawdown}</span>`;
        }

        card.innerHTML = `
            <div class="prop-header">
                <span class="prop-symbol">${prop.symbol}</span>
                <span class="prop-status ${isValidated ? 'validated' : ''}">${isValidated ? 'EXTRACTED / VALID' : 'CANDIDATE'}</span>
            </div>
            <div class="prop-body">
                ${prop.rationale ? prop.rationale.substring(0, 150) + '...' : 'No rationale provided.'}
            </div>
            <div class="prop-metrics">
                <div class="metric-box">
                    <span class="m-label">SHARPE RATIO</span>
                    <span class="m-value">${sharpe}</span>
                </div>
                <div class="metric-box">
                    <span class="m-label">MAX DRAWDOWN</span>
                    ${drawdown}
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
