// Star Protocol Monitor - Enhanced Real-time Visualization

class StarProtocolMonitor {
    constructor() {
        this.ws = null;
        this.messages = [];
        this.maxMessages = 1000;
        this.isPaused = false;
        this.messageCount = 0;
        this.lastMessageTime = Date.now();
        this.messageRate = 0;

        // D3 Graph
        this.svg = null;
        this.simulation = null;
        this.nodes = new Map();
        this.links = [];
        this.linkElements = null;
        this.nodeElements = null;

        this.init();
    }

    init() {
        this.setupWebSocket();
        this.setupEventListeners();
        this.setupD3Graph();
        this.startStatsPolling();
    }

    // WebSocket Connection
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/monitor/monitor_${Date.now()}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            try {
                const envelope = JSON.parse(event.data);
                this.handleMessage(envelope);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            setTimeout(() => this.setupWebSocket(), 3000);
        };
    }

    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connectionStatus');
        if (connected) {
            statusEl.textContent = '🟢 已连接';
            statusEl.className = 'status-connected';
        } else {
            statusEl.textContent = '🔴 未连接';
            statusEl.className = 'status-disconnected';
        }
    }

    // Message Handling
    handleMessage(envelope) {
        this.messages.unshift(envelope);
        if (this.messages.length > this.maxMessages) {
            this.messages.pop();
        }

        this.messageCount++;
        const now = Date.now();
        if (now - this.lastMessageTime > 1000) {
            this.messageRate = this.messageCount;
            this.messageCount = 0;
            this.lastMessageTime = now;
            document.getElementById('msgRate').textContent = this.messageRate;
        }

        if (!this.isPaused) {
            this.addLogEntry(envelope);
            this.updateGraph(envelope);
        }
    }

    addLogEntry(envelope) {
        const logContent = document.getElementById('messageLog');
        const entry = document.createElement('div');
        entry.className = `log-entry ${envelope.type}`;

        const timestamp = new Date(envelope.timestamp).toLocaleTimeString('zh-CN');

        let contentPreview = '';
        try {
            if (envelope.data && envelope.data.content) {
                contentPreview = JSON.stringify(envelope.data.content, null, 2);
            } else {
                contentPreview = JSON.stringify(envelope.data, null, 2);
            }
        } catch (e) {
            contentPreview = String(envelope.data);
        }

        entry.innerHTML = `
            <div class="log-entry-header">
                <span class="log-type">${envelope.type}</span>
                <span class="log-timestamp">${timestamp}</span>
            </div>
            <div class="log-route">
                ${envelope.sender} → ${envelope.recipient}
            </div>
            <div class="log-content-preview">${contentPreview}</div>
        `;

        const filterType = document.getElementById('filterType').value;
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();

        if (filterType !== 'all' && envelope.type !== filterType) {
            entry.style.display = 'none';
        }

        if (searchTerm && !envelope.sender.toLowerCase().includes(searchTerm) &&
            !envelope.recipient.toLowerCase().includes(searchTerm)) {
            entry.style.display = 'none';
        }

        logContent.insertBefore(entry, logContent.firstChild);

        while (logContent.children.length > 100) {
            logContent.removeChild(logContent.lastChild);
        }
    }

    // Enhanced D3 Graph Visualization
    setupD3Graph() {
        const container = document.getElementById('flowGraph');
        const width = container.clientWidth;
        const height = container.clientHeight;

        this.svg = d3.select('#flowGraph')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Add gradient definitions for links
        const defs = this.svg.append('defs');

        // Arrow markers with gradients
        const markerColors = {
            'system': '#ef5350',
            'message': '#5c6bc0',
            'broadcast': '#66bb6a'
        };

        Object.entries(markerColors).forEach(([type, color]) => {
            defs.append('marker')
                .attr('id', `arrow-${type}`)
                .attr('viewBox', '0 -5 10 10')
                .attr('refX', 28)
                .attr('refY', 0)
                .attr('markerWidth', 8)
                .attr('markerHeight', 8)
                .attr('orient', 'auto')
                .append('path')
                .attr('d', 'M0,-5L10,0L0,5')
                .attr('fill', color);
        });

        // Add glow filter for nodes
        const filter = defs.append('filter')
            .attr('id', 'glow');
        filter.append('feGaussianBlur')
            .attr('stdDeviation', '3')
            .attr('result', 'coloredBlur');
        const feMerge = filter.append('feMerge');
        feMerge.append('feMergeNode').attr('in', 'coloredBlur');
        feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

        // Create groups for links and nodes
        this.linksGroup = this.svg.append('g').attr('class', 'links');
        this.nodesGroup = this.svg.append('g').attr('class', 'nodes');

        // Add hub node
        this.addNode('hub', 'hub', width / 2, height / 2);

        // Setup enhanced force simulation
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id).distance(200).strength(0.5))
            .force('charge', d3.forceManyBody().strength(-800))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(50))
            .force('x', d3.forceX(width / 2).strength(0.1))
            .force('y', d3.forceY(height / 2).strength(0.1))
            .on('tick', () => this.ticked());

        this.updateSimulation();
    }

    addNode(id, role, x, y) {
        if (!this.nodes.has(id)) {
            const container = document.getElementById('flowGraph');

            // Infer role from id pattern
            if (!role || role === 'unknown') {
                if (id.startsWith('agent_')) role = 'agent';
                else if (id.startsWith('env_')) role = 'environment';
                else if (id.startsWith('human_')) role = 'human';
                else if (id.startsWith('monitor_')) role = 'monitor';
                else role = 'unknown';
            }

            this.nodes.set(id, {
                id: id,
                role: role,
                x: x || Math.random() * container.clientWidth,
                y: y || Math.random() * container.clientHeight,
                fx: id === 'hub' ? x : null,
                fy: id === 'hub' ? y : null,
                messageCount: 0
            });
        }
        return this.nodes.get(id);
    }

    updateGraph(envelope) {
        const senderNode = this.addNode(envelope.sender, this.extractRoleFromId(envelope.sender));
        senderNode.messageCount++;

        if (envelope.recipient !== 'hub' && !envelope.recipient.startsWith('@')) {
            const recipientNode = this.addNode(envelope.recipient, this.extractRoleFromId(envelope.recipient));
            recipientNode.messageCount++;
        }

        this.animateLink(envelope);
        this.updateSimulation();
    }

    extractRoleFromId(clientId) {
        if (clientId === 'hub') return 'hub';
        if (clientId.startsWith('agent_')) return 'agent';
        if (clientId.startsWith('env_')) return 'environment';
        if (clientId.startsWith('human_')) return 'human';
        if (clientId.startsWith('monitor_')) return 'monitor';
        return 'unknown';
    }

    animateLink(envelope) {
        const source = this.nodes.get(envelope.sender);
        const target = envelope.recipient === 'hub' || envelope.recipient.startsWith('@')
            ? this.nodes.get('hub')
            : this.nodes.get(envelope.recipient);

        if (!source || !target) return;

        const colors = {
            'system': '#ef5350',
            'message': '#5c6bc0',
            'broadcast': '#66bb6a'
        };
        const color = colors[envelope.type] || '#9fa8da';

        // Animated path with gradient
        const path = this.linksGroup.append('path')
            .attr('d', `M ${source.x} ${source.y} L ${source.x} ${source.y}`)
            .attr('stroke', color)
            .attr('stroke-width', 4)
            .attr('fill', 'none')
            .attr('opacity', 0)
            .attr('marker-end', `url(#arrow-${envelope.type})`)
            .style('filter', 'drop-shadow(0 0 4px ' + color + ')');

        path.transition()
            .duration(100)
            .attr('opacity', 0.9)
            .transition()
            .duration(800)
            .attr('d', `M ${source.x} ${source.y} L ${target.x} ${target.y}`)
            .transition()
            .duration(500)
            .attr('opacity', 0)
            .remove();

        // Animated particle
        const particle = this.linksGroup.append('circle')
            .attr('cx', source.x)
            .attr('cy', source.y)
            .attr('r', 6)
            .attr('fill', color)
            .attr('opacity', 1)
            .style('filter', 'drop-shadow(0 0 6px ' + color + ')');

        particle.transition()
            .duration(800)
            .attrTween('cx', () => t => source.x + (target.x - source.x) * t)
            .attrTween('cy', () => t => source.y + (target.y - source.y) * t)
            .attr('r', 4)
            .transition()
            .duration(200)
            .attr('r', 8)
            .attr('opacity', 0)
            .remove();
    }

    ticked() {
        if (this.nodeElements) {
            this.nodeElements.attr('transform', d => `translate(${d.x},${d.y})`);
        }
    }

    updateSimulation() {
        const nodesArray = Array.from(this.nodes.values());

        // Drag behavior
        const drag = d3.drag()
            .on('start', (event, d) => {
                if (!event.active) this.simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            })
            .on('drag', (event, d) => {
                d.fx = event.x;
                d.fy = event.y;
            })
            .on('end', (event, d) => {
                if (!event.active) this.simulation.alphaTarget(0);
                if (d.id !== 'hub') {
                    d.fx = null;
                    d.fy = null;
                }
            });

        // Update nodes
        this.nodesGroup.selectAll('.node').remove();

        this.nodeElements = this.nodesGroup.selectAll('.node')
            .data(nodesArray, d => d.id)
            .enter()
            .append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${d.x},${d.y})`)
            .style('cursor', 'grab')
            .call(drag);

        // Node circles with role-based colors
        const roleColors = {
            'hub': '#7e57c2',
            'agent': '#5c6bc0',
            'environment': '#66bb6a',
            'human': '#ffa726',
            'monitor': '#ab47bc',
            'unknown': '#9fa8da'
        };

        this.nodeElements.append('circle')
            .attr('r', d => d.id === 'hub' ? 35 : 25)
            .attr('fill', d => roleColors[d.role] || roleColors['unknown'])
            .attr('stroke', '#fff')
            .attr('stroke-width', 3)
            .style('filter', 'url(#glow)')
            .on('mouseover', function () {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('r', d => d.id === 'hub' ? 40 : 30);
            })
            .on('mouseout', function () {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('r', d => d.id === 'hub' ? 35 : 25);
            });

        // Role icon/emoji
        this.nodeElements.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', 5)
            .attr('font-size', d => d.id === 'hub' ? '20px' : '16px')
            .attr('pointer-events', 'none')
            .text(d => {
                if (d.id === 'hub') return '🌐';
                if (d.role === 'agent') return '🤖';
                if (d.role === 'environment') return '🌍';
                if (d.role === 'human') return '👤';
                if (d.role === 'monitor') return '👁️';
                return '❓';
            });

        // Node label
        this.nodeElements.append('text')
            .attr('dy', d => d.id === 'hub' ? 50 : 40)
            .attr('text-anchor', 'middle')
            .attr('fill', '#e8eaf6')
            .attr('font-size', '12px')
            .attr('font-weight', 'bold')
            .attr('pointer-events', 'none')
            .style('text-shadow', '0 0 4px rgba(0,0,0,0.8)')
            .text(d => {
                const maxLen = 15;
                return d.id.length > maxLen ? d.id.substring(0, maxLen) + '...' : d.id;
            });

        // Message count badge
        this.nodeElements.filter(d => d.messageCount > 0 && d.id !== 'hub')
            .append('circle')
            .attr('cx', 20)
            .attr('cy', -20)
            .attr('r', 10)
            .attr('fill', '#ef5350')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2);

        this.nodeElements.filter(d => d.messageCount > 0 && d.id !== 'hub')
            .append('text')
            .attr('x', 20)
            .attr('y', -16)
            .attr('text-anchor', 'middle')
            .attr('fill', '#fff')
            .attr('font-size', '10px')
            .attr('font-weight', 'bold')
            .attr('pointer-events', 'none')
            .text(d => d.messageCount > 99 ? '99+' : d.messageCount);

        this.simulation.nodes(nodesArray);
        this.simulation.alpha(0.5).restart();
    }

    // Stats Polling
    async startStatsPolling() {
        const poll = async () => {
            try {
                const [statsRes, clientsRes] = await Promise.all([
                    fetch('/api/monitor/stats'),
                    fetch('/api/monitor/clients')
                ]);

                const stats = await statsRes.json();
                const clientsData = await clientsRes.json();

                document.getElementById('totalClients').textContent = stats.total_clients;
                document.getElementById('totalEnvs').textContent = stats.total_environments;
                document.getElementById('uptime').textContent = this.formatUptime(stats.uptime);

                this.updateEnvironmentList(stats.environments);
                this.updateClientList(clientsData.clients);
            } catch (error) {
                console.error('Failed to fetch stats:', error);
            }
        };

        // Initial poll
        await poll();
        // Then poll every 2 seconds
        setInterval(poll, 2000);
    }

    formatUptime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        return `${hours}h ${minutes}m ${secs}s`;
    }

    updateEnvironmentList(environments) {
        const container = document.getElementById('environmentList');

        if (environments.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无环境</div>';
            return;
        }

        container.innerHTML = environments.map(env => `
            <div class="list-item">
                <div class="list-item-title">${env.env_id}</div>
                <div class="list-item-meta">${env.member_count} 成员${env.members.length > 0 ? ': ' + env.members.join(', ') : ''}</div>
            </div>
        `).join('');
    }

    updateClientList(clients) {
        const container = document.getElementById('clientList');

        if (!clients || clients.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无连接</div>';
            return;
        }

        // Sort clients by role
        const sortedClients = clients.sort((a, b) => {
            const roleOrder = { 'environment': 0, 'agent': 1, 'human': 2, 'monitor': 3 };
            return (roleOrder[a.role] || 99) - (roleOrder[b.role] || 99);
        });

        container.innerHTML = sortedClients.map(client => {
            const roleEmoji = {
                'agent': '🤖',
                'environment': '🌍',
                'human': '👤',
                'monitor': '👁️'
            };

            return `
                <div class="list-item">
                    <div class="list-item-title">${roleEmoji[client.role] || '❓'} ${client.client_id}</div>
                    <div class="list-item-meta">Role: ${client.role} | State: ${client.state}</div>
                </div>
            `;
        }).join('');
    }

    // Event Listeners
    setupEventListeners() {
        document.getElementById('pauseBtn').addEventListener('click', () => {
            this.isPaused = !this.isPaused;
            const btn = document.getElementById('pauseBtn');
            btn.textContent = this.isPaused ? '▶️ 继续' : '⏸️ 暂停';
        });

        document.getElementById('clearBtn').addEventListener('click', () => {
            document.getElementById('messageLog').innerHTML = '';
            this.messages = [];
        });

        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportLog();
        });

        document.getElementById('filterType').addEventListener('change', () => {
            this.applyFilters();
        });

        document.getElementById('searchInput').addEventListener('input', () => {
            this.applyFilters();
        });
    }

    applyFilters() {
        const filterType = document.getElementById('filterType').value;
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        const entries = document.querySelectorAll('.log-entry');

        entries.forEach(entry => {
            const type = entry.classList.contains('system') ? 'system' :
                entry.classList.contains('message') ? 'message' : 'broadcast';
            const route = entry.querySelector('.log-route').textContent.toLowerCase();

            const typeMatch = filterType === 'all' || type === filterType;
            const searchMatch = !searchTerm || route.includes(searchTerm);

            entry.style.display = (typeMatch && searchMatch) ? 'block' : 'none';
        });
    }

    exportLog() {
        const dataStr = JSON.stringify(this.messages, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `star-protocol-log-${Date.now()}.json`;
        link.click();
        URL.revokeObjectURL(url);
    }
}

// Initialize monitor when page loads
document.addEventListener('DOMContentLoaded', () => {
    new StarProtocolMonitor();
});
