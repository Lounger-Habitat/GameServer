// 服务器API基础URL
const API_BASE_URL = 'http://localhost:8000/api';
const WS_BASE_URL = 'ws://localhost:8000';

// 当前WebSocket连接
let socket = null;

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    // 初始化标签切换功能
    initTabs();
    
    // 初始化游戏管理功能
    initGamesTab();
    
    // 初始化玩家管理功能
    initPlayersTab();
    
    // 初始化WebSocket功能
    initWebSocketTab();
    
    // 首次加载数据
    fetchGames();
    fetchPlayers();
});

// 初始化标签切换功能
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // 移除所有标签和内容的active类
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // 添加当前标签和对应内容的active类
            tab.classList.add('active');
            const tabId = tab.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// ==================== 游戏管理功能 ====================

function initGamesTab() {
    // 刷新游戏列表按钮
    document.getElementById('refreshGames').addEventListener('click', fetchGames);
    
    // 创建游戏按钮
    document.getElementById('createGame').addEventListener('click', createGame);
}

// 获取所有游戏
async function fetchGames() {
    try {
        const response = await fetch(`${API_BASE_URL}/games/`);
        const games = await response.json();
        displayGames(games);
        
        // 更新WebSocket标签中的游戏选择器
        updateGameSelector(games);
    } catch (error) {
        console.error('获取游戏列表失败:', error);
        alert('获取游戏列表失败');
    }
}

// 显示游戏列表
function displayGames(games) {
    const gamesList = document.getElementById('gamesList');
    gamesList.innerHTML = '';
    
    games.forEach(game => {
        const gameItem = document.createElement('div');
        gameItem.className = 'game-item';
        gameItem.innerHTML = `
            <h3>${game.name} (ID: ${game.id})</h3>
            <p>${game.description}</p>
            <p>玩家: ${game.current_players}/${game.max_players}</p>
            <p>状态: ${game.active ? '活跃' : '不活跃'}</p>
            <button onclick="deleteGame(${game.id})">删除</button>
        `;
        gamesList.appendChild(gameItem);
    });
}

// 创建新游戏
async function createGame() {
    const name = document.getElementById('gameName').value.trim();
    const description = document.getElementById('gameDescription').value.trim();
    const maxPlayers = parseInt(document.getElementById('maxPlayers').value);
    
    if (!name || !description || isNaN(maxPlayers)) {
        alert('请填写所有必填字段');
        return;
    }
    
    const gameData = {
        name,
        description,
        max_players: maxPlayers
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/games/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(gameData)
        });
        
        if (response.status === 201) {
            const newGame = await response.json();
            alert(`游戏 "${newGame.name}" 创建成功!`);
            
            // 清空表单
            document.getElementById('gameName').value = '';
            document.getElementById('gameDescription').value = '';
            document.getElementById('maxPlayers').value = '4';
            
            // 刷新游戏列表
            fetchGames();
        } else {
            const error = await response.json();
            alert(`创建游戏失败: ${error.detail || '未知错误'}`);
        }
    } catch (error) {
        console.error('创建游戏失败:', error);
        alert('创建游戏失败');
    }
}

// 删除游戏
async function deleteGame(gameId) {
    if (!confirm(`确定要删除ID为 ${gameId} 的游戏吗?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/games/${gameId}`, {
            method: 'DELETE'
        });
        
        if (response.status === 204) {
            alert('游戏删除成功!');
            fetchGames();
        } else {
            const error = await response.json();
            alert(`删除游戏失败: ${error.detail || '未知错误'}`);
        }
    } catch (error) {
        console.error('删除游戏失败:', error);
        alert('删除游戏失败');
    }
}

// ==================== 玩家管理功能 ====================

function initPlayersTab() {
    // 刷新玩家列表按钮
    document.getElementById('refreshPlayers').addEventListener('click', fetchPlayers);
    
    // 创建玩家按钮
    document.getElementById('createPlayer').addEventListener('click', createPlayer);
}

// 获取所有玩家
async function fetchPlayers() {
    try {
        const response = await fetch(`${API_BASE_URL}/players/`);
        const players = await response.json();
        displayPlayers(players);
        
        // 更新WebSocket标签中的玩家选择器
        updatePlayerSelector(players);
    } catch (error) {
        console.error('获取玩家列表失败:', error);
        alert('获取玩家列表失败');
    }
}

