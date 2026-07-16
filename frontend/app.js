const API_BASE_URL = '';

// ── Search History (Most Searched) ───────────────────────────────
const HISTORY_KEY = 'vv_search_history';

function trackSearch(query) {
    const raw = localStorage.getItem(HISTORY_KEY);
    const history = raw ? JSON.parse(raw) : {};
    history[query] = (history[query] || 0) + 1;
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    renderPopularQueries();
}

function renderPopularQueries() {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return;
    const history = JSON.parse(raw);
    const sorted = Object.entries(history)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8);

    if (sorted.length === 0) return;

    const section = document.getElementById('popular-queries-section');
    const list = document.getElementById('popular-queries-list');
    section.classList.remove('hidden');
    list.innerHTML = '';

    sorted.forEach(([query, count]) => {
        const chip = document.createElement('button');
        chip.className = 'query-chip';
        chip.innerHTML = `${query} <span class="chip-count">${count}</span>`;
        chip.onclick = () => {
            document.getElementById('search-input').value = query;
            performSearch();
        };
        list.appendChild(chip);
    });
}

function clearSearchHistory() {
    localStorage.removeItem(HISTORY_KEY);
    document.getElementById('popular-queries-section').classList.add('hidden');
    document.getElementById('popular-queries-list').innerHTML = '';
}

// Load history + wire Enter key on startup
window.addEventListener('DOMContentLoaded', () => {
    fetchRandomBooks();
    renderPopularQueries();
    document.getElementById('search-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') performSearch();
    });
});

async function performSearch() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;

    trackSearch(query);  // ← save to history

    const btnText = document.getElementById('btn-text');
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('results-container');

    btnText.classList.add('hidden');
    loader.classList.remove('hidden');
    resultsContainer.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('API Request failed');
        const data = await response.json();
        renderResults(data);

    } catch (error) {
        console.error("Error:", error);
        resultsContainer.innerHTML = `
            <div class="empty-state" style="color: #ff7b72;">
                <p>Something went wrong. Is the backend running?</p>
                <p style="font-size: 0.9rem; margin-top:0.5rem;">${error.message}</p>
            </div>
        `;
    } finally {
        btnText.classList.remove('hidden');
        loader.classList.add('hidden');
    }
}

