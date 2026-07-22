const API_BASE_URL = '';

let currentMode = 'recommend'; // 'recommend' or 'search'

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`mode-${mode}`).classList.add('active');

    // Update placeholder and hint
    const input = document.getElementById('search-input');
    const hint = document.getElementById('search-hint');

    if (mode === 'recommend') {
        input.placeholder = "Describe the book you're looking for... (e.g., 'future with AI')";
        hint.textContent = "Powered by Semantic Search - Finds books by meaning";
    } else {
        input.placeholder = "Search by title or author... (e.g., 'Game of thrones')";
        hint.textContent = "Powered by Keyword Search - Finds exact matches";
    }
}

async function performSearch() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;

    // UI Loading State
    const btnText = document.getElementById('btn-text');
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('results-container');

    btnText.classList.add('hidden');
    loader.classList.remove('hidden');
    resultsContainer.innerHTML = ''; // Clear previous

    try {
        let endpoint = currentMode === 'recommend' ? '/recommend' : '/search';
        // Note: /recommend uses ?query=, /search uses ?q=
        const paramName = currentMode === 'recommend' ? 'query' : 'q';

        const response = await fetch(`${API_BASE_URL}${endpoint}?${paramName}=${encodeURIComponent(query)}`);

        if (!response.ok) {
            throw new Error('API Request failed');
        }

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
    // For now, just log or simple alert, or maybe expand card.
    // Ideally user would want more info, but our API currently returns limited info.
    // If we had a /books/{isbn} endpoint, we could fetch details here.
    console.log("Clicked book:", book);
    // Future enhancement: Open modal with details
}

// Allow Enter key to search
document.getElementById('search-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        performSearch();
    }
});

// Load random books on startup
window.addEventListener('DOMContentLoaded', fetchRandomBooks);
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
            // Optional: show details
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
        // Currently showing full, switch to short
        shortText.classList.remove('hidden');
        fullText.classList.add('hidden');
        btn.textContent = 'Show More';
    } else {
        // Currently showing short, switch to full
        shortText.classList.add('hidden');
        fullText.classList.remove('hidden');
        btn.textContent = 'Show Less';
    }
}
