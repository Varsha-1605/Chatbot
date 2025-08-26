// Enhanced Chatbot JavaScript with Document Upload Support
class ChatbotInterface {
    constructor() {
        this.messageCount = 0;
        this.isTyping = false;
        this.sessionId = null;
        this.hasDocument = false;
        this.supportedFormats = {};
        this.maxFileSize = 10 * 1024 * 1024; // 10MB default
        
        this.initializeElements();
        this.bindEvents();
        this.loadSupportedFormats();
        this.loadChatHistory();
        this.checkDocumentContext();
    }
    
    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatForm = document.getElementById('chatForm');
        this.messageCountElement = document.getElementById('messageCount');
        this.sessionIdElement = document.getElementById('sessionId');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.sentimentIndicator = document.getElementById('sentimentIndicator');
        this.loadingModal = document.getElementById('loadingModal');
        this.fileInput = document.getElementById('fileInput');
        this.documentStatus = document.getElementById('documentStatus');
    }
    
    bindEvents() {
        // Form submission
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Enter key handling
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize input
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });
        
        // File input handling
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => {
                this.handleFileSelect(e);
            });
        }
        
        // Drag and drop support
        this.setupDragAndDrop();
    }
    
    setupDragAndDrop() {
        const chatContainer = document.querySelector('.lg\\:col-span-3 .bg-white');
        if (!chatContainer) return;
        
        chatContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            chatContainer.classList.add('border-blue-300', 'bg-blue-50');
        });
        
        chatContainer.addEventListener('dragleave', (e) => {
            e.preventDefault();
            chatContainer.classList.remove('border-blue-300', 'bg-blue-50');
        });
        
        chatContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            chatContainer.classList.remove('border-blue-300', 'bg-blue-50');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });
    }
    
    async loadSupportedFormats() {
        try {
            const response = await fetch('/api/supported-formats');
            const data = await response.json();
            this.supportedFormats = data.formats;
            this.maxFileSize = data.max_file_size_mb * 1024 * 1024;
        } catch (error) {
            console.error('Error loading supported formats:', error);
        }
    }
    
    async checkDocumentContext() {
        try {
            const response = await fetch('/api/document-info');
            const data = await response.json();
            this.hasDocument = data.has_document;
            this.updateDocumentStatus(data);
        } catch (error) {
            console.error('Error checking document context:', error);
        }
    }
    
    updateDocumentStatus(docInfo) {
        const statusElement = this.documentStatus || this.createDocumentStatusElement();
        
        if (docInfo.has_document) {
            statusElement.innerHTML = `
                <div class="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div class="flex items-center">
                        <i class="fas fa-file-alt text-green-600 mr-2"></i>
                        <span class="text-sm text-green-800">Document loaded</span>
                    </div>
                    <button onclick="clearDocument()" class="text-green-600 hover:text-green-800 text-xs">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            this.hasDocument = true;
        } else {
            statusElement.innerHTML = `
                <div class="flex items-center justify-between p-3 bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors cursor-pointer" onclick="document.getElementById('fileInput').click()">
                    <div class="flex items-center">
                        <i class="fas fa-upload text-gray-400 mr-2"></i>
                        <span class="text-sm text-gray-600">Upload document</span>
                    </div>
                    <i class="fas fa-plus text-gray-400"></i>
                </div>
            `;
            this.hasDocument = false;
        }
    }
    
    createDocumentStatusElement() {
        const sidebar = document.querySelector('.lg\\:col-span-1');
        if (!sidebar) return null;
        
        const statusDiv = document.createElement('div');
        statusDiv.id = 'documentStatus';
        statusDiv.className = 'mb-4';
        
        sidebar.insertBefore(statusDiv, sidebar.firstChild);
        this.documentStatus = statusDiv;
        return statusDiv;
    }
    
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.handleFileUpload(file);
        }
    }
    
    async handleFileUpload(file) {
        // Validate file size
        if (file.size > this.maxFileSize) {
            showNotification(`File size exceeds ${this.maxFileSize / 1024 / 1024}MB limit`, 'error');
            return;
        }
        
        // Check if file type is supported
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        const isSupported = Object.values(this.supportedFormats).some(formats => formats.includes(fileExt));
        
        if (!isSupported) {
            showNotification('File format not supported', 'error');
            return;
        }
        
        this.showLoadingModal('Processing document...');
        
        try {
            // Convert file to base64
            const fileData = await this.fileToBase64(file);
            
            const response = await fetch('/api/upload-document', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_data: fileData,
                    filename: file.name
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                // Add document upload message to chat
                this.addDocumentUploadMessage(file.name, result.file_info);
                
                // Add bot response about document
                if (result.bot_response) {
                    this.addMessage(result.bot_response.message, 'bot', result.bot_response);
                }
                
                // Update document status
                this.updateDocumentStatus({ has_document: true });
                
                showNotification('Document uploaded successfully!', 'success');
                
            } else {
                throw new Error(result.error || 'Upload failed');
            }
            
        } catch (error) {
            console.error('Error uploading document:', error);
            showNotification('Failed to upload document: ' + error.message, 'error');
        } finally {
            this.hideLoadingModal();
            // Clear file input
            if (this.fileInput) {
                this.fileInput.value = '';
            }
        }
    }
    
    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                // Remove the data:image/jpeg;base64, part
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = error => reject(error);
        });
    }
    
    addDocumentUploadMessage(filename, fileInfo) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'flex items-start space-x-3 message-slide-in';
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const fileSize = this.formatFileSize(fileInfo.size);
        
        messageDiv.innerHTML = `
            <div class="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm">
                <i class="fas fa-file-upload"></i>
            </div>
            <div class="bg-blue-100 border border-blue-200 p-4 rounded-lg shadow-sm max-w-md">
                <div class="flex items-center mb-2">
                    <i class="fas fa-file-alt text-blue-600 mr-2"></i>
                    <span class="font-medium text-blue-800">Document Uploaded</span>
                </div>
                <div class="text-sm text-blue-700">
                    <p><strong>File:</strong> ${filename}</p>
                    <p><strong>Size:</strong> ${fileSize}</p>
                    <p><strong>Type:</strong> ${fileInfo.file_type}</p>
                    ${fileInfo.word_count ? `<p><strong>Words:</strong> ${fileInfo.word_count.toLocaleString()}</p>` : ''}
                </div>
                <span class="text-xs text-blue-600 mt-2 block">${timestamp}</span>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        this.updateMessageCount();
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    showLoadingModal(message = 'Processing...') {
        if (this.loadingModal) {
            this.loadingModal.querySelector('span').textContent = message;
            this.loadingModal.classList.remove('hidden');
            this.loadingModal.classList.add('flex');
        }
    }
    
    hideLoadingModal() {
        if (this.loadingModal) {
            this.loadingModal.classList.add('hidden');
            this.loadingModal.classList.remove('flex');
        }
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        
        // Show typing indicator
        this.showTyping();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Add bot response with enhanced formatting
                this.addMessage(data.response, 'bot', data);
                
                // Update sentiment indicator
                if (data.sentiment) {
                    this.updateSentimentIndicator(data.sentiment);
                }
            } else {
                throw new Error(data.error || 'Unknown error occurred');
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', { intent: 'error' });
            showNotification('Failed to send message. Please try again.', 'error');
        } finally {
            this.hideTyping();
        }
    }
    
    /**
     * Enhanced text formatting function
     */
    formatBotMessage(content) {
        // Convert markdown-style formatting to HTML
        let formattedContent = content
            // Bold text: **text** or __text__
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/__(.*?)__/g, '<strong>$1</strong>')
            
            // Italic text: *text* or _text_
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/_(.*?)_/g, '<em>$1</em>')
            
            // Code blocks: ```code```
            .replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-100 p-2 rounded text-sm font-mono overflow-x-auto"><code>$1</code></pre>')
            
            // Inline code: `code`
            .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">$1</code>')
            
            // Links: [text](url)
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="text-blue-600 hover:underline">$1</a>');
        
        // Handle bullet points and lists
        formattedContent = this.formatLists(formattedContent);
        
        // Handle line breaks and paragraphs
        formattedContent = this.formatParagraphs(formattedContent);
        
        return formattedContent;
    }
    
    /**
     * Format bullet points and numbered lists
     */
    formatLists(content) {
        const lines = content.split('\n');
        let formattedLines = [];
        let inList = false;
        let listType = null;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            const bulletMatch = line.match(/^[-*•]\s+(.+)/);
            const numberedMatch = line.match(/^\d+\.\s+(.+)/);
            
            if (bulletMatch) {
                if (!inList || listType !== 'ul') {
                    if (inList) formattedLines.push(`</${listType}>`);
                    formattedLines.push('<ul class="list-disc list-inside space-y-1 my-2 ml-4">');
                    inList = true;
                    listType = 'ul';
                }
                formattedLines.push(`<li class="text-gray-800">${bulletMatch[1]}</li>`);
            } else if (numberedMatch) {
                if (!inList || listType !== 'ol') {
                    if (inList) formattedLines.push(`</${listType}>`);
                    formattedLines.push('<ol class="list-decimal list-inside space-y-1 my-2 ml-4">');
                    inList = true;
                    listType = 'ol';
                }
                formattedLines.push(`<li class="text-gray-800">${numberedMatch[1]}</li>`);
            } else {
                if (inList) {
                    formattedLines.push(`</${listType}>`);
                    inList = false;
                    listType = null;
                }
                if (line) {
                    formattedLines.push(line);
                }
            }
        }
        
        if (inList) {
            formattedLines.push(`</${listType}>`);
        }
        
        return formattedLines.join('\n');
    }
    
    /**
     * Format paragraphs and line breaks
     */
    formatParagraphs(content) {
        const paragraphs = content.split('\n\n');
        
        return paragraphs
            .map(paragraph => {
                const trimmed = paragraph.trim();
                if (!trimmed) return '';
                
                if (trimmed.startsWith('<')) {
                    return trimmed;
                }
                
                const withBreaks = trimmed.replace(/\n/g, '<br>');
                return `<p class="mb-2 text-gray-800 leading-relaxed">${withBreaks}</p>`;
            })
            .filter(p => p)
            .join('');
    }
    
    addMessage(content, sender, data = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex items-start space-x-3 message-slide-in ${sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`;
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        if (sender === 'user') {
            messageDiv.innerHTML = `
                <div class="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm">
                    <i class="fas fa-user"></i>
                </div>
                <div class="bg-blue-500 text-white p-4 rounded-lg shadow-sm max-w-md">
                    <div class="text-white">${this.escapeHtml(content)}</div>
                    <span class="text-xs opacity-75 mt-2 block">${timestamp}</span>
                </div>
            `;
        } else {
            const intentIcon = this.getIntentIcon(data.intent || 'general');
            const formattedContent = this.formatBotMessage(content);
            const hasDocContext = data.has_document_context;
            
            messageDiv.innerHTML = `
                <div class="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="bg-white p-4 rounded-lg shadow-sm max-w-2xl border border-gray-200">
                    <div class="flex items-center mb-2">
                        <i class="fas ${intentIcon} text-primary mr-2 text-xs"></i>
                        <span class="text-xs text-gray-500 uppercase tracking-wide">${data.intent || 'response'}</span>
                        ${hasDocContext ? '<span class="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full"><i class="fas fa-file-alt mr-1"></i>From Document</span>' : ''}
                    </div>
                    <div class="prose prose-sm max-w-none">
                        ${formattedContent}
                    </div>
                    <div class="flex items-center justify-between mt-3 pt-2 border-t border-gray-100">
                        <span class="text-xs text-gray-500">${timestamp}</span>
                        <div class="flex items-center space-x-2">
                            ${data.sentiment ? this.getSentimentBadge(data.sentiment) : ''}
                            <button onclick="copyMessage(this)" class="text-gray-400 hover:text-gray-600 text-xs p-1" title="Copy message">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        this.updateMessageCount();
    }
    
    getSentimentBadge(sentiment) {
        const { label } = sentiment;
        let badgeClass, icon;
        
        switch (label) {
            case 'positive':
                badgeClass = 'bg-green-100 text-green-800';
                icon = 'fa-smile';
                break;
            case 'negative':
                badgeClass = 'bg-red-100 text-red-800';
                icon = 'fa-frown';
                break;
            default:
                badgeClass = 'bg-gray-100 text-gray-800';
                icon = 'fa-meh';
        }
        
        return `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs ${badgeClass}">
                    <i class="fas ${icon} mr-1"></i>
                    ${label}
                </span>`;
    }
    
    getIntentIcon(intent) {
        const icons = {
            'greeting': 'fa-hand-wave',
            'goodbye': 'fa-wave-square',
            'question': 'fa-question-circle',
            'help_request': 'fa-life-ring',
            'thanks': 'fa-heart',
            'error': 'fa-exclamation-triangle',
            'document_query': 'fa-file-search',
            'document_analysis': 'fa-file-alt',
            'document_uploaded': 'fa-file-upload',
            'general': 'fa-comment'
        };
        return icons[intent] || 'fa-comment';
    }
    
    showTyping() {
        this.isTyping = true;
        this.sendButton.disabled = true;
        this.sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'flex items-start space-x-3 message-slide-in';
        typingDiv.innerHTML = `
            <div class="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm">
                <i class="fas fa-robot"></i>
            </div>
            <div class="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
                <div class="flex items-center space-x-2">
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <span class="text-sm text-gray-500">AI is thinking...</span>
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        this.sendButton.disabled = false;
        this.sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    updateSentimentIndicator(sentiment) {
        if (!this.sentimentIndicator) return;
        
        const { label, polarity } = sentiment;
        let emoji, text, color;
        
        switch (label) {
            case 'positive':
                emoji = '😊';
                text = 'Positive';
                color = 'text-green-600';
                break;
            case 'negative':
                emoji = '😟';
                text = 'Negative';
                color = 'text-red-600';
                break;
            default:
                emoji = '😐';
                text = 'Neutral';
                color = 'text-gray-600';
        }
        
        this.sentimentIndicator.innerHTML = `
            <div class="text-2xl mb-2">${emoji}</div>
            <div class="text-sm ${color}">${text}</div>
            <div class="text-xs text-gray-500 mt-1">${(polarity * 100).toFixed(0)}%</div>
        `;
    }
    
    updateMessageCount() {
        this.messageCount++;
        if (this.messageCountElement) {
            this.messageCountElement.textContent = Math.floor(this.messageCount / 2);
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    async loadChatHistory() {
        try {
            const response = await fetch('/api/history');
            const history = await response.json();
            
            // Clear existing messages except welcome message
            const welcomeMessage = this.chatMessages.querySelector('.flex');
            this.chatMessages.innerHTML = '';
            if (welcomeMessage) {
                this.chatMessages.appendChild(welcomeMessage);
            }
            
            // Add history messages
            history.forEach(item => {
                this.addMessage(item.user_message, 'user');
                this.addMessage(item.bot_response, 'bot', { timestamp: item.timestamp });
            });
            
            this.scrollToBottom();
            
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global functions for document management and quick actions
function sendQuickMessage(message) {
    if (window.chatbot) {
        window.chatbot.messageInput.value = message;
        window.chatbot.sendMessage();
    }
}

async function clearDocument() {
    if (confirm('Are you sure you want to clear the current document?')) {
        try {
            const response = await fetch('/api/clear-document', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                window.chatbot.updateDocumentStatus({ has_document: false });
                window.chatbot.hasDocument = false;
                showNotification('Document context cleared', 'success');
            } else {
                throw new Error(result.message || 'Failed to clear document');
            }
            
        } catch (error) {
            console.error('Error clearing document:', error);
            showNotification('Error clearing document', 'error');
        }
    }
}

function clearChat() {
    if (confirm('Are you sure you want to clear the chat? This will also clear any uploaded document.')) {
        fetch('/api/clear_session', { method: 'POST' })
            .then(response => response.json())
            .then(() => {
                // Clear document context as well
                if (window.chatbot.hasDocument) {
                    clearDocument();
                }
                location.reload();
            })
            .catch(error => {
                showNotification('Error clearing chat', 'error');
            });
    }
}

function downloadChat() {
    const messages = document.querySelectorAll('#chatMessages .message-slide-in');
    let chatText = 'Chat Export\n' + '='.repeat(50) + '\n\n';
    
    messages.forEach(message => {
        const textEl = message.querySelector('.prose, .text-white');
        const text = textEl?.textContent || '';
        const time = message.querySelector('.text-xs')?.textContent || '';
        const sender = message.querySelector('.fa-user') ? 'User' : 'AI';
        
        if (text && !text.includes('AI is thinking') && !text.includes('Document Uploaded')) {
            chatText += `[${time}] ${sender}: ${text}\n\n`;
        }
    });
    
    const blob = new Blob([chatText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

function toggleVoiceInput() {
    showNotification('Voice input not yet implemented', 'info');
}

// Copy message functionality
function copyMessage(button) {
    const messageContent = button.closest('.bg-white').querySelector('.prose').textContent;
    navigator.clipboard.writeText(messageContent).then(() => {
        showNotification('Message copied!', 'success');
    }).catch(() => {
        // Fallback for browsers that don't support clipboard API
        const textArea = document.createElement('textarea');
        textArea.value = messageContent;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification('Message copied!', 'success');
    });
}

// Document upload helper function
function uploadDocument() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.click();
    }
}

// Initialize chatbot
function initializeChatbot() {
    window.chatbot = new ChatbotInterface();
    
    // Add document upload quick action if not already present
    setTimeout(() => {
        addDocumentQuickActions();
    }, 100);
}

// Add document-specific quick actions
function addDocumentQuickActions() {
    const quickActionsContainer = document.querySelector('.space-y-2');
    if (!quickActionsContainer || document.getElementById('document-quick-actions')) return;
    
    const documentActions = document.createElement('div');
    documentActions.id = 'document-quick-actions';
    documentActions.className = 'border-t border-gray-200 pt-2 mt-2';
    
    documentActions.innerHTML = `
        <div class="text-xs text-gray-500 uppercase tracking-wide mb-2">Document Actions</div>
        <button onclick="uploadDocument()" 
                class="w-full text-left p-2 rounded-lg hover:bg-gray-50 transition-colors text-sm">
            📄 Upload Document
        </button>
        <button onclick="sendQuickMessage('Summarize this document')" 
                class="w-full text-left p-2 rounded-lg hover:bg-gray-50 transition-colors text-sm ${window.chatbot && window.chatbot.hasDocument ? '' : 'opacity-50 cursor-not-allowed'}"
                ${window.chatbot && window.chatbot.hasDocument ? '' : 'disabled'}>
            📋 Summarize Document
        </button>
        <button onclick="sendQuickMessage('What are the key points of this document?')" 
                class="w-full text-left p-2 rounded-lg hover:bg-gray-50 transition-colors text-sm ${window.chatbot && window.chatbot.hasDocument ? '' : 'opacity-50 cursor-not-allowed'}"
                ${window.chatbot && window.chatbot.hasDocument ? '' : 'disabled'}>
            🗂️ Extract Key Points
        </button>
    `;
    quickActionsContainer.appendChild(documentActions);
}