function renderResults(books) {
    const container = document.getElementById('results-container');

    if (!books || books.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No books found. Try a different query.</p>
            </div>
        `;
        return;
    }

    books.forEach((book, index) => {
        const card = document.createElement('div');
        card.className = 'book-card';
        card.style.animationDelay = `${index * 0.05}s`;

        const scoreHtml = book.score
            ? `<div class="book-score">Match: ${(book.score * 100).toFixed(0)}%</div>`
            : '';

        // Safely handle missing year/isbn
        const year = book.year || 'Unknown Year';

        const posterHtml = book.poster_url
            ? `<div class="book-poster-container"><img src="${book.poster_url}" alt="Cover" class="book-poster" onerror="this.src='https://via.placeholder.com/150x220?text=No+Cover'"></div>`
            : '<div class="book-poster-placeholder">No Cover</div>';

        const moreDetailsHtml = book.book_url
            ? `<a href="${book.book_url}" target="_blank" class="more-details-btn">More Details</a>`
            : '';

        card.innerHTML = `
            ${posterHtml}
            <div class="book-info">
                <div class="book-title">${book.title}</div>
                <div class="book-author">by ${book.author}</div>
                <div class="book-meta">${year} • ISBN: ${book.isbn}</div>
                
                <div class="book-description">
                    ${(() => {
                const desc = book.description || 'No description available.';
                if (desc.length > 400) {
                    return `
                                <span class="desc-short">${desc.substring(0, 400)}...</span>
                                <span class="desc-full hidden">${desc}</span>
                                <button class="show-more-btn" onclick="toggleDescription(event, this)">Show More</button>
                            `;
                }
                return desc;
            })()}
                </div>

                <div class="card-footer">
                    ${scoreHtml}
                    ${moreDetailsHtml}
                </div>
            </div>
        `;

        card.onclick = (e) => {
            // Prevent clicking the card when clicking the button
            if (e.target.closest('.more-details-btn')) return;
            showBookDetails(book);
        };
        container.appendChild(card);
    });
}

function showBookDetails(book) {
    console.log("Clicked book:", book);
}

async function fetchRandomBooks() {
    const list = document.getElementById('random-books-list');
    const section = document.getElementById('random-books-section');

    try {
        const response = await fetch(`${API_BASE_URL}/random-books`);
        if (!response.ok) throw new Error('Failed to fetch random books');

        const books = await response.json();
        if (books && books.length > 0) {
            section.classList.remove('hidden');
            renderBookList(books, list);
        }
    } catch (e) {
        console.error("Could not load random books:", e);
    }
}

function renderBookList(books, container) {
    container.innerHTML = '';
    books.forEach((book, index) => {
        const card = document.createElement('div');
        card.className = 'book-card';
        card.style.animationDelay = `${index * 0.1}s`;

        const scoreHtml = book.score
            ? `<div class="book-score">Match: ${(book.score * 100).toFixed(0)}%</div>`
            : '';

        // Safely handle missing year/isbn
        const year = book.year || 'Unknown Year';

        const posterHtml = book.poster_url
            ? `<div class="book-poster-container"><img src="${book.poster_url}" alt="Cover" class="book-poster" onerror="this.src='https://via.placeholder.com/150x220?text=No+Cover'"></div>`
            : '<div class="book-poster-placeholder">No Cover</div>';

        const moreDetailsHtml = book.book_url
            ? `<a href="${book.book_url}" target="_blank" class="more-details-btn">Details</a>`
            : '';

        // Simplified description for cards
        const desc = book.description || 'No description available.';
        const shortDesc = desc.length > 100 ? desc.substring(0, 100) + '...' : desc;

        card.innerHTML = `
            ${posterHtml}
            <div class="book-info">
                <div class="book-title">${book.title}</div>
                <div class="book-author">by ${book.author}</div>
                <div class="book-meta">${year}</div>
                
                <div class="book-description">
                     ${shortDesc}
                </div>

                <div class="card-footer">
                    ${scoreHtml}
                    ${moreDetailsHtml}
                </div>
            </div>
        `;

        card.onclick = (e) => {
            if (e.target.closest('.more-details-btn')) return;
        };
        container.appendChild(card);
    });
}

function toggleDescription(event, btn) {
    event.stopPropagation();
    const container = btn.closest('.book-description');
    const shortText = container.querySelector('.desc-short');
    const fullText = container.querySelector('.desc-full');

    if (shortText.classList.contains('hidden')) {
        shortText.classList.remove('hidden');
        fullText.classList.add('hidden');
        btn.textContent = 'Show More';
    } else {
        shortText.classList.add('hidden');
        fullText.classList.remove('hidden');
        btn.textContent = 'Show Less';
    }
}

// ── Chat Logic ────────────────────────────────────────────────────────────────

let chatHistory = [];  // [{role: 'user'|'assistant', content: '...'}]
let chatOpen = false;

function toggleChat() {
    const panel = document.getElementById('chat-panel');
    chatOpen = !chatOpen;

    if (chatOpen) {
        panel.classList.remove('hidden');
        document.getElementById('chat-input').focus();
    } else {
        panel.classList.add('hidden');
    }
}

function handleChatKey(event) {
    // Send on Enter (without Shift for newline)
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Show user bubble
    appendBubble('user', message);

    // Disable send button
    const sendBtn = document.getElementById('chat-send-btn');
    const sendIcon = document.getElementById('chat-send-icon');
    const chatLoader = document.getElementById('chat-loader');
    sendBtn.disabled = true;
    sendIcon.classList.add('hidden');
    chatLoader.classList.remove('hidden');

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, history: chatHistory }),
        });

        removeTypingIndicator(typingId);

        if (!response.ok) {
            const err = await response.json();
            appendBubble('assistant', `⚠️ ${err.detail || 'Something went wrong. Please try again.'}`);
            return;
        }

        const data = await response.json();

        // Show reply + retrieved books
        appendAssistantBubble(data.reply, data.books || []);

        // Update history for multi-turn
        chatHistory.push({ role: 'user', content: message });
        chatHistory.push({ role: 'assistant', content: data.reply });

    } catch (err) {
        removeTypingIndicator(typingId);
        appendBubble('assistant', '⚠️ Could not reach the server. Is the backend running?');
    } finally {
        sendBtn.disabled = false;
        sendIcon.classList.remove('hidden');
        chatLoader.classList.add('hidden');
    }
}

function appendBubble(role, text) {
    const messages = document.getElementById('chat-messages');
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    bubble.textContent = text;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
}

function appendAssistantBubble(reply, books) {
    const messages = document.getElementById('chat-messages');
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble assistant';

    // Reply text
    const replyEl = document.createElement('p');
    replyEl.textContent = reply;
    bubble.appendChild(replyEl);

    // Book pills
    if (books.length > 0) {
        const booksEl = document.createElement('div');
        booksEl.className = 'chat-books';
        books.slice(0, 5).forEach(book => {
            const pill = document.createElement('div');
            pill.className = 'chat-book-pill';
            pill.textContent = `${book.title} — ${book.author || 'Unknown'}`;
            booksEl.appendChild(pill);
        });
        bubble.appendChild(booksEl);
    }

    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
}

function showTypingIndicator() {
    const messages = document.getElementById('chat-messages');
    const bubble = document.createElement('div');
    const id = 'typing-' + Date.now();
    bubble.id = id;
    bubble.className = 'chat-bubble typing';
    bubble.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