// 显示玩家列表
function displayPlayers(players) {
    const playersList = document.getElementById('playersList');
    playersList.innerHTML = '';
    
    players.forEach(player => {
        const playerItem = document.createElement('div');
        playerItem.className = 'player-item';
        playerItem.innerHTML = `
            <h3>${player.display_name || player.username} (ID: ${player.id})</h3>
            <p>用户名: ${player.username}</p>
            <p>邮箱: ${player.email}</p>
            <p>当前游戏: ${player.current_game_id ? player.current_game_id : '无'}</p>
            <div>
                ${player.current_game_id ? 
                    `<button onclick="leaveGame(${player.id})">离开游戏</button>` : 
                    `<select id="gameSelect-${player.id}" class="game-select"></select>
                    <button onclick="joinGame(${player.id})">加入游戏</button>`
                }
                <button onclick="deletePlayer(${player.id})">删除玩家</button>
            </div>
        `;
        playersList.appendChild(playerItem);
        
        // 如果玩家不在游戏中，填充游戏选择器
        if (!player.current_game_id) {
            fillGameSelector(`gameSelect-${player.id}`);
        }
    });
}

// 填充游戏选择器
async function fillGameSelector(selectId) {
    try {
        const response = await fetch(`${API_BASE_URL}/games/`);
        const games = await response.json();
        
        const select = document.getElementById(selectId);
        select.innerHTML = '';
        
        games.forEach(game => {
            const option = document.createElement('option');
            option.value = game.id;
            option.textContent = `${game.name} (ID: ${game.id})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('获取游戏列表失败:', error);
    }
}

// 创建新玩家
async function createPlayer() {
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const displayName = document.getElementById('displayName').value.trim();
    
    if (!username || !email) {
        alert('用户名和邮箱为必填字段');
        return;
    }
    
    const playerData = {
        username,
        email,
        display_name: displayName || null
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/players/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(playerData)
        });
        
        if (response.status === 201) {
            const newPlayer = await response.json();
            alert(`玩家 "${newPlayer.username}" 创建成功!`);
            
            // 清空表单
            document.getElementById('username').value = '';
            document.getElementById('email').value = '';
            document.getElementById('displayName').value = '';
            
            // 刷新玩家列表
            fetchPlayers();
        } else {
            const error = await response.json();
            alert(`创建玩家失败: ${error.detail || '未知错误'}`);
        }
    } catch (error) {
        console.error('创建玩家失败:', error);
        alert('创建玩家失败');
    }
}

// 玩家加入游戏
async function joinGame(playerId) {
    const selectId = `gameSelect-${playerId}`;
    const gameId = document.getElementById(selectId).value;
    
    if (!gameId) {
        alert('请选择一个游戏');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/players/${playerId}/join/${gameId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const updatedPlayer = await response.json();
            alert(`玩家已成功加入游戏 ${updatedPlayer.current_game_id}`);
            fetchPlayers();
        } else {
            const error = await response.json();
            alert(`加入游戏失败: ${error.detail || '未知错误'}`);
        }
    } catch (error) {
        console.error('加入游戏失败:', error);
        alert('加入游戏失败');
    }
}

// 玩家离开游戏
async function leaveGame(playerId) {
    try {
        const response = await fetch(`${API_BASE_URL}/players/${playerId}/leave`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('玩家已成功离开游戏');
            fetchPlayers();
        } else {
            const error = await response.json();
            alert(`离开游戏失败: ${error.detail || '未知错误'}`);
        }
    } catch (error) {
        console.error('离开游戏失败:', error);
        alert('离开游戏失败');
    }
}

// 删除玩家
async function deletePlayer(playerId) {
    if (!confirm(`确定要删除ID为 ${playerId} 的玩家吗?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/players/${playerId}`, {
            method: 'DELETE'
        });
        
        if (response.status === 204) {
            alert('玩家删除成功!');
            fetchPlayers();
        } else {
            const error = await response.json();
            alert(`删除玩家失败: ${error.detail || '未知错误'}`);
        }
    } catch (error) {
        console.error('删除玩家失败:', error);
        alert('删除玩家失败');
    }
}

// ==================== WebSocket功能 ====================

function initWebSocketTab() {
    // 连接类型选择器变化事件
    document.getElementById('wsType').addEventListener('change', function() {
        const gamePlayerSelectors = document.getElementById('gamePlayerSelectors');
        if (this.value === 'game') {
            gamePlayerSelectors.style.display = 'block';
        } else {
            gamePlayerSelectors.style.display = 'none';
        }
    });
    
    // 连接按钮
    document.getElementById('connectWs').addEventListener('click', connectWebSocket);
    
    // 断开连接按钮
    document.getElementById('disconnectWs').addEventListener('click', disconnectWebSocket);
    
    // 消息类型选择器变化事件
    document.getElementById('messageType').addEventListener('change', updateMessageParams);
    
    // 发送消息按钮
    document.getElementById('sendMessage').addEventListener('click', sendWebSocketMessage);
    
    // 初始化消息参数表单
    updateMessageParams();
}

// 更新游戏选择器
function updateGameSelector(games) {
    const wsGameId = document.getElementById('wsGameId');
    wsGameId.innerHTML = '';
    
    games.forEach(game => {
        const option = document.createElement('option');
        option.value = game.id;
        option.textContent = `${game.name} (ID: ${game.id})`;
        wsGameId.appendChild(option);
    });
}

// 更新玩家选择器
function updatePlayerSelector(players) {
    const wsPlayerId = document.getElementById('wsPlayerId');
    wsPlayerId.innerHTML = '';
    
    players.forEach(player => {
        const option = document.createElement('option');
        option.value = player.id;
        option.textContent = `${player.username} (ID: ${player.id})`;
        wsPlayerId.appendChild(option);
    });
}

// 连接WebSocket
function connectWebSocket() {
    if (socket) {
        addMessageToLog('已经连接到WebSocket服务器', 'system');
        return;
    }
    
    const wsType = document.getElementById('wsType').value;
    let wsUrl;
    
    if (wsType === 'general') {
        wsUrl = `${WS_BASE_URL}/ws`;
    } else {
        const gameId = document.getElementById('wsGameId').value;
        const playerId = document.getElementById('wsPlayerId').value;
        wsUrl = `${WS_BASE_URL}/ws/${gameId}/${playerId}`;
    }
    
    try {
        socket = new WebSocket(wsUrl);
        
        socket.onopen = function() {
            document.getElementById('connectionStatus').textContent = '已连接';
            document.getElementById('connectionStatus').style.color = 'green';
            document.getElementById('connectWs').disabled = true;
            document.getElementById('disconnectWs').disabled = false;
            document.getElementById('sendMessage').disabled = false;
            
            addMessageToLog(`WebSocket连接已建立: ${wsUrl}`, 'system');
        };
        
        socket.onmessage = function(event) {
            const message = JSON.parse(event.data);
            addMessageToLog(JSON.stringify(message, null, 2), 'received');
        };
        
        socket.onclose = function() {
            addMessageToLog('WebSocket连接已关闭', 'system');
            resetWebSocketConnection();
        };
        
        socket.onerror = function(error) {
            addMessageToLog(`WebSocket错误: ${error.message}`, 'error');
            resetWebSocketConnection();
        };
    } catch (error) {
        addMessageToLog(`WebSocket连接失败: ${error.message}`, 'error');
        resetWebSocketConnection();
    }
}

// 断开WebSocket连接
function disconnectWebSocket() {
    if (socket) {
        socket.close();
        resetWebSocketConnection();
        addMessageToLog('WebSocket连接已手动关闭', 'system');
    }
}

// 重置WebSocket连接状态
function resetWebSocketConnection() {
    socket = null;
    document.getElementById('connectionStatus').textContent = '未连接';
    document.getElementById('connectionStatus').style.color = 'red';
    document.getElementById('connectWs').disabled = false;
    document.getElementById('disconnectWs').disabled = true;
    document.getElementById('sendMessage').disabled = true;
}

// 更新消息参数表单
function updateMessageParams() {
    const messageType = document.getElementById('messageType').value;
    const messageParams = document.getElementById('messageParams');
    messageParams.innerHTML = '';
    
    switch (messageType) {
        case 'ping':
            messageParams.innerHTML = `
                <div class="form-group">
                    <label for="pingMessage">消息内容:</label>
                    <input type="text" id="pingMessage" placeholder="输入消息内容">
                </div>
            `;
            break;
            
        case 'join_game':
            messageParams.innerHTML = `
                <div class="form-group">
                    <label for="joinGameId">游戏ID:</label>
                    <input type="number" id="joinGameId" min="1" value="1">
                </div>
                <div class="form-group">
                    <label for="joinPlayerId">玩家ID:</label>
                    <input type="number" id="joinPlayerId" min="1" value="1">
                </div>
            `;
            break;
            
        case 'game_message':
            messageParams.innerHTML = `
                <div class="form-group">
                    <label for="gameAction">动作:</label>
                    <input type="text" id="gameAction" placeholder="例如: move, attack, use_item">
                </div>
                <div class="form-group">
                    <label for="gamePositionX">位置X:</label>
                    <input type="number" id="gamePositionX" value="0">
                </div>
                <div class="form-group">
                    <label for="gamePositionY">位置Y:</label>
                    <input type="number" id="gamePositionY" value="0">
                </div>
                <div class="form-group">
                    <label for="gameCustomData">自定义数据 (JSON):</label>
                    <input type="text" id="gameCustomData" placeholder='{"key": "value"}'>
                </div>
            `;
            break;
            
        case 'direct_message':
            messageParams.innerHTML = `
                <div class="form-group">
                    <label for="dmToPlayerId">接收者玩家ID:</label>
                    <input type="number" id="dmToPlayerId" min="1" value="1">
                </div>
                <div class="form-group">
                    <label for="dmMessage">消息内容:</label>
                    <input type="text" id="dmMessage" placeholder="输入消息内容">
                </div>
            `;
            break;
    }
}

// 发送WebSocket消息
function sendWebSocketMessage() {
    if (!socket) {
        addMessageToLog('未连接到WebSocket服务器', 'error');
        return;
    }
    
    const messageType = document.getElementById('messageType').value;
    let message = { type: messageType };
    
    switch (messageType) {
        case 'ping':
            const pingMessage = document.getElementById('pingMessage').value;
            message.data = { message: pingMessage };
            break;
            
        case 'join_game':
            message.game_id = parseInt(document.getElementById('joinGameId').value);
            message.player_id = parseInt(document.getElementById('joinPlayerId').value);
            break;
            
        case 'game_message':
            const action = document.getElementById('gameAction').value;
            const posX = parseInt(document.getElementById('gamePositionX').value);
            const posY = parseInt(document.getElementById('gamePositionY').value);
            let customData = {};
            
            try {
                const customDataInput = document.getElementById('gameCustomData').value;
                if (customDataInput) {
                    customData = JSON.parse(customDataInput);
                }
            } catch (error) {
                addMessageToLog('自定义数据JSON格式错误', 'error');
                return;
            }
            
            message.content = {
                action: action,
                position: { x: posX, y: posY },
                ...customData
            };
            break;
            
        case 'direct_message':
            message.to_player_id = parseInt(document.getElementById('dmToPlayerId').value);
            message.content = { message: document.getElementById('dmMessage').value };
            break;
    }
    
    try {
        socket.send(JSON.stringify(message));
        addMessageToLog(JSON.stringify(message, null, 2), 'sent');
    } catch (error) {
        addMessageToLog(`发送消息失败: ${error.message}`, 'error');
    }
}

// 添加消息到日志
function addMessageToLog(message, type) {
    const messageLog = document.getElementById('messageLog');
    const messageElement = document.createElement('div');
    messageElement.className = `message ${type}`;
    
    // 格式化JSON消息
    if (type === 'sent' || type === 'received') {
        try {
            if (typeof message === 'string' && message.trim().startsWith('{')) {
                const jsonObj = JSON.parse(message);
                message = JSON.stringify(jsonObj, null, 2);
            }
        } catch (e) {
            // 如果解析失败，保持原始消息
        }
    }
    
    messageElement.textContent = message;
    messageLog.appendChild(messageElement);
    
    // 滚动到底部
    messageLog.scrollTop = messageLog.scrollHeight;
}