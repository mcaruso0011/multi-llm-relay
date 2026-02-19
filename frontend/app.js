
    let currentConversationId = generateConversationId();
    let isWaitingForResponse = false;
    let allConversations = [];
    let currentFilters = {
        search: '',
        date: 'all',
        sort: 'newest'
    };

    const API_BASE = 'http://localhost:8000';

    // DOM elements
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const modelSelect = document.getElementById('modelSelect');
    const newChatBtn = document.getElementById('newChatBtn');
    const conversationList = document.getElementById('conversationList');
    const comparisonModeCheckbox = document.getElementById('comparisonMode');
    const modelSelector = document.getElementById('modelSelector');

    // Initialize
    document.addEventListener('DOMContentLoaded', () => {
        loadConversations();
        setupEventListeners();
        setupKeyboardShortcuts();
    });

    comparisonModeCheckbox.addEventListener('change', () => {
        modelSelector.style.display = comparisonModeCheckbox.checked ? 'block' : 'none';
    });

    function setupEventListeners() {
        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !isWaitingForResponse) {
                sendMessage();
            }
        });
        newChatBtn.addEventListener('click', startNewChat);

        // Search input
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', (e) => {
            currentFilters.search = e.target.value;
            updateClearFiltersButton();
            renderConversationList(applyFilters(allConversations));
        });

        // Date filter
        const dateFilter = document.getElementById('dateFilter');
        dateFilter.addEventListener('change', (e) => {
            currentFilters.date = e.target.value;
            updateClearFiltersButton();
            renderConversationList(applyFilters(allConversations));
        });

        // Sort filter
        const sortFiler = document.getElementById('sortFilter');
        sortFilter.addEventListener('change', (e) => {
            currentFilters.sort = e.target.value;
            updateClearFiltesButton();
            renderConversationList(applyFilters(allConversations));
        });

        // Clear filters button
        const clearFiltersBtn = document.getElementById('clearFilters');
        clearFiltersBtn.addEventListener('click', clearAllFilters);
    }

    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K: New chat
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                startNewChat();
                userInput.focus();
            }

            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }

            // Escape: Clear input
            if (e.key === 'Escape') {
                if (document.activeElement === userInput) {
                    userInput.value = '';
                } else if (document.activeElement === document.getElementById('searchInput')) {
                    clearAllFilters();
                }
            }
        });
    }

    function generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async function loadConversations() {
        try {
            const response = await fetch(`${API_BASE}/conversations`);
            const data = await response.json();

            if (data.conversations) {
                allConversations = data.conversations;
                renderConversationList(data.conversations);
            }
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    }

    function renderConversationList(conversations) {
        conversationList.innerHTML = '';

        if (conversations.length === 0) {
            const hasActiveFilters = currentFilters.search !== '' ||
                                     currentFilters.date !== 'all' ||
                                     currentFilters.sort !== 'newest';

            if (hasActiveFilters) {
                conversationsList.innerHTML = `
                <div class="no-results">
                    No conversations match your filters
                </div>
            `;
            } else {
                conversationList.innerHTML = `
                    <div style="padding: 20px; text-align: center; color: #888; font-size: 13px;">
                        No conversations yet<br>
                        <span style="font-size: 11px; color: #666;">Click "New Chat" to start</span>
                    </div>
                `;
            }
            return;
        }

        conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'conversation-item';
            if (conv.conversation_id === currentConversationId) {
                item.classList.add('active');
            }

            const createDate = new Date(conv.created_at).toLocaleDateString();
            const lastMessageDate = conv.last_message_at
                ? new Date(conv.last_message_at).toLocaleDateString()
                : createdDate;

            // Highlight search term in conversation ID
            let displayId = conv.conversation_id;
            if (currentFilters.search) {
                const regex = new RegExp(`(${currentFilters.search})`, 'gi');
                displayId = displayId.replace(regex, '<mark>$1</mark>');
            }

            item.innerHTML = `
                <div class="convesration-itme-header">
                    <div class="conversation-item-id">${conv.conversation_id}</div>
                    <button class="delete-btn" title="Delete conversation">x<</button>
                </div>
                    <div class="conversation-item-meta">
                        ${conv.message_count} messages • ${lastMessageDate}
                    </div>
             `;

            // Load conversation when clicking the item
             item.addEventListener('click', () => loadConversation(conv.conversation_id));

             // Delete conversation when clicking the delte button
            const deleteBtn = item.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', (e) => deleteConversation(conv.conversation_id, e));

            conversationList.appendChild(item);
        });
    }

    async function loadConversation(conversationId) {
        currentConversationId = conversationId;
        chatMessages.innerHTML = '';

        try {
            const response = await fetch(`${API_BASE}/ask`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    prompt: '', //Empty prompt to just get history
                    model: modelSelect.value,
                    conversation_id: currentConversationId
                })
            });

            const data = await response.json();

            if (data.history) {
                data.history.forEach(msg => {
                    displayMessage(msg.role, msg.content, '');
                });
            }

            loadConversations(); // Refresh sidebar to update active state
        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    }

    async function deleteConversation(conversationId, event) {
        event.stopPropagation(); // Prevent triggering the conversation load

        if (!confirm('Delete this conversation? This cannot be undone.')) {
            return;
        }

        // Find and mark the item as deleting
        const items = document.querySelectorAll('.conversation-item');
        items.forEach(item => {
            const itemId = item.querySelector('.conversation-item-id').textContent;
            if (itemId === conversationId) {
                item.classList.add('deleting');
            }
        });

        try {
            const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.error) {
                alert(`Failed to delete: ${data.error}`);
                // Remove deleting class on error
                items.forEach(item => item.classList.remove('deleting'));
                return;
            }

            // Wait for animation to complete
            setTimeout(() => {
                if (conversationId === currentConversationId) {
                    startNewChat();
                } else {
                    loadConversations();
                }
            }, 300);

        } catch (error) {
            alert(`Failed to delete conversation: ${error.message}`);
            items.forEach(item => item.classList.remove('deleting'));
        }
    }

    function startNewChat() {
        currentConversationId = generateConversationId();
        chatMessages.innerHTML = '';
        showWelcomeMessage();
        loadConversations();
        userInput.focus();
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message || isWaitingForResponse) return;

        isWaitingForResponse = true;
        sendBtn.disabled = true;
        userInput.value = '';

        // Display user message
        displayMessage('user', message);

        //Display thinking indicator
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message assistant thinking';
        thinkingDiv.textContent = 'Thinking...';
        chatMessages.appendChild(thinkingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const isComparisonMode = comparisonModeCheckbox.checked;

            if (isComparisonMode) {
                // Get selected models
                const selectedModels = Array.from(document.querySelectorAll('.model-checkbox:checked''))
                    .map(cb => cb.value);

                if (selectdModels.length === 0) {
                    alert('Please select at least one model');
                    thinkingDiv.remove();
                    return;
                }

                // Call comparison endpoint
                const response = await fetch(`${API_BASE}/compare`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        models: selectedModels,
                        conversation_id: currentConversationId
                    })
                });

                const data = await response.json();
                thinkingDiv.remove();

                if (data.error) {
                    displayMessage('assistant', `Error: ${data.error}`, 'system');
                } else {
                    // Display comparison results
                    displayComparison(data.responses);
                }

            } else {
                // Normal single-model mode (your existing logic)
            const response = await fetch(`${API_BASE}/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: message,
                    model: modelSelect.value,
                    conversation_id: currentConversationId
                })
            });

            const data = await response.json();

            // Remove thinking indicator
            thinkingDiv.remove()

            if (data.error) {
                displayMessage('assistant', `Error: ${data.error}`, data.model || 'system');
            } else {
                displayMessage('assistant', data.response, data.model);
            }

            // Refresh conversation list
            loadConversations();

        } catch (error) {
            thinkingDiv.remove();
            displayMessage('assistant', `Network error: ${error.message}`, 'system');
        } finally {
            isWaitingForResponse = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    function displayMessage(role, content, model = '') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        if (role === 'assistant' && model) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            metaDiv.textContent = `${model} • ${new Date().toLocaleTimeString()}`;
            contentDiv.appendChild(metaDiv);
        }

        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function displayComparison(responses) {
        const container = document.createElement('div');
        container.className = 'comparison-container';

        responses.forEach(resp => {
            const responseDiv = document.createElement('div');
            responseDiv.className = 'comparison-response';

            const modelLabel = document.createElement('div');
            modelLabel.className = 'model-label';
            modelLabel.textContent = resp.model;

            const content = document.createElement('div');
            content.className = 'response-content';
            content.textContent = resp.response;

            responseDiv.appendChild(modelLabel);
            responseDiv.appendChild(content);
            container.appendChild(responseDiv);
        })};

        chatMessages.appendChild(container);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showWelcomeMessage() {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'welcome-mesasge';
        welcomeDiv.innerHTML = `
            <h2>Welcome to Multi-LLM Relay</h2>
            <p>Start a conversation by typing a message below.</p>
            <p style="font-size: 12px; color: #999; margin-type: 8px;">
                Tip: Use Ctrl+K (Cmd+K on Mac) to start a new chat
            </p>
        `;
        chatMessages.appendChild(welcomeDiv);
    }

    function applyFilters(conversations) {
        let filtered = [...conversations];

        // Apply search filter
        if (currentFilters.search) {
            const searchLower = currentFilters.search.toLowerCase();
            filtered = filtered.filter(conv =>
                conv.conversation_id.toLowerCase().includes(searchLower)
            );
        }

        // Apply date filter
        if (currentFilters.date !== 'all') {
            const now = new Date();
            const cutoffDate = new Date();

            switch (currentFilters.date) {
                case 'today':
                    cutoffDate.setHours(0, 0, 0, 0);
                    break;
                case 'week':
                    cutoffDate.setDate(now.getDate() - 7);
                    break;
                case 'month':
                    cutoffDate.setMonth(now.getMonth() - 1);
                    break;
            }

            filtered = filtered.filter(conv => {
                const convDate = new Date(conv.last_message_at || conv.created_at);
                return convDate >= cutoffDate;
            });
        }

        // Apply sort
        switch (currentFilters.sort) {
            case 'newest':
                filtered.sort((a,b) => {
                    const dateA = new Date(a.last_message_at || a.created_at);
                    const dateB = new Date(b.last_message_at || b.created_at);
                    return dateB - dateA;
                });
                break;
            case 'oldest':
                filtered.sort((a,b) => {
                    const dateA = new Date(a.last_message_at || a.created_at);
                    const dateB = new Date(b.last_message_at || b.created_at);
                    return dateA - dateB;
                });
                break;
            case 'most_messages':
                filtered.sort((a,b) => b.message_count - a.message_count);
                break;
        }

        return filtered;
    }

    function updateClearFiltersButton() {
        const clearBtn = document.getElementById('clearFilters');
        const hasActiveFilters = currentFilters.search !== '' ||
                                 currentFilters.date !== 'all' ||
                                 currentFilters.sort !== 'newest';
        clearBtn.style.display = hasActiveFilters ? 'block' : 'none';
    }

    function clearAllFilters() {
        currentFilters = {
            search: '',
            date: 'all',
            sort: 'newest'
        };

        document.getElementById('searchInput').value = '';
        document.getElementById('dateFilter').value = 'all';
        document.getElementById('sortFilter').value = 'newest';

        updateClearFiltersButton();
        renderConversationList(applyFilters(allConversations));
    }

    function addComparisonToUI(responses) {
        const container = document.createElement('div');
        container.className = 'comparison-container';

        responses.forEach(resp => {
            const responseDiv = document.createElement('div');
            responseDiv.className = 'comparison-response';

            const modelLabel = document.createElement('div');
            modelLabel.className = 'model-label';
            modelLabel.textContent = resp.model;

            const content = document.createElement('div');
            content.className = 'response-content';
            content.textContent = resp.response;

            responseDiv.appendChild(modelLabel);
            responseDiv.appendChild(content);
            container.appendChild(responseDiv);
        });

        chatMessages.appendChild(container);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
