const API_BASE = '';

let accessToken = localStorage.getItem('accessToken') || '';
let currentUser = localStorage.getItem('currentUser') || '';
let currentRole = localStorage.getItem('currentRole') || '';
let currentUserId = parseInt(localStorage.getItem('currentUserId') || '0');

document.addEventListener('DOMContentLoaded', () => {
    loadFilteredProducts();
    loadCategories();
    loadBrands();
    loadRecommendations();
    updateHeader();
    updateCartCount();
    loadTheme();
    setLang(currentLang);
    loadStoreBranding();
    initViewHistory();
    initComparison();
    initDeferred();
    initNotifications();
    loadAdBanners();
    checkWishlistAlerts();
    const saved = localStorage.getItem('lastSection');
    if (saved && document.getElementById(saved)) {
        if (saved === 'product-detail') {
            const pid = localStorage.getItem('lastProductId');
            if (pid) { showProductDetail(pid); return; }
        }
        showSection(saved);
    }
});

/* ═══ 1. Scroll to Top ═══ */
(function initScrollToTop() {
    const btn = document.createElement('button');
    btn.className = 'scroll-top';
    btn.id = 'scroll-top-btn';
    btn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    btn.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
    document.body.appendChild(btn);
    window.addEventListener('scroll', () => {
        btn.classList.toggle('visible', window.scrollY > 400);
    });
})();

/* ═══ 2. Product Skeleton ═══ */
function skeletonProducts(n) {
    let html = '';
    for (let i = 0; i < n; i++) {
        html += `<div class="skeleton-product"><div class="skeleton skeleton-img"></div><div class="skeleton-body"><div class="skeleton skeleton-text" style="width:60%"></div><div class="skeleton skeleton-text" style="width:80%"></div><div class="skeleton skeleton-text" style="width:40%"></div></div></div>`;
    }
    return html;
}

/* ═══ 5. Cart Count Pulse (on page load) ═══ */
setTimeout(() => { if (accessToken) updateCartCountPulse(); }, 500);

/* ═══ 6. Enter on Forms ═══ */
document.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const el = e.target;
    if (!el) return;
    const id = el.id || '';
    if (id === 'search-input' || id === 'promo-input' || id === 'promo-input-admin') { e.preventDefault(); return; }
    if (id === 'auth-login' || id === 'auth-password') { e.preventDefault(); login(); return; }
    if (id === 'reg-login' || id === 'reg-password' || id === 'reg-password2') { e.preventDefault(); register(); return; }
    if (id === 'pw-old' || id === 'pw-new' || id === 'pw-confirm') { e.preventDefault(); changePassword(); return; }
    if (id === 'pf-fullname' || id === 'pf-email' || id === 'pf-phone' || id === 'pf-address') { e.preventDefault(); saveProfile(); return; }
    if (id === 'review-text') { e.preventDefault(); submitReview(); return; }
    if (el.closest('.promo-row')) { e.preventDefault(); applyPromo(); return; }
    if (el.closest('#deferred-checkout-form')) { e.preventDefault(); placeDeferredOrder(); return; }
});

/* ═══ 7. Copy Promo Code ═══ */
function copyPromoCode(el, code) {
    navigator.clipboard.writeText(code).then(() => {
        el.classList.add('copied');
        el.textContent = '✓ Скопировано';
        setTimeout(() => { el.classList.remove('copied'); el.textContent = code; }, 1500);
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = code; document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
        el.classList.add('copied');
        el.textContent = '✓ Скопировано';
        setTimeout(() => { el.classList.remove('copied'); el.textContent = code; }, 1500);
    });
}

/* ═══ 9. Lazy Loading ═══ */
if ('IntersectionObserver' in window) {
    const imgObs = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                const img = e.target;
                if (img.dataset.src) { img.src = img.dataset.src; img.removeAttribute('data-src'); }
                imgObs.unobserve(img);
            }
        });
    }, { rootMargin: '200px' });
    window._lazyImgObserver = imgObs;
}

/* ═══ 13. Recently Viewed (in profile) ═══ */
function renderRecentlyViewed() {
    const history = JSON.parse(localStorage.getItem('myshop-history') || '[]');
    if (!history.length) return '';
    return `<div class="profile-form-card" id="recently-viewed-card">
        <h3>Недавно просмотренные</h3>
        <div class="recent-viewed">
            ${history.slice(0, 10).map(p => `
                <div class="recent-viewed-item" onclick="showProductDetail(${p.id})">
                    <img src="${p.image}" alt="${p.name}" loading="lazy">
                    <span>${p.name}</span>
                </div>`).join('')}
        </div>
    </div>`;
}

const _origLoadProfile2 = window.loadProfile;
window.loadProfile = async function() {
    if (_origLoadProfile2) await _origLoadProfile2();
    const profileLayout = document.querySelector('.profile-layout');
    if (profileLayout && !document.getElementById('recently-viewed-card')) {
        const html = renderRecentlyViewed();
        if (html) {
            const tmp = document.createElement('div');
            tmp.innerHTML = html;
            profileLayout.appendChild(tmp.firstElementChild);
        }
    }
};

/* ═══ 14. Mini Cart ═══ */
async function updateMiniCart() {
    const dropdown = document.getElementById('mini-cart-dropdown');
    if (!dropdown) return;
    if (!accessToken) { dropdown.innerHTML = '<div style="text-align:center;padding:1rem;color:var(--text-secondary);font-size:0.85rem;">Войдите, чтобы увидеть корзину</div>'; return; }
    try {
        const res = await api('/api/cart');
        if (!res.ok) throw new Error();
        const data = await res.json();
        const items = data.items || [];
        if (!items.length) { dropdown.innerHTML = '<div style="text-align:center;padding:1rem;color:var(--text-secondary);font-size:0.85rem;">Корзина пуста</div>'; return; }
        dropdown.innerHTML = items.slice(0, 4).map(item => `
            <div class="mini-cart-item">
                <img src="${item.image || '/static/img/placeholder.png'}" alt="${item.name}">
                <span class="name">${item.name}</span>
                <span class="price">${item.price.toLocaleString()} ₽</span>
            </div>`).join('') +
            `<div class="mini-cart-total"><span>Итого (${data.count} шт.)</span><span>${data.total.toLocaleString()} ₽</span></div>
             <button class="btn-sm primary" style="width:100%;margin-top:8px;" onclick="showSection('cart')">Перейти в корзину</button>`;
    } catch { dropdown.innerHTML = '<div style="text-align:center;padding:1rem;color:var(--text-secondary);">Ошибка</div>'; }
}

document.addEventListener('DOMContentLoaded', () => {
    const cartIcon = document.querySelector('.cart-icon');
    if (cartIcon) {
        const wrapper = document.createElement('div');
        wrapper.className = 'mini-cart';
        cartIcon.parentNode.insertBefore(wrapper, cartIcon);
        wrapper.appendChild(cartIcon);
        const dd = document.createElement('div');
        dd.className = 'mini-cart-dropdown';
        dd.id = 'mini-cart-dropdown';
        wrapper.appendChild(dd);
        wrapper.addEventListener('mouseenter', () => { if (accessToken) updateMiniCart(); });
    }
    if (accessToken) updateMiniCart();
});

/* ===== 1. Live Search Dropdown ===== */
let searchDropdownTimeout = null;

async function liveSearch() {
    const q = document.getElementById('search-input')?.value || '';
    const dd = document.getElementById('search-dropdown');
    if (!dd) return;
    if (q.length < 2) { dd.style.display = 'none'; return; }
    clearTimeout(searchDropdownTimeout);
    searchDropdownTimeout = setTimeout(async () => {
        try {
            const res = await api(`/api/products?search=${encodeURIComponent(q)}`);
            if (!res.ok) return;
            const products = await res.json();
            if (!products.length) { dd.style.display = 'none'; return; }
            dd.innerHTML = products.slice(0, 5).map(p =>
                `<div class="search-item" onclick="showProductDetail(${p.id});document.getElementById('search-dropdown').style.display='none';">
                    <img src="${p.image}" width="30" height="30" style="border-radius:4px;object-fit:cover;">
                    <div><strong>${p.name}</strong><br><small>${p.price.toLocaleString()} ₽</small></div>
                </div>`
            ).join('');
            dd.style.display = 'block';
        } catch {}
    }, 300);
}

document.addEventListener('click', e => {
    const dd = document.getElementById('search-dropdown');
    if (dd && !e.target.closest('.search-input-wrap')) dd.style.display = 'none';
});

/* ===== 2. Price Range Filter ===== */
function debounceSearch() {
    clearTimeout(window._searchTimeout);
    window._searchTimeout = setTimeout(() => {
        loadFilteredProducts();
        liveSearch();
    }, 300);
}

/* ===== 3. Product Comparison ===== */
let compareList = JSON.parse(localStorage.getItem('myshop-compare') || '[]');

function toggleCompareItem(productId) {
    const idx = compareList.findIndex(c => c.id === productId);
    if (idx >= 0) {
        compareList.splice(idx, 1);
        showToast(t('remove') + ' ' + t('compare'));
    } else {
        if (compareList.length >= 3) { showToast('Максимум 3 товара для сравнения', 'error'); return; }
        api(`/api/products/${productId}`).then(r => r.json()).then(p => {
            compareList.push(p);
            localStorage.setItem('myshop-compare', JSON.stringify(compareList));
            updateCompareBadge();
            showToast(t('compare') + ': ' + p.name);
        });
    }
    localStorage.setItem('myshop-compare', JSON.stringify(compareList));
    updateCompareBadge();
}

function updateCompareBadge() {
    const link = document.getElementById('compare-link');
    if (link) link.style.display = compareList.length > 0 ? '' : 'none';
}

function renderComparison() {
    const el = document.getElementById('compare-content');
    if (!compareList.length) {
        el.innerHTML = `<div class="empty-cart"><i class="fas fa-balance-scale"></i><p>${t('no_compare')}</p></div>`;
        return;
    }
    const attrs = ['price', 'brand', 'category', 'rating'];
    el.innerHTML = `<div style="overflow-x:auto;"><table class="admin-table"><thead><tr><th></th>${compareList.map(p =>
        `<th style="text-align:center;"><img src="${p.image}" style="width:80px;height:80px;border-radius:8px;object-fit:cover;"><br>${p.name}<br><button class="btn-sm danger" onclick="toggleCompareItem(${p.id});renderComparison();" style="margin-top:0.5rem;">${t('remove')}</button></th>`
    ).join('')}</tr></thead><tbody>${attrs.map(a =>
        `<tr><td style="font-weight:600;text-transform:capitalize;">${a}</td>${compareList.map(p =>
            `<td style="text-align:center;">${a === 'price' ? p.price.toLocaleString() + ' ₽' : a === 'rating' ? renderStars(p.rating) + ' ' + p.rating : p[a]}</td>`
        ).join('')}</tr>`
    ).join('')}</tbody></table></div>`;
}

function initComparison() { updateCompareBadge(); }

/* ===== 4. View History ===== */
let viewHistory = JSON.parse(localStorage.getItem('myshop-history') || '[]');

function trackViewHistory(products) {
    products.forEach(p => {
        const idx = viewHistory.findIndex(h => h.id === p.id);
        if (idx >= 0) viewHistory.splice(idx, 1);
        viewHistory.unshift({ id: p.id, name: p.name, price: p.price, image: p.image, brand: p.brand, category: p.category, rating: p.rating });
    });
    viewHistory = viewHistory.slice(0, 20);
    localStorage.setItem('myshop-history', JSON.stringify(viewHistory));
}

function initViewHistory() {}

/* ===== 5. Recommendations ===== */
async function loadRecommendations() {
    const el = document.getElementById('home-recommendations');
    if (!el) return;
    try {
        const res = await api('/api/products/recommendations?limit=6');
        if (!res.ok) throw new Error();
        const products = await res.json();
        el.innerHTML = products.map(p => `
            <div class="product-card fade-in" onclick="showProductDetail(${p.id})" style="cursor:pointer;">
                <div class="product-image"><img src="${p.image}" alt="${p.name}" loading="lazy" style="width:100%;height:100%;object-fit:cover;"></div>
                <div class="product-content">
                    <div class="product-brand">${p.brand}</div>
                    <h3 class="product-name">${p.name}</h3>
                    <div class="product-rating"><span class="stars">${renderStars(p.rating)}</span><span class="rating-value">${p.rating.toFixed(1)}</span></div>
                    <div class="product-price">${p.price.toLocaleString()} ₽</div>
                </div>
            </div>
        `).join('');
    } catch { el.innerHTML = ''; }
}

/* ===== 6. Deferred Checkout ===== */
let deferredList = JSON.parse(localStorage.getItem('myshop-deferred') || '[]');

function addToDeferred() {
    const id = window._currentProductId;
    if (!id) return;
    api(`/api/products/${id}`).then(r => r.json()).then(p => {
        if (!deferredList.some(d => d.id === p.id)) {
            deferredList.push(p);
            localStorage.setItem('myshop-deferred', JSON.stringify(deferredList));
            showToast(t('buy_later') + ': ' + p.name);
        }
    });
}

function renderDeferred() {
    const el = document.getElementById('deferred-grid');
    if (!deferredList.length) {
        el.innerHTML = `<div class="empty-cart"><i class="fas fa-clock"></i><p>${t('empty_cart')}</p></div>`;
        return;
    }
    el.innerHTML = deferredList.map(p => `
        <div class="product-card fade-in" onclick="showProductDetail(${p.id})" style="cursor:pointer;">
            <div class="product-image"><img src="${p.image}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover;"></div>
            <div class="product-content">
                <div class="product-brand">${p.brand}</div>
                <h3 class="product-name">${p.name}</h3>
                <div class="product-price">${p.price.toLocaleString()} ₽</div>
                <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
                    <button class="add-to-cart" style="flex:1;" onclick="addToCart(${p.id},event)"><i class="fas fa-shopping-cart"></i> ${t('add_cart')}</button>
                    <button class="btn-sm danger" onclick="event.stopPropagation();removeDeferred(${p.id})"><i class="fas fa-trash"></i></button>
                </div>
            </div>
        </div>
    `).join('');
}

function removeDeferred(id) {
    deferredList = deferredList.filter(d => d.id !== id);
    localStorage.setItem('myshop-deferred', JSON.stringify(deferredList));
    renderDeferred();
}

function initDeferred() {}

/* ===== 7. Brand Page ===== */
async function showBrandPage(brand) {
    showSection('brand-page');
    document.getElementById('brand-page-title').textContent = `${t('brand_page')}: ${brand}`;
    const grid = document.getElementById('brand-grid');
    grid.innerHTML = '<div class="spinner"></div>';
    try {
        const res = await api(`/api/products/brand/${encodeURIComponent(brand)}`);
        if (!res.ok) throw new Error();
        const products = await res.json();
        grid.innerHTML = products.map(p => `
            <div class="product-card fade-in" onclick="showProductDetail(${p.id})" style="cursor:pointer;">
                <div class="product-image"><img src="${p.image}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover;"></div>
                <div class="product-content">
                    <div class="product-name">${p.name}</div>
                    <div class="product-rating"><span class="stars">${renderStars(p.rating)}</span><span class="rating-value">${p.rating.toFixed(1)}</span></div>
                    <div class="product-price">${p.price.toLocaleString()} ₽</div>
                </div>
            </div>
        `).join('');
    } catch { grid.innerHTML = '<p style="color:var(--danger-color);">Ошибка</p>'; }
}

/* ===== 8. Support Chat ===== */
let chatWs = null;
let chatMode = 'support';
let storeName = 'MyShop';

function setChatMode(mode) {
    chatMode = mode;
    const supBtn = document.getElementById('chat-mode-support');
    const aiBtn = document.getElementById('chat-mode-ai');
    const input = document.getElementById('chat-input');
    if (supBtn) supBtn.classList.toggle('primary', mode === 'support');
    if (aiBtn) aiBtn.classList.toggle('primary', mode === 'ai');
    if (input) input.placeholder = mode === 'ai' ? 'Например: смени тему на cyber' : t('chat_placeholder') || 'Напишите сообщение...';
    const el = document.getElementById('chat-messages');
    if (el) {
        el.innerHTML = mode === 'ai'
            ? '<div class="chat-msg ai"><strong>ИИ:</strong> 🤖 Я ИИ-помощник. Вот что я умею:<br>• Смени тему на cyber<br>• Создай промокод SALE20 на 20%<br>• Создай баннер Летняя распродажа<br>• Включи отзывы<br>• Покажи статистику<br><br>Напишите команду или "помощь"</div>'
            : '';
    }
}

function toggleChat() {
    const w = document.getElementById('chat-window');
    w.classList.toggle('active');
    if (w.classList.contains('active') && !chatWs && chatMode === 'support') connectChat();
}

function connectChat() {
    if (!accessToken) { showToast(t('login'), 'error'); return; }
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    chatWs = new WebSocket(`${proto}//${location.host}/ws/chat?token=${accessToken}`);
    chatWs.onmessage = e => {
        const msg = JSON.parse(e.data);
        const el = document.getElementById('chat-messages');
        el.innerHTML += `<div class="chat-msg ${msg.sender}"><strong>${msg.sender === 'admin' ? 'Admin' : 'You'}:</strong> ${msg.text}</div>`;
        el.scrollTop = el.scrollHeight;
    };
    chatWs.onclose = () => { chatWs = null; };
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';

    const el = document.getElementById('chat-messages');
    el.innerHTML += `<div class="chat-msg user"><strong>You:</strong> ${text}</div>`;
    el.scrollTop = el.scrollHeight;

    if (chatMode === 'ai') {
        el.innerHTML += `<div class="chat-msg ai" style="opacity:0.5;"><strong>ИИ:</strong> ⏳ Думаю...</div>`;
        el.scrollTop = el.scrollHeight;
        try {
            const res = await api('/api/ai/chat', { method: 'POST', body: JSON.stringify({ message: text }) });
            const data = await res.json();
            const aiMsgs = el.querySelectorAll('.chat-msg.ai');
            const lastAi = aiMsgs[aiMsgs.length - 1];
            if (lastAi) lastAi.remove();
            const icon = data.success ? '✅' : '❌';
            el.innerHTML += `<div class="chat-msg ai"><strong>ИИ:</strong> ${icon} ${data.message.replace(/\n/g, '<br>')}</div>`;
            el.scrollTop = el.scrollHeight;
        } catch {
            const aiMsgs = el.querySelectorAll('.chat-msg.ai');
            const lastAi = aiMsgs[aiMsgs.length - 1];
            if (lastAi) lastAi.remove();
            el.innerHTML += `<div class="chat-msg ai"><strong>ИИ:</strong> ❌ Ошибка соединения</div>`;
        }
    } else {
        if (!chatWs) connectChat();
        if (chatWs) chatWs.send(JSON.stringify({ text }));
    }
}

/* ===== 9. Store Branding ===== */
async function loadStoreBranding() {
    try {
        const res = await api('/api/store/settings');
        if (!res.ok) return;
        const s = await res.json();
        const name = s.store_name || 'MyShop';
        storeName = name;
        document.getElementById('store-logo-text').textContent = name;
        document.title = name + ' — Интернет-магазин';
        document.querySelectorAll('[data-store-name]').forEach(el => el.textContent = name);
        const heroTitle = document.querySelector('[data-i18n="hero_title"]');
        if (heroTitle) heroTitle.textContent = `Добро пожаловать в ${name}`;
        document.querySelectorAll('.footer-logo').forEach(el => el.innerHTML = `<i class="fas fa-shopping-bag"></i> ${name}`);
        document.querySelectorAll('.copyright').forEach(el => el.textContent = `© ${new Date().getFullYear()} ${name}. Все права защищены.`);
        if (s.theme) setTheme(s.theme);
    } catch {}
}

/* ===== 10. CSV Export ===== */
function exportCSV(type) {
    if (!accessToken) return;
    window.open(`/api/admin/export/${type}?token=${accessToken}`, '_blank');
}

/* ===== API Helper ===== */
async function api(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }
    const res = await fetch(`${API_BASE}${url}`, { ...options, headers });
    if (res.status === 401 && accessToken) {
        accessToken = '';
        currentUser = '';
        currentRole = '';
        currentUserId = 0;
        localStorage.removeItem('accessToken');
        localStorage.removeItem('currentUser');
        localStorage.removeItem('currentRole');
        localStorage.removeItem('currentUserId');
        updateHeader();
        showToast('Сессия истекла. Войдите снова.', 'error');
        showAuthModal();
    }
    return res;
}

/* ===== Navigation ===== */
function showSection(sectionId) {
    document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(sectionId);
    if (target) target.classList.add('active');

    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const link = document.querySelector(`.nav-links a[onclick*="'${sectionId}'"]`);
    if (link) link.classList.add('active');

    localStorage.setItem('lastSection', sectionId);

    if (sectionId === 'cart') loadCart();
    if (sectionId === 'profile') { loadProfile(); loadProfileOrders(); loadLoyalty(); loadReferral(); load2FA(); }
    if (sectionId === 'wishlist') loadWishlist();
    if (sectionId === 'catalog') loadFilteredProducts();
    if (sectionId === 'compare') renderComparison();
    if (sectionId === 'deferred') renderDeferred();
    if (sectionId === 'home') { loadRecommendations(); loadFlashSales(); }
    if (sectionId === 'admin') {
        const savedTab = localStorage.getItem('lastAdminTab') || 'stats';
        setTimeout(() => adminTab(savedTab), 50);
    }
}

/* ===== Products & Search ===== */
let searchTimeout = null;

async function loadCategories() {
    try {
        const res = await api('/api/products/categories');
        if (!res.ok) throw new Error();
        const categories = await res.json();
        const select = document.getElementById('category-filter');
        categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            select.appendChild(opt);
        });
    } catch {}
}

async function loadBrands() {
    try {
        const res = await api('/api/products/brands');
        if (!res.ok) throw new Error();
        const brands = await res.json();
        const select = document.getElementById('brand-filter');
        brands.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b;
            opt.textContent = b;
            select.appendChild(opt);
        });
    } catch {}
}

function renderStars(rating) {
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.3;
    let html = '';
    for (let i = 0; i < full; i++) html += '<i class="fas fa-star"></i>';
    if (half) html += '<i class="fas fa-star-half-alt"></i>';
    const empty = 5 - full - (half ? 1 : 0);
    for (let i = 0; i < empty; i++) html += '<i class="far fa-star"></i>';
    return html;
}

async function loadFilteredProducts() {
    const search = document.getElementById('search-input')?.value || '';
    const category = document.getElementById('category-filter')?.value || '';
    const brand = document.getElementById('brand-filter')?.value || '';
    const minRating = document.getElementById('rating-filter')?.value || '';
    const sort = document.getElementById('sort-filter')?.value || '';
    const minPrice = document.getElementById('min-price')?.value || '';
    const maxPrice = document.getElementById('max-price')?.value || '';
    const color = document.getElementById('color-filter')?.value || '';
    const size = document.getElementById('size-filter')?.value || '';
    const inStock = document.getElementById('stock-filter')?.checked || false;
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    if (brand) params.set('brand', brand);
    if (minRating) params.set('min_rating', minRating);
    if (sort) params.set('sort', sort);
    if (minPrice) params.set('min_price', minPrice);
    if (maxPrice) params.set('max_price', maxPrice);
    if (color) params.set('color', color);
    if (size) params.set('size', size);
    if (inStock) params.set('in_stock', 'true');
    const qs = params.toString();
    const url = '/api/products' + (qs ? '?' + qs : '');

    const grid = document.getElementById('products-grid');
    let skeletonTimer = setTimeout(() => { grid.innerHTML = skeletonProducts(6); }, 500);
    try {
        const res = await api(url);
        clearTimeout(skeletonTimer);
        if (!res.ok) throw new Error();
        const products = await res.json();
        if (!products.length) {
            grid.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-secondary);">
                <i class="fas fa-search" style="font-size:3rem;margin-bottom:1rem;"></i>
                <p>${t('not_found')}</p></div>`;
            return;
        }
        const now = Date.now();
        const WEEK = 7 * 24 * 60 * 60 * 1000;
        products.forEach(p => {
            const inCompare = compareList.some(c => c.id === p.id);
            const isNew = p.created_at && (now - new Date(p.created_at).getTime()) < WEEK;
            const card = document.createElement('div');
            card.className = 'product-card fade-in';
            card.style.animationDelay = `${p.id * 0.05}s`;
            card.style.cursor = 'pointer';
            card.onclick = () => showProductDetail(p.id);
            card.innerHTML = `
                <div class="product-image">
                    ${isNew ? '<span class="badge-new">Новинка</span>' : ''}
                    <img src="${p.image}" alt="${p.name}" loading="lazy" style="width:100%;height:100%;object-fit:cover;">
                    <button class="wishlist-btn" onclick="toggleWishlist(${p.id}, event)"><i class="far fa-heart"></i></button>
                </div>
                <div class="product-content">
                    <div class="product-brand" onclick="showBrandPage('${p.brand}')" style="cursor:pointer;text-decoration:underline;">${p.brand}</div>
                    <h3 class="product-name">${p.name}</h3>
                    <div class="product-rating">
                        <span class="stars">${renderStars(p.rating)}</span>
                        <span class="rating-value">${p.rating.toFixed(1)}</span>
                    </div>
                    <div class="product-price">${p.price.toLocaleString()} ₽</div>
                    <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
                        <button class="add-to-cart" style="flex:1;" onclick="addToCart(${p.id}, event)"><i class="fas fa-shopping-cart"></i> ${t('add_cart')}</button>
                        <button class="btn-sm ${inCompare ? 'primary' : ''}" onclick="event.stopPropagation();toggleCompareItem(${p.id})" title="${t('compare')}"><i class="fas fa-balance-scale"></i></button>
                    </div>
                </div>`;
            grid.appendChild(card);
        });
        trackViewHistory(products.slice(0, 5));
        updateMiniCart();
    } catch (e) {
        grid.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--danger-color);">
            <i class="fas fa-exclamation-triangle" style="font-size:3rem;margin-bottom:1rem;"></i>
            <p>Не удалось загрузить товары</p></div>`;
    }
}

/* ===== Product Detail & Reviews ===== */
let currentProductId = null;
let selectedRating = 0;

async function showProductDetail(productId) {
    currentProductId = productId;
    window._currentProductId = productId;
    localStorage.setItem('lastProductId', productId);
    showSection('product-detail');
    const content = document.getElementById('product-detail-content');
    const reviewsEl = document.getElementById('product-reviews');
    content.innerHTML = skeleton(6);
    reviewsEl.innerHTML = '';

    try {
        const [prodRes, avgRes, reviewsRes] = await Promise.all([
            api(`/api/products/${productId}`),
            api(`/api/reviews/product/${productId}/avg`),
            api(`/api/reviews/product/${productId}`),
        ]);
        const product = await prodRes.json();
        const avg = await avgRes.json();
        const reviews = await reviewsRes.json();

        content.innerHTML = `
            <div class="product-detail-img">
                <img src="${product.image}" alt="${product.name}" loading="lazy">
            </div>
            <div class="product-detail-info">
                <div class="product-brand">${product.brand}</div>
                <h2>${product.name}</h2>
                <div class="detail-rating">
                    <span class="stars">${renderStars(avg.avg_rating || product.rating)}</span>
                    <span>${(avg.avg_rating || product.rating).toFixed(1)}</span>
                    <span style="color:var(--text-secondary);">(${avg.review_count} отзывов)</span>
                </div>
                <div class="detail-price">${product.price.toLocaleString()} ₽</div>
                <div style="color:var(--text-secondary);">Категория: ${product.category}</div>
                <button class="add-to-cart" onclick="addToCart(${product.id}, event)" style="width:fit-content;margin-top:1rem;">
                    <i class="fas fa-shopping-cart"></i> В корзину
                </button>
            </div>`;

        renderReviews(reviews);
        renderReviewForm();
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Товар не найден</p>';
    }
}

function renderReviews(reviews) {
    const el = document.getElementById('product-reviews');
    if (!reviews.length) {
        el.innerHTML = '<p style="color:var(--text-secondary);margin-top:1rem;">Отзывов пока нет. Будьте первым!</p>';
        return;
    }
    el.innerHTML = reviews.map(r => `
        <div class="review-card">
            <div class="review-card-header">
                <span class="review-author">${r.username}</span>
                <span class="review-date">${r.created_at.split('T')[0]}</span>
            </div>
            <div class="review-stars">${renderStars(r.rating)}</div>
            ${r.text ? `<div class="review-text">${r.text}</div>` : ''}
        </div>`).join('');
}

function renderReviewForm() {
    const el = document.getElementById('product-reviews');
    if (!accessToken) return;
    const formHtml = `
        <div class="review-form" id="review-form">
            <h4 style="margin-bottom:0.75rem;">Оставить отзыв</h4>
            <div class="review-stars-select" id="review-stars">
                ${[1,2,3,4,5].map(i => `<i class="far fa-star" data-val="${i}" onmouseenter="hoverStars(${i})" onmouseleave="resetStars()" onclick="selectStar(${i})"></i>`).join('')}
            </div>
            <textarea id="review-text" placeholder="Ваш отзыв (необязательно)"></textarea>
            <button class="btn-sm primary" onclick="submitReview()">Отправить</button>
        </div>`;
    el.insertAdjacentHTML('afterbegin', formHtml);
}

function hoverStars(n) {
    document.querySelectorAll('#review-stars i').forEach((s, i) => {
        s.className = i < n ? 'fas fa-star active' : 'far fa-star';
    });
}

function resetStars() {
    document.querySelectorAll('#review-stars i').forEach((s, i) => {
        s.className = i < selectedRating ? 'fas fa-star active' : 'far fa-star';
    });
}

function selectStar(n) {
    selectedRating = n;
    resetStars();
}

async function submitReview() {
    if (!selectedRating) { showToast('Выберите рейтинг', 'error'); return; }
    const text = document.getElementById('review-text')?.value || '';
    try {
        const res = await api('/api/reviews', {
            method: 'POST',
            body: JSON.stringify({ product_id: currentProductId, rating: selectedRating, text })
        });
        if (res.ok) {
            showToast('Отзыв добавлен');
            selectedRating = 0;
            showProductDetail(currentProductId);
        } else {
            const e = await res.json();
            showToast(e.detail || 'Ошибка', 'error');
        }
    } catch { showToast('Ошибка сервера', 'error'); }
}

/* ===== Wishlist ===== */
async function toggleWishlist(productId, event) {
    event?.stopPropagation();
    if (!accessToken) { showToast('Войдите, чтобы добавить в избранное', 'error'); showAuthModal(); return; }
    try {
        const checkRes = await api(`/api/wishlist/check/${productId}`);
        const check = await checkRes.json();
        if (check.is_wishlisted) {
            await api(`/api/wishlist/${productId}`, { method: 'DELETE' });
            showToast('Удалено из избранного');
        } else {
            await api('/api/wishlist', { method: 'POST', body: JSON.stringify({ product_id: productId }) });
            showToast('Добавлено в избранное');
        }
        if (document.getElementById('wishlist')?.classList.contains('active')) loadWishlist();
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function loadWishlist() {
    const grid = document.getElementById('wishlist-grid');
    grid.innerHTML = '';
    if (!accessToken) {
        grid.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-secondary);"><i class="fas fa-heart" style="font-size:3rem;margin-bottom:1rem;"></i><p>Войдите, чтобы увидеть избранное</p></div>`;
        return;
    }
    try {
        const res = await api('/api/wishlist');
        if (!res.ok) throw new Error();
        const items = await res.json();
        if (!items.length) {
            grid.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-secondary);"><i class="fas fa-heart-broken" style="font-size:3rem;margin-bottom:1rem;"></i><p>Избранное пусто</p></div>`;
            return;
        }
        items.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card fade-in';
            card.style.cursor = 'pointer';
            card.onclick = () => showProductDetail(p.product_id);
            card.innerHTML = `
                <div class="product-image">
                    <img src="${p.image}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover;">
                    <button class="wishlist-btn active" onclick="toggleWishlist(${p.product_id}, event)"><i class="fas fa-heart"></i></button>
                </div>
                <div class="product-content">
                    <div class="product-brand">${p.brand}</div>
                    <h3 class="product-name">${p.name}</h3>
                    <div class="product-rating">
                        <span class="stars">${renderStars(p.rating)}</span>
                        <span class="rating-value">${p.rating.toFixed(1)}</span>
                    </div>
                    <div class="product-price">${p.price.toLocaleString()} ₽</div>
                </div>`;
            grid.appendChild(card);
        });
    } catch {
        grid.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--danger-color);">Ошибка загрузки</div>`;
    }
}

/* ===== Cart ===== */
async function addToCart(productId, event) {
    if (!accessToken) {
        showToast('Войдите, чтобы добавить товары', 'error');
        showAuthModal();
        return;
    }
    const btn = event?.target?.closest('.add-to-cart');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-check"></i> Добавлено';
        setTimeout(() => { btn.disabled = false; btn.innerHTML = '<i class="fas fa-shopping-cart"></i> В корзину'; }, 2000);
    }
    try {
        const res = await api('/api/cart/add', {
            method: 'POST',
            body: JSON.stringify({ product_id: productId, quantity: 1 })
        });
        if (res.ok) {
            showToast('Товар добавлен в корзину');
            loadCart();
            updateCartCountPulse();
            updateMiniCart();
        } else {
            const err = await res.json();
            showToast(err.detail || 'Ошибка', 'error');
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-shopping-cart"></i> В корзину'; }
        }
    } catch {
        showToast('Ошибка сервера', 'error');
    }
}

let cartSelectedIds = [];
let deliveryType = 'courier';
let savedAddress = '';

async function loadCart() {
    const container = document.getElementById('cart-items');
    const totalBlock = document.getElementById('cart-total');
    const toolbar = document.getElementById('cart-toolbar');
    const totalAmount = document.getElementById('total-amount');
    const totalItems = document.getElementById('total-items');

    if (!accessToken) {
        container.innerHTML = `<div class="empty-cart"><i class="fas fa-lock"></i>
            <p>Войдите, чтобы увидеть корзину</p>
            <button class="cta-button" onclick="showAuthModal()">Войти</button></div>`;
        totalBlock.style.display = 'none';
        toolbar.style.display = 'none';
        return;
    }

    savedAddress = localStorage.getItem('cartAddress') || '';
    updateAddressDisplay();

    try {
        const res = await api('/api/cart');
        if (!res.ok) throw new Error();
        const data = await res.json();
        const items = data.items;
        if (!items.length) {
            container.innerHTML = `<div class="empty-cart"><i class="fas fa-shopping-cart"></i><p>Корзина пуста</p></div>`;
            totalBlock.style.display = 'none';
            toolbar.style.display = 'none';
            return;
        }
        cartSelectedIds = items.map(i => i.id);
        toolbar.style.display = 'flex';
        document.getElementById('cart-select-all').checked = true;

        const days = [2, 3, 1, 4, 2, 5, 3];
        const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

        container.innerHTML = '';
        items.forEach((item, idx) => {
            const daysToAdd = days[idx % days.length];
            const delivDate = new Date();
            delivDate.setDate(delivDate.getDate() + daysToAdd);
            const delivStr = `${delivDate.getDate()} ${months[delivDate.getMonth()]}`;

            const el = document.createElement('div');
            el.className = 'cart-item fade-in selected';
            el.dataset.id = item.id;
            el.innerHTML = `
                <input type="checkbox" class="cart-item-check" checked onchange="toggleCartItem(${item.id}, this.checked)">
                <img class="cart-item-img" src="${item.image || '/static/img/placeholder.png'}" alt="${item.name}">
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.name}</div>
                    <div class="cart-item-price">${item.price.toLocaleString()} ₽ × ${item.quantity}</div>
                    <div class="cart-item-delivery"><i class="fas fa-truck"></i> Доставка: ${delivStr}</div>
                </div>
                <div class="cart-item-actions">
                    <div class="cart-item-total">${(item.price * item.quantity).toLocaleString()} ₽</div>
                    <div class="cart-item-qty">
                        <button class="quantity-btn" onclick="updateQuantity(${item.id}, ${item.quantity - 1})"><i class="fas fa-minus"></i></button>
                        <input type="text" class="quantity-input" value="${item.quantity}" readonly>
                        <button class="quantity-btn" onclick="updateQuantity(${item.id}, ${item.quantity + 1})"><i class="fas fa-plus"></i></button>
                    </div>
                    <button class="cart-item-remove" onclick="removeFromCart(${item.id})"><i class="fas fa-trash"></i> Удалить</button>
                </div>`;
            container.appendChild(el);
        });

        totalBlock.style.display = 'block';
        cartSubtotal = data.total;

        const savedPromo = localStorage.getItem('appliedPromo');
        if (savedPromo) {
            try {
                appliedPromo = JSON.parse(savedPromo);
                const promoEl = document.getElementById('promo-applied');
                if (promoEl) {
                    promoEl.style.display = 'block';
                    const displayCode = appliedPromo.code ? `<span class="promo-code" onclick="copyPromoCode(this, '${appliedPromo.code}')" title="Нажмите, чтобы скопировать">${appliedPromo.code}</span>` : '';
                    document.getElementById('promo-applied-text').innerHTML = displayCode + ' ' + (appliedPromo.message || `— ${appliedPromo.discount_percent || appliedPromo.discount_amount}`);
                }
            } catch { appliedPromo = null; }
        }
        updateCartTotal();
    } catch {
        container.innerHTML = `<div class="empty-cart"><i class="fas fa-wifi"></i><p>Ошибка соединения</p></div>`;
    }
}

function toggleCartItem(id, checked) {
    if (checked) {
        if (!cartSelectedIds.includes(id)) cartSelectedIds.push(id);
    } else {
        cartSelectedIds = cartSelectedIds.filter(i => i !== id);
    }
    const item = document.querySelector(`.cart-item[data-id="${id}"]`);
    if (item) item.classList.toggle('selected', checked);
    document.getElementById('cart-select-all').checked = cartSelectedIds.length === document.querySelectorAll('.cart-item-check').length;
    updateCartTotal();
}

function toggleSelectAll(checked) {
    document.querySelectorAll('.cart-item-check').forEach(cb => {
        cb.checked = checked;
        const id = parseInt(cb.closest('.cart-item').dataset.id);
        cb.closest('.cart-item').classList.toggle('selected', checked);
    });
    cartSelectedIds = checked ? Array.from(document.querySelectorAll('.cart-item')).map(el => parseInt(el.dataset.id)) : [];
    updateCartTotal();
}

function removeSelected() {
    if (!cartSelectedIds.length) return;
    if (!confirm(`Удалить ${cartSelectedIds.length} товаров?`)) return;
    Promise.all(cartSelectedIds.map(id => api(`/api/cart/remove?product_id=${id}`, { method: 'DELETE' })))
        .then(() => { showToast('Выбранные товары удалены'); loadCart(); });
}

function updateCartTotal() {
    const totalAmount = document.getElementById('total-amount');
    const totalItems = document.getElementById('total-items');
    let total = 0, count = 0;
    document.querySelectorAll('.cart-item.selected').forEach(el => {
        const text = el.querySelector('.cart-item-total').textContent.replace(/\s/g, '').replace('₽', '');
        total += parseInt(text) || 0;
        count++;
    });
    if (appliedPromo) {
        if (appliedPromo.discount_percent) total = Math.round(total * (1 - appliedPromo.discount_percent / 100));
        else if (appliedPromo.discount_amount) total = Math.max(0, total - appliedPromo.discount_amount);
    }
    totalAmount.textContent = `${total.toLocaleString()} ₽`;
    if (totalItems) totalItems.textContent = count;
}

async function updateQuantity(productId, qty) {
    if (qty < 1) return removeFromCart(productId);
    try {
        const res = await api(`/api/cart/item/${productId}`, {
            method: 'PUT', body: JSON.stringify({ product_id: productId, quantity: qty })
        });
        if (res.ok) loadCart();
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function removeFromCart(productId) {
    try {
        const res = await api(`/api/cart/remove?product_id=${productId}`, { method: 'DELETE' });
        if (res.ok) { showToast('Товар удалён'); loadCart(); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function clearCart() {
    if (!confirm('Очистить корзину?')) return;
    try {
        const res = await api('/api/cart/clear', { method: 'DELETE' });
        if (res.ok) { showToast('Корзина очищена'); loadCart(); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

function openAddressModal() {
    document.getElementById('cart-address-view').style.display = 'none';
    document.getElementById('cart-address-btn').style.display = 'none';
    document.getElementById('cart-address-form').style.display = 'block';
    const addr = JSON.parse(localStorage.getItem('cartAddressRaw') || '{}');
    if (addr.city) document.getElementById('addr-city').value = addr.city;
    if (addr.street) document.getElementById('addr-street').value = addr.street;
    if (addr.house) document.getElementById('addr-house').value = addr.house;
    if (addr.flat) document.getElementById('addr-flat').value = addr.flat;
    if (addr.pickup) document.getElementById('addr-pickup').value = addr.pickup;
    if (addr.type) selectDeliveryType(addr.type);
}

function closeAddressModal() {
    document.getElementById('cart-address-view').style.display = '';
    document.getElementById('cart-address-btn').style.display = '';
    document.getElementById('cart-address-form').style.display = 'none';
}

function selectDeliveryType(type) {
    deliveryType = type;
    document.querySelectorAll('.delivery-option').forEach(o => o.classList.toggle('active', o.dataset.type === type));
    document.getElementById('delivery-courier-fields').style.display = type === 'courier' ? 'grid' : 'none';
    document.getElementById('delivery-pickup-fields').style.display = type === 'pickup' ? 'grid' : 'none';
}

function saveDeliveryAddress() {
    let addrStr = '';
    const raw = { type: deliveryType };
    if (deliveryType === 'courier') {
        const city = document.getElementById('addr-city').value.trim();
        const street = document.getElementById('addr-street').value.trim();
        const house = document.getElementById('addr-house').value.trim();
        const flat = document.getElementById('addr-flat').value.trim();
        if (!city || !street) { showToast('Укажите город и улицу', 'error'); return; }
        raw.city = city; raw.street = street; raw.house = house; raw.flat = flat;
        addrStr = `${city}, ${street}${house ? ', д. ' + house : ''}${flat ? ', кв. ' + flat : ''}`;
    } else {
        const pickup = document.getElementById('addr-pickup').value;
        if (!pickup) { showToast('Выберите пункт выдачи', 'error'); return; }
        raw.pickup = pickup;
        const opt = document.getElementById('addr-pickup').selectedOptions[0];
        addrStr = opt ? opt.textContent : pickup;
    }
    localStorage.setItem('cartAddress', addrStr);
    localStorage.setItem('cartAddressRaw', JSON.stringify(raw));
    savedAddress = addrStr;
    updateAddressDisplay();
    closeAddressModal();
    showToast('Адрес сохранён');
}

function updateAddressDisplay() {
    const text = document.getElementById('cart-address-text');
    const btn = document.getElementById('cart-address-btn');
    const checkoutAddr = document.getElementById('checkout-address');
    if (savedAddress) {
        text.textContent = savedAddress;
        text.style.color = 'var(--text-primary)';
        text.style.fontWeight = '500';
        btn.innerHTML = '<i class="fas fa-edit"></i> Изменить';
        if (checkoutAddr) checkoutAddr.textContent = savedAddress;
    } else {
        text.textContent = 'Укажите адрес получения';
        text.style.color = 'var(--text-secondary)';
        text.style.fontWeight = '400';
        btn.innerHTML = '<i class="fas fa-plus"></i> Указать адрес';
        if (checkoutAddr) checkoutAddr.textContent = 'Не указан';
    }
}

function updateCartCount() {
    const el = document.getElementById('cart-count');
    if (!accessToken) { el.textContent = '0'; return; }
    api('/api/cart').then(r => r.json()).then(data => {
        el.textContent = data.count;
    }).catch(() => { el.textContent = '0'; });
}

function updateCartCountPulse() {
    const el = document.getElementById('cart-count');
    if (!el) return;
    if (!accessToken) { el.textContent = '0'; return; }
    api('/api/cart').then(r => r.json()).then(data => {
        el.textContent = data.count;
        el.classList.remove('pulse');
        void el.offsetWidth;
        el.classList.add('pulse');
    }).catch(() => { el.textContent = '0'; });
}

/* ===== Auth Modal ===== */
function showAuthModal() {
    document.getElementById('auth-modal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeAuthModal() {
    document.getElementById('auth-modal').classList.remove('active');
    document.body.style.overflow = 'auto';
}

function switchTab(name) {
    const login = document.getElementById('login-form');
    const reg = document.getElementById('register-form');
    const tabs = document.querySelectorAll('.tab');
    if (name === 'login') {
        login.style.display = 'block'; reg.style.display = 'none';
        tabs[0].classList.add('active'); tabs[1].classList.remove('active');
    } else {
        login.style.display = 'none'; reg.style.display = 'block';
        tabs[0].classList.remove('active'); tabs[1].classList.add('active');
    }
}

function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

async function login(event) {
    event.preventDefault();
    const username = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const totpCode = document.getElementById('login-totp')?.value || '';
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');
    let hasError = false;
    if (!username) { document.getElementById('login-email-error').style.display = 'block'; hasError = true; }
    if (!password) { document.getElementById('login-password-error').style.display = 'block'; hasError = true; }
    if (hasError) return;

    try {
        const url = totpCode
            ? `/login/2fa?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&totp_code=${encodeURIComponent(totpCode)}`
            : `/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;
        const res = await api(url, { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            if (!data.access_token) {
                document.getElementById('tfa-row').style.display = 'block';
                showToast('Введите код из приложения', 'error');
                return;
            }
            accessToken = data.access_token;
            currentUser = data.username;
            currentRole = data.role;
            currentUserId = data.user_id || 0;
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('currentUser', currentUser);
            localStorage.setItem('currentRole', currentRole);
            localStorage.setItem('currentUserId', currentUserId);
            showToast('Вход выполнен!');
            closeAuthModal();
            updateHeader();
            updateCartCount();
            connectNotifWS();
        } else {
            const err = await res.json();
            showToast(err.detail || 'Неверные данные', 'error');
        }
    } catch {
        showToast('Ошибка сервера', 'error');
    }
}

async function register(event) {
    event.preventDefault();
    const email = document.getElementById('register-email').value;
    const loginVal = document.getElementById('register-login').value;
    const password = document.getElementById('register-password').value;
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');
    let hasError = false;
    if (!email || !validateEmail(email)) { document.getElementById('register-email-error').style.display = 'block'; hasError = true; }
    if (!loginVal) { document.getElementById('register-login-error').style.display = 'block'; hasError = true; }
    if (!password || password.length < 6) { document.getElementById('register-password-error').style.display = 'block'; hasError = true; }
    if (hasError) return;

    try {
        const res = await api(`/register?username=${encodeURIComponent(loginVal)}&password=${encodeURIComponent(password)}`, {
            method: 'POST'
        });
        if (res.ok) {
            showToast('Регистрация выполнена!');
            document.getElementById('login-email').value = loginVal;
            document.getElementById('login-password').value = password;
            await login(new Event('submit'));
        } else {
            const err = await res.json();
            showToast(err.detail || 'Ошибка регистрации', 'error');
        }
    } catch {
        showToast('Ошибка сервера', 'error');
    }
}

function logout() {
    if (chatWs) { chatWs.close(); chatWs = null; }
    if (notifWs) { notifWs.close(); notifWs = null; }
    accessToken = '';
    currentUser = '';
    currentRole = '';
    currentUserId = 0;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('currentRole');
    localStorage.removeItem('currentUserId');
    localStorage.removeItem('appliedPromo');
    localStorage.removeItem('lastSection');
    localStorage.removeItem('lastAdminTab');
    localStorage.removeItem('lastProductId');
    updateHeader();
    updateCartCount();
    showToast('Вы вышли из системы');
    showSection('home');
}

function updateHeader() {
    const authLink = document.getElementById('auth-link');
    const userInfo = document.getElementById('user-info');
    const headerUser = document.getElementById('header-username');
    const adminLink = document.getElementById('admin-link');
    const profileLink = document.getElementById('profile-link');
    const wishlistLink = document.getElementById('wishlist-link');
    const chatWidget = document.getElementById('chat-widget');
    if (accessToken && currentUser) {
        authLink.style.display = 'none';
        userInfo.style.display = 'flex';
        headerUser.textContent = currentUser;
        const avatarEl = document.getElementById('header-avatar');
        if (avatarEl) {
            api('/api/profile').then(r => r.ok ? r.json() : null).then(p => {
                if (p && p.avatar_url) {
                    avatarEl.innerHTML = `<img src="${p.avatar_url}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">`;
                } else {
                    avatarEl.innerHTML = userAvatar(currentUser, 'sm');
                }
            }).catch(() => {
                avatarEl.innerHTML = userAvatar(currentUser, 'sm');
            });
        }
        if (adminLink) adminLink.style.display = currentRole === 'admin' ? 'list-item' : 'none';
        if (profileLink) profileLink.style.display = 'list-item';
        if (wishlistLink) wishlistLink.style.display = 'list-item';
        if (chatWidget) {
            chatWidget.style.display = 'block';
            const aiBtn = document.getElementById('chat-mode-ai');
            if (aiBtn) {
                if (currentRole === 'admin') {
                    aiBtn.style.display = '';
                } else {
                    api(`/api/admin/users/${currentUserId}/roles`).then(r => r.ok ? r.json() : []).then(roles => {
                        const isOwner = roles.some(r => r.role_name === 'owner');
                        aiBtn.style.display = isOwner ? '' : 'none';
                        if (!isOwner && chatMode === 'ai') setChatMode('support');
                    }).catch(() => { aiBtn.style.display = 'none'; });
                }
            }
        }
    } else {
        authLink.style.display = 'list-item';
        userInfo.style.display = 'none';
        if (adminLink) adminLink.style.display = 'none';
        if (profileLink) profileLink.style.display = 'none';
        if (wishlistLink) wishlistLink.style.display = 'none';
        if (chatWidget) chatWidget.style.display = 'none';
    }
}

/* ===== Checkout ===== */
let appliedPromo = null;
let cartSubtotal = 0;

async function checkout() {
    if (!accessToken) { showToast('Войдите для оформления', 'error'); showAuthModal(); return; }
    const addr = savedAddress || localStorage.getItem('cartAddress') || '';
    if (!addr) { showToast('Укажите адрес доставки', 'error'); openAddressModal(); return; }
    const paymentMethod = document.getElementById('payment-method')?.value || 'card';
    const promoCode = document.getElementById('promo-input')?.value || null;
    const selectedCount = document.querySelectorAll('.cart-item.selected').length;
    if (!selectedCount) { showToast('Выберите хотя бы один товар', 'error'); return; }
    try {
        const res = await api('/api/order', {
            method: 'POST',
            body: JSON.stringify({ address: addr, promo_code: promoCode, payment_method: paymentMethod })
        });
        if (res.ok) {
            const data = await res.json();
            let msg = `✅ Заказ #${data.order_id} на сумму ${data.total.toLocaleString()} ₽ оформлен!`;
            if (data.discount > 0) msg += ` (Скидка: ${data.discount.toLocaleString()} ₽)`;
            const toast = document.getElementById('toast');
            toast.innerHTML = `<span class="toast-icon">✓</span><span>${msg}</span><button class="toast-close" onclick="this.parentElement.classList.remove('show')">×</button><button onclick="showSection('profile');setTimeout(()=>document.getElementById('order-history-anchor').scrollIntoView({behavior:'smooth'}),300);this.parentElement.classList.remove('show')" style="background:var(--primary-color);color:#fff;border:none;border-radius:6px;padding:4px 12px;cursor:pointer;font-size:0.8rem;margin-left:8px;white-space:nowrap;">Посмотреть заказы</button>`;
            toast.className = 'toast success';
            setTimeout(() => toast.classList.add('show'), 10);
            clearTimeout(window._toastTimer);
            window._toastTimer = setTimeout(() => toast.classList.remove('show'), 8000);
            document.getElementById('promo-input').value = '';
            appliedPromo = null;
            localStorage.removeItem('appliedPromo');
            loadCart();
        } else {
            const err = await res.json();
            showToast(err.detail || 'Ошибка', 'error');
        }
    } catch {
        showToast('Ошибка сервера', 'error');
    }
}

async function applyPromo() {
    const code = document.getElementById('promo-input')?.value;
    if (!code) { showToast('Введите промокод', 'error'); return; }
    try {
        const res = await api('/api/promos/validate', { method: 'POST', body: JSON.stringify({ code }) });
        if (res.ok) {
            const data = await res.json();
            appliedPromo = data;
            localStorage.setItem('appliedPromo', JSON.stringify(data));
            document.getElementById('promo-applied').style.display = 'block';
            const promoText = document.getElementById('promo-applied-text');
            const displayCode = data.code ? `<span class="promo-code" onclick="copyPromoCode(this, '${data.code}')" title="Нажмите, чтобы скопировать">${data.code}</span>` : '';
            promoText.innerHTML = displayCode + ' ' + (data.message || `— ${data.discount_percent || data.discount_amount}`);
            document.getElementById('promo-input').value = '';
            updateCartTotal();
            showToast(data.message);
        } else {
            const err = await res.json();
            showToast(err.detail || 'Ошибка', 'error');
        }
    } catch { showToast('Ошибка сервера', 'error'); }
}

function removePromo() {
    appliedPromo = null;
    localStorage.removeItem('appliedPromo');
    document.getElementById('promo-applied').style.display = 'none';
    document.getElementById('promo-input').value = '';
    updateCartTotal();
}

/* ===== Profile ===== */
async function loadProfile() {
    if (!accessToken) return;
    try {
        const res = await api('/api/profile');
        if (!res.ok) throw new Error();
        const p = await res.json();
        document.getElementById('pf-fullname').value = p.full_name || '';
        document.getElementById('pf-email').value = p.email || '';
        document.getElementById('pf-phone').value = p.phone || '';
        document.getElementById('pf-address').value = p.address || '';
        renderProfileAvatar(p.avatar_url, p.username);
    } catch {}
}

function renderProfileAvatar(url, username) {
    const wrap = document.getElementById('profile-avatar-wrap');
    const delBtn = document.getElementById('avatar-delete-btn');
    if (!wrap) return;
    if (url) {
        wrap.innerHTML = `<img src="${url}" style="width:64px;height:64px;border-radius:50%;object-fit:cover;border:2px solid var(--border-color);box-shadow:0 2px 8px rgba(0,0,0,0.12);">`;
        if (delBtn) delBtn.style.display = '';
    } else {
        wrap.innerHTML = userAvatar(username || currentUser, 'lg');
        if (delBtn) delBtn.style.display = 'none';
    }
}

async function uploadAvatar(input) {
    const file = input.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    const headers = {};
    if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;
    try {
        const res = await fetch('/api/profile/avatar', { method: 'POST', headers, body: formData });
        if (res.ok) {
            const data = await res.json();
            showToast('Аватар загружен');
            renderProfileAvatar(data.avatar_url, currentUser);
            const avatarEl = document.getElementById('header-avatar');
            if (avatarEl && data.avatar_url) {
                avatarEl.innerHTML = `<img src="${data.avatar_url}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">`;
            }
        } else {
            const e = await res.json();
            showToast(e.detail || 'Ошибка', 'error');
        }
    } catch { showToast('Ошибка сервера', 'error'); }
    input.value = '';
}

async function deleteAvatar() {
    if (!confirm('Удалить аватар?')) return;
    try {
        const res = await api('/api/profile/avatar', { method: 'DELETE' });
        if (res.ok) {
            showToast('Аватар удалён');
            renderProfileAvatar(null, currentUser);
            const avatarEl = document.getElementById('header-avatar');
            if (avatarEl) avatarEl.innerHTML = userAvatar(currentUser, 'sm');
        } else { showToast('Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function saveProfile() {
    const body = {
        full_name: document.getElementById('pf-fullname').value || null,
        email: document.getElementById('pf-email').value || null,
        phone: document.getElementById('pf-phone').value || null,
        address: document.getElementById('pf-address').value || null,
    };
    try {
        const res = await api('/api/profile', { method: 'PATCH', body: JSON.stringify(body) });
        if (res.ok) { showToast('Профиль сохранён'); }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function changePassword() {
    const oldPw = document.getElementById('pw-old').value;
    const newPw = document.getElementById('pw-new').value;
    const confirmPw = document.getElementById('pw-confirm')?.value || '';
    if (!oldPw || !newPw) { showToast('Заполните все поля', 'error'); return; }
    if (newPw.length < 6) { showToast('Минимум 6 символов', 'error'); return; }
    if (newPw !== confirmPw) { showToast('Пароли не совпадают', 'error'); return; }
    try {
        const res = await api('/api/profile/change-password', {
            method: 'POST', body: JSON.stringify({ old_password: oldPw, new_password: newPw })
        });
        if (res.ok) { showToast('Пароль изменён'); document.getElementById('pw-old').value = ''; document.getElementById('pw-new').value = ''; document.getElementById('pw-confirm').value = ''; resetPasswordStrength(); }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

function checkPasswordStrength(pw) {
    let score = 0;
    if (pw.length >= 6) score++;
    if (pw.length >= 10) score++;
    if (/[A-Z]/.test(pw) && /[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;

    const bars = [document.getElementById('pw-bar-1'), document.getElementById('pw-bar-2'), document.getElementById('pw-bar-3')];
    const label = document.getElementById('pw-label');
    if (!bars[0] || !label) return;

    const colors = ['var(--danger-color)', 'var(--warning-color)', 'var(--success-color)'];
    const labels = ['', 'Слабый', 'Средний', 'Надёжный'];
    const idx = Math.min(score, 3);

    bars.forEach((b, i) => { b.style.background = i < idx ? colors[idx - 1] : 'var(--border-color)'; });
    label.textContent = pw.length ? labels[idx] || labels[1] : '';
    label.style.color = idx > 0 ? colors[idx - 1] : 'var(--text-secondary)';
}

function resetPasswordStrength() {
    ['pw-bar-1', 'pw-bar-2', 'pw-bar-3'].forEach(id => { const el = document.getElementById(id); if (el) el.style.background = 'var(--border-color)'; });
    const label = document.getElementById('pw-label'); if (label) { label.textContent = ''; }
}

async function loadProfileOrders() {
    const el = document.getElementById('profile-orders');
    if (!accessToken) { el.innerHTML = ''; return; }
    try {
        const res = await api('/api/profile/orders');
        if (!res.ok) throw new Error();
        const orders = await res.json();
        if (!orders.length) { el.innerHTML = '<p style="color:var(--text-secondary);margin-top:1rem;">Заказов пока нет</p>'; return; }
        el.innerHTML = orders.map(o => `
            <div class="order-card">
                <div class="order-card-header">
                    <div>
                        <strong>#${o.id}</strong> — ${o.total.toLocaleString()} ₽
                        <span class="status-badge ${o.status}" style="margin-left:0.5rem;">${o.status}</span>
                    </div>
                    <div style="font-size:0.85rem;color:var(--text-secondary);">${o.created_at.split('T')[0]}</div>
                </div>
                <div class="order-items-list">
                    ${o.items.map(i => `${i.product_name} × ${i.quantity} — ${i.price.toLocaleString()} ₽`).join(', ')}
                </div>
                <div style="font-size:0.85rem;color:var(--text-secondary);">Адрес: ${o.address}</div>
                <button class="btn-sm" style="margin-top:0.5rem;" onclick="trackOrder(${o.id})"><i class="fas fa-truck"></i> ${t('tracking_title')}</button>
                <div id="tracking-${o.id}" style="display:none;"></div>
            </div>`).join('');
    } catch { el.innerHTML = ''; }
}

/* ===== Admin ===== */
let adminCurrentTab = 'stats';

function adminTab(tab) {
    adminCurrentTab = tab;
    localStorage.setItem('lastAdminTab', tab);
    document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.admin-tab[onclick="adminTab('${tab}')"]`).classList.add('active');
    if (tab === 'guide') loadGuideTab();
    else if (tab === 'stats') loadAdminStats();
    else if (tab === 'products') loadAdminProducts();
    else if (tab === 'users') loadAdminUsers();
    else if (tab === 'rbac') loadRbacTab();
    else if (tab === 'orders') loadAdminOrders();
    else if (tab === 'store') loadStoreSettings();
}

function loadGuideTab() {
    const content = document.getElementById('admin-content');
    content.innerHTML = `
        <div style="max-width:800px;">
            <div style="background:linear-gradient(135deg,#3b82f6,#8b5cf6);border-radius:16px;padding:30px;color:#fff;margin-bottom:24px;">
                <h2 style="margin:0 0 8px;font-size:24px;">Добро пожаловать в MyShop!</h2>
                <p style="margin:0;opacity:0.9;">Ваш магазин создан. Вот что нужно сделать дальше.</p>
            </div>

            <div style="display:grid;gap:16px;">

                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
                    <h3 style="margin:0 0 12px;display:flex;align-items:center;gap:8px;">
                        <span style="background:#dbeafe;color:#2563eb;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;">1</span>
                        О платформе
                    </h3>
                    <p style="color:#64748b;font-size:14px;line-height:1.7;margin:0 0 12px;">
                        MyShop — это готовая платформа для интернет-магазина. Вам не нужно программировать.
                        Всё уже работает: каталог, корзина, оплата, доставка, аналитика.
                    </p>
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">
                        <div style="background:#f8fafc;padding:12px;border-radius:8px;text-align:center;">
                            <div style="font-size:24px;">📦</div>
                            <div style="font-size:13px;font-weight:500;">Каталог</div>
                        </div>
                        <div style="background:#f8fafc;padding:12px;border-radius:8px;text-align:center;">
                            <div style="font-size:24px;">💳</div>
                            <div style="font-size:13px;font-weight:500;">Оплата</div>
                        </div>
                        <div style="background:#f8fafc;padding:12px;border-radius:8px;text-align:center;">
                            <div style="font-size:24px;">🚚</div>
                            <div style="font-size:13px;font-weight:500;">Доставка</div>
                        </div>
                    </div>
                </div>

                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
                    <h3 style="margin:0 0 12px;display:flex;align-items:center;gap:8px;">
                        <span style="background:#dcfce7;color:#16a34a;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;">2</span>
                        Добавьте товары
                    </h3>
                    <p style="color:#64748b;font-size:14px;line-height:1.7;margin:0 0 12px;">
                        Товары — основа вашего магазина. Добавьте фото, название, описание и цену.
                        Покупатели смогут найти их через поиск и фильтры.
                    </p>
                    <button class="btn-sm primary" onclick="adminTab('products')" style="margin-top:4px;">
                        <i class="fas fa-plus"></i> Перейти к товарам
                    </button>
                </div>

                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
                    <h3 style="margin:0 0 12px;display:flex;align-items:center;gap:8px;">
                        <span style="background:#fef3c7;color:#d97706;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;">3</span>
                        Настройте дизайн
                    </h3>
                    <p style="color:#64748b;font-size:14px;line-height:1.7;margin:0 0 12px;">
                        Выберите тему, загрузите логотип, напишите название магазина.
                        Всё настраивается в одном месте.
                    </p>
                    <button class="btn-sm primary" onclick="adminTab('store')" style="margin-top:4px;">
                        <i class="fas fa-palette"></i> Настроить дизайн
                    </button>
                </div>

                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
                    <h3 style="margin:0 0 12px;display:flex;align-items:center;gap:8px;">
                        <span style="background:#ede9fe;color:#7c3aed;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;">4</span>
                        Подключите оплату
                    </h3>
                    <p style="color:#64748b;font-size:14px;line-height:1.7;margin:0 0 12px;">
                        Чтобы принимать платежи, добавьте ключи ЮKassa в настройки.
                        Клиенты смогут платить картой, СБП.
                    </p>
                    <div style="background:#f8fafc;border-radius:8px;padding:12px;margin-top:8px;font-size:13px;color:#64748b;">
                        <strong>Что нужно:</strong> Зарегистрируйтесь на <a href="https://yookassa.ru" target="_blank" style="color:#3b82f6;">yookassa.ru</a>,
                        возьмите ключи из настроек магазина.
                    </div>
                </div>

                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
                    <h3 style="margin:0 0 12px;display:flex;align-items:center;gap:8px;">
                        <span style="background:#fee2e2;color:#dc2626;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;">5</span>
                        Запустите продажи!
                    </h3>
                    <p style="color:#64748b;font-size:14px;line-height:1.7;margin:0;">
                        После добавления товаров и настройки оплаты — ваш магазин готов к продажам!
                        Делитесь ссылкой с клиентами.
                    </p>
                    <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap;">
                        <a href="/" target="_blank" class="btn-sm primary"><i class="fas fa-external-link-alt"></i> Открыть магазин</a>
                        <button class="btn-sm" onclick="adminTab('stats')"><i class="fas fa-chart-line"></i> Статистика</button>
                    </div>
                </div>

            </div>
        </div>
    `;
}

async function loadAdminStats() {
    const content = document.getElementById('admin-content');
    content.innerHTML = skeletonCards(4);
    try {
        const res = await api('/api/admin/stats');
        if (!res.ok) throw new Error();
        const s = await res.json();
        content.innerHTML = `
            <div class="admin-panel">
                <div class="admin-card"><h3>${t('users_count')}</h3><p style="font-size:2rem;">${s.total_users}</p></div>
                <div class="admin-card"><h3>${t('products_count')}</h3><p style="font-size:2rem;">${s.total_products}</p></div>
                <div class="admin-card"><h3>${t('orders_count')}</h3><p style="font-size:2rem;">${s.total_orders}</p></div>
                <div class="admin-card"><h3>${t('revenue')}</h3><p style="font-size:2rem;">${s.total_revenue.toLocaleString()} ₽</p></div>
            </div>
            <div style="margin-top:1.5rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
                <button class="btn-sm primary" onclick="exportCSV('products')"><i class="fas fa-download"></i> ${t('export_csv')} — Products</button>
                <button class="btn-sm primary" onclick="exportCSV('orders')"><i class="fas fa-download"></i> ${t('export_csv')} — Orders</button>
                <button class="btn-sm primary" onclick="exportCSV('users')"><i class="fas fa-download"></i> ${t('export_csv')} — Users</button>
            </div>
            <div id="period-comparison"></div>
            <div id="funnel-chart"></div>
            <div id="orders-map" style="height:400px;border-radius:12px;overflow:hidden;margin-top:1rem;"></div>`;
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Нет прав или ошибка</p>';
    }
    loadPeriodComparison();
    loadFunnel();
    loadOrdersMap();
}

/* ─── Products CRUD ─── */
async function loadAdminProducts() {
    const content = document.getElementById('admin-content');
    content.innerHTML = skeleton(6);
    try {
        const res = await api('/api/admin/products');
        if (!res.ok) throw new Error();
        const products = await res.json();
        content.innerHTML = `
            <div class="admin-toolbar">
                <h3>Товары (${products.length})</h3>
                <button class="btn-sm primary" onclick="showProductForm()">+ Добавить</button>
            </div>
            <div id="product-form-slot"></div>
            <table class="admin-table">
                <thead><tr><th>ID</th><th>Название</th><th>Цена</th><th>Категория</th><th>Действия</th></tr></thead>
                <tbody>
                    ${products.map(p => `<tr>
                        <td>${p.id}</td><td>${p.name}</td><td>${p.price.toLocaleString()} ₽</td><td>${p.category}</td>
                        <td>
                            <button class="btn-sm primary" onclick="showProductForm(${p.id},'${p.name.replace(/'/g,"\\'")}',${p.price},'${p.image.replace(/'/g,"\\'")}','${p.category}','${p.brand.replace(/'/g,"\\'")}')">Ред.</button>
                            <button class="btn-sm danger" onclick="deleteProduct(${p.id})">Удал.</button>
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>`;
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Нет прав или ошибка</p>';
    }
}

function showProductForm(id = null, name = '', price = '', image = '', category = '', brand = '') {
    const slot = document.getElementById('product-form-slot');
    const isEdit = id !== null;
    slot.innerHTML = `
        <div class="admin-form">
            <div class="form-group"><label>Название</label><input id="pf-name" value="${name}"></div>
            <div class="form-group"><label>Цена</label><input id="pf-price" type="number" value="${price}"></div>
            <div class="form-group"><label>Категория</label><input id="pf-category" value="${category}"></div>
            <div class="form-group"><label>Бренд</label><input id="pf-brand" value="${brand}"></div>
            <div class="form-group"><label>Изображение URL</label><input id="pf-image" value="${image}"></div>
            <div class="form-group"><label>Или загрузить файл</label><input type="file" id="pf-file" accept="image/*" onchange="previewUpload(this)"></div>
            <div id="pf-preview" style="grid-column:1/-1;"></div>
            <div class="form-actions">
                <button class="btn-sm" onclick="document.getElementById('product-form-slot').innerHTML=''">Отмена</button>
                <button class="btn-sm primary" onclick="saveProduct(${id})">${isEdit ? 'Сохранить' : 'Создать'}</button>
            </div>
        </div>`;
}

function previewUpload(input) {
    const preview = document.getElementById('pf-preview');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => { preview.innerHTML = `<img src="${e.target.result}" style="max-height:100px;border-radius:8px;margin-top:0.5rem;">`; };
        reader.readAsDataURL(input.files[0]);
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const headers = {};
    if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;
    const res = await fetch('/api/upload', { method: 'POST', headers, body: formData });
    if (!res.ok) throw new Error('Upload failed');
    const data = await res.json();
    return data.url;
}

async function saveProduct(id) {
    const fileInput = document.getElementById('pf-file');
    let imageUrl = document.getElementById('pf-image').value;
    if (fileInput.files && fileInput.files[0]) {
        try { imageUrl = await uploadFile(fileInput.files[0]); }
        catch { showToast('Ошибка загрузки файла', 'error'); return; }
    }
    const body = {
        name: document.getElementById('pf-name').value,
        price: parseInt(document.getElementById('pf-price').value),
        image: imageUrl,
        category: document.getElementById('pf-category').value,
        brand: document.getElementById('pf-brand').value,
    };
    if (!body.name || !body.price) { showToast('Название и цена обязательны', 'error'); return; }
    try {
        const url = id ? `/api/admin/products/${id}` : '/api/admin/products';
        const res = await api(url, { method: id ? 'PUT' : 'POST', body: JSON.stringify(body) });
        if (res.ok) { showToast(id ? 'Товар обновлён' : 'Товар создан'); loadAdminProducts(); }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function deleteProduct(id) {
    if (!confirm('Удалить товар?')) return;
    try {
        const res = await api(`/api/admin/products/${id}`, { method: 'DELETE' });
        if (res.ok) { showToast('Товар удалён'); loadAdminProducts(); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

/* ─── Users ─── */
async function loadAdminUsers() {
    const content = document.getElementById('admin-content');
    content.innerHTML = skeleton(6);
    try {
        const [usersRes, rolesRes] = await Promise.all([
            api('/api/admin/users'),
            api('/api/admin/roles')
        ]);
        if (!usersRes.ok) throw new Error();
        const users = await usersRes.json();
        const roles = rolesRes.ok ? await rolesRes.json() : [];

        const myRolesRes = await api(`/api/admin/users/${currentUserId}/roles`);
        const myRoles = myRolesRes.ok ? await myRolesRes.json() : [];
        const isOwner = myRoles.some(r => r.role_name === 'owner');
        const isAdmin = currentRole === 'admin';

        let ownerCount = 0;
        const ownerMap = {};
        const allUserRoles = {};
        for (const u of users) {
            const urRes = await api(`/api/admin/users/${u.id}/roles`);
            const ur = urRes.ok ? await urRes.json() : [];
            allUserRoles[u.id] = ur;
            for (const r of ur) {
                if (r.role_name === 'owner') {
                    ownerCount++;
                    ownerMap[u.id] = ownerCount;
                }
            }
        }

        const roleWeight = { owner: 100, superadmin: 90, content_manager: 70, order_manager: 60, product_manager: 50, user_manager: 40, viewer: 20, user: 10 };
        function maxWeight(userId) {
            const roles = allUserRoles[userId] || [];
            let w = 0;
            for (const r of roles) {
                const rw = roleWeight[r.role_name] || 0;
                if (rw > w) w = rw;
            }
            return w;
        }
        users.sort((a, b) => maxWeight(b.id) - maxWeight(a.id) || a.id - b.id);

        const showActions = isAdmin || isOwner;

        window._usersData = { users, roles, allUserRoles, ownerMap, isOwner, isAdmin, showActions };

        content.innerHTML = `
            <h3 style="margin-bottom:1rem;">Пользователи (${users.length})</h3>
            <div style="display:flex;gap:8px;margin-bottom:1rem;flex-wrap:wrap;align-items:center;">
                <input type="text" id="user-search" placeholder="Поиск по ID, логину или роли..." 
                    style="flex:1;min-width:200px;max-width:400px;padding:8px 12px;background:var(--darker-bg);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;"
                    oninput="filterUsers()">
                <button class="btn-sm primary" onclick="setUserFilter('all')" id="uf-all">Все</button>
                <button class="btn-sm" onclick="setUserFilter('admin')" id="uf-admin">Админы</button>
                <button class="btn-sm" onclick="setUserFilter('user')" id="uf-user">User</button>
            </div>
            <div id="users-table-wrap"></div>`;

        window._userFilter = 'all';
        window._userShowCount = 20;
        renderUsersTable();
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Нет прав или ошибка</p>';
    }
}

function renderUsersTable() {
    const d = window._usersData;
    if (!d) return;
    const filter = window._userFilter || 'all';
    const showCount = window._userShowCount || 20;
    const query = (document.getElementById('user-search')?.value || '').toLowerCase().trim();

    let filtered = d.users.filter(u => {
        if (filter === 'admin') return d.allUserRoles[u.id]?.some(r => ['owner','superadmin'].includes(r.role_name)) || u.role === 'admin';
        if (filter === 'user') return !d.allUserRoles[u.id]?.some(r => ['owner','superadmin'].includes(r.role_name)) && u.role !== 'admin';
        return true;
    });

    if (query) {
        filtered = filtered.filter(u => {
            const roleNames = (d.allUserRoles[u.id] || []).map(r => (r.description || r.role_name).toLowerCase()).join(' ');
            return String(u.id).includes(query) || u.username.toLowerCase().includes(query) || u.role.toLowerCase().includes(query) || roleNames.includes(query);
        });
    }

    const total = filtered.length;
    const visible = filtered.slice(0, showCount);

    const buttons = [
        `<button class="btn-sm${filter==='all'?' primary':''}" onclick="setUserFilter('all')" id="uf-all">Все (${d.users.length})</button>`,
        `<button class="btn-sm${filter==='admin'?' primary':''}" onclick="setUserFilter('admin')" id="uf-admin">Админы (${d.users.filter(u => d.allUserRoles[u.id]?.some(r => ['owner','superadmin'].includes(r.role_name)) || u.role === 'admin').length})</button>`,
        `<button class="btn-sm${filter==='user'?' primary':''}" onclick="setUserFilter('user')" id="uf-user">User (${d.users.filter(u => !d.allUserRoles[u.id]?.some(r => ['owner','superadmin'].includes(r.role_name)) && u.role !== 'admin').length})</button>`,
    ];

    let rows = '';
    for (const u of visible) {
        const userRoles = d.allUserRoles[u.id] || [];
        const roleBadges = userRoles.map(r => {
            const isOwn = r.role_name === 'owner';
            const num = isOwn ? (d.ownerMap[u.id] || '') : '';
            const label = isOwn ? `Владелец${num > 1 ? ' ' + num : ''}` : (r.description || r.role_name);
            const removeBtn = (!isOwn || (d.isOwner && u.id !== currentUserId))
                ? ` <a href="#" onclick="revokeRole(${u.id},'${r.role_name}');return false;" style="color:var(--danger-color);margin-left:4px;">×</a>`
                : '';
            const bg = isOwn ? 'background:rgba(255,193,7,0.2);color:#ffc107;' : '';
            return `<span class="status-badge" style="margin:2px;font-size:0.75rem;${bg}">${label}${removeBtn}</span>`;
        }).join('');

        const tempBadges = userRoles.filter(r => r.expires_at).map(r => {
            const d2 = new Date(r.expires_at);
            const now = new Date();
            const days = Math.ceil((d2 - now) / 86400000);
            return `<span style="font-size:0.7rem;color:${days <= 3 ? 'var(--danger-color)' : 'var(--text-secondary)'};">⏰ ${days > 0 ? days + 'д' : 'истекла'}</span>`;
        }).join(' ');

        if (!d.isAdmin && !d.isOwner) {
            rows += `<tr><td><span class="uc-check" style="display:none;"><input type="checkbox" class="user-check" value="${u.id}"></span></td><td>${u.id}</td><td><div style="display:flex;align-items:center;gap:8px;">${userAvatar(u.username, 'sm')}<span>${u.username}</span></div></td><td style="min-width:200px;">${roleBadges || '<span style="color:var(--text-secondary);">нет ролей</span>'} ${tempBadges}</td></tr>`;
        } else {
            rows += `<tr>
                <td><span class="uc-check" style="display:none;"><input type="checkbox" class="user-check" value="${u.id}" ${u.id === currentUserId ? 'disabled' : ''}></span></td>
                <td>${u.id}</td>
                <td><div style="display:flex;align-items:center;gap:8px;">${userAvatar(u.username, 'sm')}<span>${u.username}</span></div></td>
                <td><span class="status-badge ${u.role === 'admin' ? 'processing' : ''}">${u.role}</span></td>
                <td style="min-width:200px;">${roleBadges || '<span style="color:var(--text-secondary);">нет RBAC ролей</span>'} ${tempBadges}</td>
                <td style="white-space:nowrap;">
                    ${u.id !== currentUserId ? `
                        <button class="btn-sm ${u.role==='user'?'warning':'primary'}" onclick="toggleRole(${u.id},'${u.role}')" style="margin-right:4px;">${u.role==='user'?'Admin':'User'}</button>
                        <select class="btn-sm" style="background:var(--darker-bg);color:var(--text-primary);border:1px solid var(--border-color);width:130px;" onchange="if(this.value){if(confirm('Назначить на 30 дней?'))assignTempRole(${u.id},this.value,30);else assignRole(${u.id},this.value);}this.value='';">
                            <option value="">+ RBAC роль</option>
                            ${d.roles.filter(r => r.name !== 'owner' || d.isOwner).map(r => `<option value="${r.name}">${r.description || r.name}</option>`).join('')}
                        </select>
                    ` : '<span style="color:var(--text-secondary);">—</span>'}
                </td>
            </tr>`;
        }
    }

    const wrap = document.getElementById('users-table-wrap');
    if (!wrap) return;
    const editBtn = (d.isAdmin || d.isOwner) ? `<button class="btn-sm" id="edit-users-btn" onclick="toggleUsersEditMode()">Редактировать</button>` : '';
    wrap.innerHTML = `
        <div style="display:flex;gap:8px;margin-bottom:1rem;flex-wrap:wrap;align-items:center;">
            ${buttons.join('')}
            ${editBtn}
            ${total > showCount ? `<button class="btn-sm" onclick="window._userShowCount=9999;renderUsersTable()">Показать всех (${total})</button>` : ''}
        </div>
        <div id="bulk-toolbar" style="display:none;gap:8px;margin-bottom:1rem;flex-wrap:wrap;align-items:center;padding:10px 12px;background:var(--darker-bg);border:1px solid var(--border-color);border-radius:8px;">
            <button class="btn-sm" onclick="selectAllChecks()">Выбрать все</button>
            <button class="btn-sm" onclick="deselectAllChecks()">Снять выделение</button>
            <select id="bulk-role-select" class="btn-sm" style="background:var(--bg);color:var(--text-primary);border:1px solid var(--border-color);">
                <option value="">Роль для назначения</option>
                ${(d.roles || []).filter(r => !['owner','superadmin'].includes(r.name)).map(r => `<option value="${r.name}">${r.description || r.name}</option>`).join('')}
            </select>
            <select id="bulk-days" class="btn-sm" style="background:var(--bg);color:var(--text-primary);border:1px solid var(--border-color);">
                <option value="">Постоянно</option>
                <option value="7">7 дней</option>
                <option value="14">14 дней</option>
                <option value="30">30 дней</option>
                <option value="90">90 дней</option>
            </select>
            <button class="btn-sm primary" onclick="bulkAssignRole()">Назначить</button>
        </div>
        <div style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:0.5rem;">Показано ${Math.min(showCount, total)} из ${total}</div>
        <table class="admin-table" id="users-table">
            <thead><tr><th><span class="uc-check" style="display:none;"><input type="checkbox" id="check-all" onchange="toggleAllChecks(this.checked)"></span></th><th>ID</th><th>Логин</th>${d.showActions ? '<th>Роль</th>' : ''}<th>RBAC Роли</th>${d.showActions ? '<th>Действия</th>' : ''}</tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
}

function setUserFilter(f) {
    window._userFilter = f;
    window._userShowCount = 20;
    renderUsersTable();
}

function filterUsers() {
    renderUsersTable();
}

function toggleUsersEditMode() {
    const toolbar = document.getElementById('bulk-toolbar');
    const btn = document.getElementById('edit-users-btn');
    if (!toolbar) return;
    const visible = toolbar.style.display !== 'none';
    toolbar.style.display = visible ? 'none' : 'flex';
    document.querySelectorAll('.uc-check').forEach(el => el.style.display = visible ? 'none' : '');
    if (btn) {
        btn.textContent = visible ? 'Редактировать' : 'Скрыть';
        btn.classList.toggle('primary', !visible);
    }
    if (visible) {
        document.querySelectorAll('.user-check').forEach(c => c.checked = false);
    }
}

function toggleAllChecks(checked) {
    document.querySelectorAll('.user-check:not(:disabled)').forEach(c => c.checked = checked);
}
function selectAllChecks() { toggleAllChecks(true); }
function deselectAllChecks() { toggleAllChecks(false); }

async function bulkAssignRole() {
    const ids = Array.from(document.querySelectorAll('.user-check:checked')).map(c => parseInt(c.value));
    const roleName = document.getElementById('bulk-role-select')?.value;
    const days = document.getElementById('bulk-days')?.value;
    if (!ids.length) { showToast('Выберите пользователей', 'error'); return; }
    if (!roleName) { showToast('Выберите роль', 'error'); return; }

    if (days) {
        let assigned = 0;
        for (const uid of ids) {
            const res = await api(`/api/admin/users/${uid}/roles/temp`, {
                method: 'POST', body: JSON.stringify({ role_name: roleName, expires_days: parseInt(days) }),
            });
            if (res.ok) assigned++;
        }
        showToast(`Назначено ${assigned} из ${ids.length} (${roleName} на ${days} дн.)`);
    } else {
        const res = await api('/api/admin/roles/bulk-assign', {
            method: 'POST', body: JSON.stringify({ user_ids: ids, role_name: roleName }),
        });
        if (res.ok) {
            const data = await res.json();
            showToast(data.detail);
        } else {
            const e = await res.json();
            showToast(e.detail || 'Ошибка', 'error');
        }
    }
    renderUsersTable();
}

async function assignTempRole(userId, roleName, days) {
    const res = await api(`/api/admin/users/${userId}/roles/temp`, {
        method: 'POST', body: JSON.stringify({ role_name: roleName, expires_days: days }),
    });
    if (res.ok) { showToast('Роль назначена временно'); renderUsersTable(); }
    else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
}

/* ─── RBAC Tab ─── */
let rbacSubTab = 'matrix';

async function loadRbacTab(sub) {
    if (sub) rbacSubTab = sub;
    const content = document.getElementById('admin-content');
    content.innerHTML = skeleton(6);
    try {
        const [matrixRes, limitsRes] = await Promise.all([
            api('/api/admin/permissions/matrix'),
            api('/api/admin/roles/limits'),
        ]);
        const matrix = matrixRes.ok ? await matrixRes.json() : { roles: [], permissions: {}, matrix: {} };
        const limits = limitsRes.ok ? await limitsRes.json() : {};

        const tabs = [
            { id: 'matrix', label: 'Матрица прав' },
            { id: 'roles', label: 'Роли' },
            { id: 'history', label: 'История' },
            { id: 'settings', label: 'Настройки' },
        ];
        const tabBtns = tabs.map(t =>
            `<button class="btn-sm${rbacSubTab === t.id ? ' primary' : ''}" onclick="loadRbacTab('${t.id}')">${t.label}</button>`
        ).join('');

        content.innerHTML = `
            <h3 style="margin-bottom:1rem;">RBAC — Управление ролями</h3>
            <div style="display:flex;gap:8px;margin-bottom:1.5rem;flex-wrap:wrap;">
                ${tabBtns}
                <span style="margin-left:auto;color:var(--text-secondary);font-size:0.85rem;">
                    Кастомных ролей: ${limits.current_custom_roles || 0}/${limits.max_custom_roles === -1 ? '∞' : limits.max_custom_roles}
                </span>
            </div>
            <div id="rbac-content"></div>`;

        if (rbacSubTab === 'matrix') renderMatrix(matrix);
        else if (rbacSubTab === 'roles') renderRolesList(matrix, limits);
        else if (rbacSubTab === 'history') renderRoleHistory();
        else if (rbacSubTab === 'settings') renderRoleSettings();
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Ошибка загрузки RBAC</p>';
    }
}

function renderMatrix(matrix) {
    const el = document.getElementById('rbac-content');
    const categories = matrix.permissions;
    const roles = matrix.roles;
    const m = matrix.matrix;

    let catLabels = { products: 'Товары', orders: 'Заказы', billing: 'Биллинг', analytics: 'Аналитика', users: 'Пользователи', tenant: 'Магазин', ai: 'ИИ', promos: 'Промо', reviews: 'Отзывы', integrations: 'Интеграции', audit: 'Аудит', support: 'Поддержка', other: 'Другое' };

    let header = '<tr><th style="min-width:150px;">Разрешение</th>';
    for (const r of roles) {
        const style = r.is_system ? 'color:var(--accent-color);' : 'color:var(--success-color);';
        header += `<th style="min-width:100px;text-align:center;${style}">${r.description || r.name}</th>`;
    }
    header += '</tr>';

    let body = '';
    for (const [cat, perms] of Object.entries(categories)) {
        body += `<tr><td colspan="${roles.length + 1}" style="font-weight:700;padding:12px 8px 4px;color:var(--accent-color);font-size:0.9rem;">${catLabels[cat] || cat}</td></tr>`;
        for (const perm of perms) {
            body += `<tr><td style="font-size:0.85rem;">${perm.description}</td>`;
            for (const r of roles) {
                const checked = m[r.id]?.includes(perm.name);
                body += `<td style="text-align:center;"><input type="checkbox" ${checked ? 'checked' : ''} 
                    onchange="togglePerm(${r.id},'${perm.name}',this.checked)" 
                    style="width:18px;height:18px;cursor:pointer;${r.is_system ? 'pointer-events:none;opacity:0.5;' : ''}"></td>`;
            }
            body += '</tr>';
        }
    }

    el.innerHTML = `
        <div style="overflow-x:auto;">
            <table class="admin-table">
                <thead>${header}</thead>
                <tbody>${body}</tbody>
            </table>
        </div>
        <p style="color:var(--text-secondary);font-size:0.8rem;margin-top:0.5rem;">Серые чекбоксы — системные роли (нельзя изменить)</p>`;
}

async function togglePerm(roleId, permName, checked) {
    const matrixRes = await api('/api/admin/permissions/matrix');
    const matrix = await matrixRes.json();
    const currentPerms = matrix.matrix[roleId] || [];
    const newPerms = checked ? [...currentPerms, permName] : currentPerms.filter(p => p !== permName);
    const res = await api(`/api/admin/roles/${roleId}`, {
        method: 'PUT',
        body: JSON.stringify({ permission_names: newPerms }),
    });
    if (!res.ok) {
        const e = await res.json();
        showToast(e.detail || 'Ошибка', 'error');
    }
}

function renderRolesList(matrix, limits) {
    const el = document.getElementById('rbac-content');
    const roles = matrix.roles;
    const permCount = Object.values(matrix.permissions).flat().length;

    let rows = roles.map(r => {
        const count = matrix.matrix[r.id]?.length || 0;
        const style = r.is_system ? 'color:var(--accent-color);' : 'color:var(--success-color);';
        return `<tr>
            <td style="${style}font-weight:600;">${r.name}</td>
            <td>${r.description || '—'}</td>
            <td style="text-align:center;">${count} / ${permCount}</td>
            <td>${r.is_system ? '<span style="color:var(--text-secondary);">Системная</span>' : `<button class="btn-sm" onclick="deleteCustomRole(${r.id})" style="color:var(--danger-color);">Удалить</button>`}</td>
        </tr>`;
    }).join('');

    const canCreate = limits.max_custom_roles === -1 || limits.current_custom_roles < limits.max_custom_roles;

    el.innerHTML = `
        <div style="margin-bottom:1rem;">
            <button class="btn-sm primary" onclick="showCreateRoleForm()" ${!canCreate ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>
                + Создать роль
            </button>
            ${!canCreate ? '<span style="color:var(--danger-color);margin-left:8px;font-size:0.85rem;">Достигнут лимит тарифа</span>' : ''}
        </div>
        <div id="create-role-form"></div>
        <table class="admin-table">
            <thead><tr><th>Имя</th><th>Описание</th><th>Разрешений</th><th>Действия</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
}

async function showCreateRoleForm() {
    const matrixRes = await api('/api/admin/permissions/matrix');
    const matrix = await matrixRes.json();
    const categories = matrix.permissions;

    let permCheckboxes = '';
    for (const [cat, perms] of Object.entries(categories)) {
        permCheckboxes += `<div style="margin-top:8px;"><strong style="font-size:0.85rem;color:var(--accent-color);">${cat}</strong><br>`;
        for (const p of perms) {
            permCheckboxes += `<label style="display:inline-flex;gap:4px;margin:4px 8px 0 0;font-size:0.85rem;cursor:pointer;">
                <input type="checkbox" value="${p.name}" class="cr-perm"> ${p.description}</label>`;
        }
        permCheckboxes += '</div>';
    }

    document.getElementById('create-role-form').innerHTML = `
        <div style="background:var(--darker-bg);border:1px solid var(--border-color);border-radius:8px;padding:1rem;margin-bottom:1rem;">
            <h4 style="margin-bottom:0.5rem;">Новая роль</h4>
            <div class="form-group"><label>Имя (latin)</label><input id="cr-name" placeholder="delivery_manager" style="width:100%;padding:8px;background:var(--bg);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;"></div>
            <div class="form-group"><label>Описание</label><input id="cr-desc" placeholder="Менеджер доставки" style="width:100%;padding:8px;background:var(--bg);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;"></div>
            <div class="form-group"><label>Разрешения</label>${permCheckboxes}</div>
            <div style="display:flex;gap:8px;margin-top:8px;">
                <button class="btn-sm primary" onclick="createCustomRole()">Создать</button>
                <button class="btn-sm" onclick="document.getElementById('create-role-form').innerHTML=''">Отмена</button>
            </div>
        </div>`;
}

async function createCustomRole() {
    const name = document.getElementById('cr-name').value.trim();
    const desc = document.getElementById('cr-desc').value.trim();
    const perms = Array.from(document.querySelectorAll('.cr-perm:checked')).map(c => c.value);
    if (!name) { showToast('Введите имя роли', 'error'); return; }
    const res = await api('/api/admin/roles', {
        method: 'POST', body: JSON.stringify({ name, description: desc, permission_names: perms }),
    });
    if (res.ok) { showToast('Роль создана'); loadRbacTab('roles'); }
    else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
}

async function deleteCustomRole(roleId) {
    if (!confirm('Удалить роль?')) return;
    const res = await api(`/api/admin/roles/${roleId}`, { method: 'DELETE' });
    if (res.ok) { showToast('Роль удалена'); loadRbacTab('roles'); }
    else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
}

async function renderRoleHistory() {
    const el = document.getElementById('rbac-content');
    const res = await api('/api/admin/roles/history?limit=50');
    if (!res.ok) { el.innerHTML = '<p>Ошибка загрузки</p>'; return; }
    const logs = await res.json();
    if (!logs.length) { el.innerHTML = '<p style="color:var(--text-secondary);">История пуста</p>'; return; }
    const rows = logs.map(l => `<tr>
        <td>${l.id}</td>
        <td>${l.action === 'role_assigned' ? '✅ Назначена' : '❌ Снята'}</td>
        <td style="font-size:0.85rem;">${l.details || '—'}</td>
        <td>User #${l.user_id}</td>
        <td>${l.created_at ? new Date(l.created_at).toLocaleString('ru-RU') : '—'}</td>
    </tr>`).join('');
    el.innerHTML = `
        <table class="admin-table">
            <thead><tr><th>ID</th><th>Действие</th><th>Детали</th><th>Кто</th><th>Когда</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
}

async function renderRoleSettings() {
    const el = document.getElementById('rbac-content');
    const [limitsRes, matrixRes] = await Promise.all([
        api('/api/admin/roles/limits'),
        api('/api/admin/permissions/matrix'),
    ]);
    const limits = limitsRes.ok ? await limitsRes.json() : {};
    const matrix = matrixRes.ok ? await matrixRes.json() : {};
    const roles = matrix.roles || [];

    el.innerHTML = `
        <div style="background:var(--darker-bg);border:1px solid var(--border-color);border-radius:8px;padding:1.5rem;max-width:500px;">
            <h4 style="margin-bottom:1rem;">Настройки RBAC</h4>
            <div class="form-group">
                <label>Роль по умолчанию для новых пользователей</label>
                <select id="default-role-select" style="width:100%;padding:8px;background:var(--bg);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;">
                    <option value="">Не задана</option>
                    ${roles.filter(r => !['owner','superadmin'].includes(r.name)).map(r => `<option value="${r.name}">${r.description || r.name}</option>`).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Лимит тарифа</label>
                <p style="color:var(--text-secondary);font-size:0.9rem;">Кастомных ролей: <strong>${limits.current_custom_roles || 0}</strong> / ${limits.max_custom_roles === -1 ? '∞' : limits.max_custom_roles}</p>
            </div>
            <button class="btn-sm primary" onclick="saveDefaultRole()">Сохранить</button>
        </div>`;

    const drRes = await api('/api/admin/roles/full');
    if (drRes.ok) {
        const rData = await drRes.json();
    }
}

async function saveDefaultRole() {
    const roleName = document.getElementById('default-role-select').value || null;
    const res = await api('/api/admin/tenant/default-role', {
        method: 'PATCH', body: JSON.stringify({ role_name: roleName }),
    });
    if (res.ok) { showToast('Сохранено'); }
    else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
}

async function toggleRole(userId, currentRole) {
    const newRole = currentRole === 'user' ? 'admin' : 'user';
    try {
        const res = await api(`/api/admin/users/${userId}/role`, {
            method: 'PATCH', body: JSON.stringify({ role: newRole })
        });
        if (res.ok) { showToast('Роль обновлена'); loadAdminUsers(); }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function assignRole(userId, roleName) {
    try {
        const res = await api(`/api/admin/users/${userId}/roles`, {
            method: 'POST',
            headers: { 'X-Tenant-ID': '1' },
            body: JSON.stringify({ role_name: roleName })
        });
        const data = await res.json();
        if (res.ok || res.status === 201) { showToast(data.detail); loadAdminUsers(); }
        else { showToast(data.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function revokeRole(userId, roleName) {
    try {
        const res = await api(`/api/admin/users/${userId}/roles/${roleName}`, {
            method: 'DELETE',
            headers: { 'X-Tenant-ID': '1' }
        });
        const data = await res.json();
        if (res.ok) { showToast(data.detail); loadAdminUsers(); }
        else { showToast(data.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

/* ─── Orders ─── */
async function loadAdminOrders() {
    const content = document.getElementById('admin-content');
    content.innerHTML = skeleton(6);
    try {
        const res = await api('/api/admin/orders');
        if (!res.ok) throw new Error();
        const orders = await res.json();
        if (!orders.length) { content.innerHTML = '<p style="margin-top:1rem;">Заказов пока нет</p>'; return; }
        content.innerHTML = `<h3 style="margin-bottom:1rem;">Заказы (${orders.length})</h3>` +
            orders.map(o => `
                <div class="order-card">
                    <div class="order-card-header">
                        <div>
                            <strong>#${o.id}</strong> — ${o.username} — ${o.total.toLocaleString()} ₽
                            <span class="status-badge ${o.status}" style="margin-left:0.5rem;">${o.status}</span>
                        </div>
                        <div>
                            <select class="btn-sm" style="background:var(--darker-bg);color:var(--text-primary);border:1px solid var(--border-color);" onchange="changeOrderStatus(${o.id}, this.value)">
                                ${['pending','processing','shipped','delivered','cancelled'].map(s => `<option value="${s}" ${s===o.status?'selected':''}>${s}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="order-items-list">
                        ${o.items.map(i => `${i.product_name} × ${i.quantity} — ${i.price.toLocaleString()} ₽`).join(', ')}
                    </div>
                    <div style="font-size:0.85rem;color:var(--text-secondary);">Адрес: ${o.address} | ${o.created_at.split('T')[0]}</div>
                </div>`).join('');
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Нет прав или ошибка</p>';
    }
}

async function changeOrderStatus(orderId, status) {
    try {
        const res = await api(`/api/admin/orders/${orderId}/status`, {
            method: 'PATCH', body: JSON.stringify({ status })
        });
        if (res.ok) { showToast('Статус обновлён'); loadAdminOrders(); }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}
/* ─── Store Settings ─── */
const THEME_NAMES = { midnight: 'Midnight', light: 'Light', nature: 'Nature', rose: 'Rose', cyber: 'Cyber', minimal: 'Minimal' };
const THEME_COLORS = {
    midnight: ['#0f172a','#3b82f6'],
    light: ['#f8fafc','#3b82f6'],
    nature: ['#059669','#10b981'],
    rose: ['#e11d48','#f43f5e'],
    cyber: ['#7c3aed','#a855f7'],
    minimal: ['#fafafa','#737373'],
};

async function loadStoreSettings() {
    const content = document.getElementById('admin-content');
    content.innerHTML = skeleton(6);
    try {
        const res = await api('/api/store/settings');
        if (!res.ok) throw new Error();
        const s = await res.json();
        const themeOptions = THEMES.map(t => {
            const [bg, accent] = THEME_COLORS[t] || ['#333','#3b82f6'];
            return `<div class="theme-pick ${s.theme === t ? 'active' : ''}" data-theme="${t}" onclick="previewTheme('${t}')">
                <span class="theme-dot" style="background:linear-gradient(135deg,${bg},${accent})"></span>
                ${THEME_NAMES[t]}
            </div>`;
        }).join('');
        content.innerHTML = `
            <div class="profile-form-card" style="max-width:600px;">
                <h3>Настройки магазина</h3>
                <div class="admin-form">
                    <div class="form-group" style="grid-column:1/-1;">
                        <label>Название магазина</label>
                        <input id="store-name" value="${s.store_name || ''}" placeholder="Мой магазин">
                    </div>
                    <div class="form-group" style="grid-column:1/-1;">
                        <label>URL логотипа</label>
                        <input id="store-logo" value="${s.logo_url || ''}" placeholder="https://example.com/logo.png">
                    </div>
                    <div class="form-group" style="grid-column:1/-1;">
                        <label>Тема оформления</label>
                        <div class="theme-picks">${themeOptions}</div>
                    </div>
                    <div class="form-actions">
                        <button class="btn-sm primary" onclick="saveStoreSettings()">Сохранить</button>
                    </div>
                </div>
            </div>`;
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Ошибка загрузки настроек</p>';
    }
}

function previewTheme(theme) {
    setTheme(theme);
    document.querySelectorAll('.theme-pick').forEach(p => {
        p.classList.toggle('active', p.dataset.theme === theme);
    });
}

async function saveStoreSettings() {
    const name = document.getElementById('store-name')?.value;
    const logo = document.getElementById('store-logo')?.value;
    const activeTheme = document.querySelector('.theme-pick.active')?.dataset.theme || 'midnight';
    try {
        const res = await api('/api/store/settings', {
            method: 'PUT',
            body: JSON.stringify({ store_name: name, logo_url: logo, theme: activeTheme })
        });
        if (res.ok) {
            showToast('Настройки магазина сохранены');
            setTheme(activeTheme);
        } else {
            const e = await res.json();
            showToast(e.detail || 'Ошибка', 'error');
        }
    } catch { showToast('Ошибка сервера', 'error'); }
}

function showToast(message, type = 'success', duration) {
    const icons = { success: '✓', error: '✗', info: 'ℹ' };
    const toast = document.getElementById('toast');
    toast.innerHTML = `<span class="toast-icon">${icons[type] || ''}</span><span>${message}</span><button class="toast-close" onclick="this.parentElement.classList.remove('show')">×</button>`;
    toast.className = `toast ${type}`;
    setTimeout(() => toast.classList.add('show'), 10);
    clearTimeout(window._toastTimer);
    window._toastTimer = setTimeout(() => toast.classList.remove('show'), duration || 3500);
}

function getAvatarColor(name) {
    const colors = ['#6366f1','#f59e0b','#10b981','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316','#3b82f6','#84cc16'];
    let h = 0;
    for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
    return colors[Math.abs(h) % colors.length];
}

function userAvatar(name, size = '') {
    const initials = name.split(/[_\s]/).map(w => w[0]).join('').slice(0, 2).toUpperCase();
    const cls = size ? `user-avatar ${size}` : 'user-avatar';
    return `<span class="${cls}" style="background:${getAvatarColor(name)};">${initials}</span>`;
}

function skeleton(rows = 5) {
    let html = '';
    for (let i = 0; i < rows; i++) {
        html += `<div class="skeleton-row">
            <div class="skeleton skeleton-avatar"></div>
            <div class="skeleton-cell"><div class="skeleton skeleton-text w60"></div><div class="skeleton skeleton-text w40"></div></div>
            <div class="skeleton skeleton-cell"><div class="skeleton skeleton-text w80"></div></div>
            <div class="skeleton skeleton-badge"></div>
        </div>`;
    }
    return html;
}

function skeletonCards(n = 4) {
    let html = '<div class="admin-panel">';
    for (let i = 0; i < n; i++) {
        html += `<div class="skeleton-card"><div class="skeleton skeleton-text w40" style="margin:0 auto;height:12px;"></div><div class="skeleton skeleton-text w60" style="margin:8px auto;height:32px;"></div></div>`;
    }
    return html + '</div>';
}

/* ===== Flash Sales ===== */
async function loadFlashSales() {
    const banner = document.getElementById('flash-sale-banner');
    if (!banner) return;
    try {
        const res = await api('/api/flash-sales/active');
        if (!res.ok) return;
        const sales = await res.json();
        if (!sales.length) { banner.style.display = 'none'; return; }
        banner.style.display = 'block';
        banner.innerHTML = sales.map(s => `
            <div style="background:linear-gradient(135deg,#f59e0b,#ef4444);border-radius:12px;padding:1.5rem;color:#fff;margin-bottom:1rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;">
                    <div>
                        <h3 style="margin:0;">⚡ ${s.product_name}</h3>
                        <p style="margin:0.3rem 0 0;">${s.original_price.toLocaleString()} ₽ → <strong style="font-size:1.4rem;">${s.sale_price.toLocaleString()} ₽</strong></p>
                        <span style="background:rgba(0,0,0,0.3);padding:3px 10px;border-radius:20px;font-size:0.85rem;">-${s.discount_percent}%</span>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.85rem;opacity:0.9;" data-i18n="flash_ends_in">До конца:</div>
                        <div class="flash-timer" data-ends="${s.ends_in_seconds}" style="font-size:1.3rem;font-weight:bold;font-family:monospace;"></div>
                        <button class="cta-button" style="margin-top:0.5rem;padding:0.5rem 1.5rem;font-size:0.9rem;" onclick="showProductDetail(${s.product_id})">${t('add_cart')}</button>
                    </div>
                </div>
            </div>
        `).join('');
        startFlashTimers();
    } catch { banner.style.display = 'none'; }
}

function startFlashTimers() {
    document.querySelectorAll('.flash-timer').forEach(el => {
        let secs = parseInt(el.dataset.ends) || 0;
        const update = () => {
            if (secs <= 0) { el.innerHTML = '<span class="timer-block">00</span>:<span class="timer-block">00</span>:<span class="timer-block">00</span>'; return; }
            const h = Math.floor(secs / 3600);
            const m = Math.floor((secs % 3600) / 60);
            const s = secs % 60;
            el.innerHTML = `<span class="timer-block">${String(h).padStart(2,'0')}</span>:<span class="timer-block">${String(m).padStart(2,'0')}</span>:<span class="timer-block">${String(s).padStart(2,'0')}</span>`;
            secs--;
        };
        update();
        setInterval(update, 1000);
    });
}

/* ===== Loyalty ===== */
async function loadLoyalty() {
    const el = document.getElementById('loyalty-content');
    if (!el || !accessToken) { if (el) el.innerHTML = '<p style="color:var(--text-secondary);">Войдите</p>'; return; }
    try {
        const res = await api('/api/loyalty/stats');
        if (!res.ok) return;
        const s = await res.json();
        el.innerHTML = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
                <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;text-align:center;">
                    <div style="font-size:0.85rem;color:var(--text-secondary);">${t('loyalty_level')}</div>
                    <div style="font-size:1.5rem;font-weight:bold;color:var(--primary-color);">${s.level_label}</div>
                </div>
                <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;text-align:center;">
                    <div style="font-size:0.85rem;color:var(--text-secondary);">${t('loyalty_points')}</div>
                    <div style="font-size:1.5rem;font-weight:bold;color:var(--secondary-color);">${s.points}</div>
                </div>
                <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;text-align:center;">
                    <div style="font-size:0.85rem;color:var(--text-secondary);">${t('loyalty_cashback')}</div>
                    <div style="font-size:1.5rem;font-weight:bold;color:#22c55e;">${s.cashback_percent}%</div>
                </div>
                ${s.next_level ? `<div style="background:var(--darker-bg);padding:1rem;border-radius:8px;text-align:center;">
                    <div style="font-size:0.85rem;color:var(--text-secondary);">${t('loyalty_next')}</div>
                    <div style="font-size:1.1rem;font-weight:bold;">${s.next_level} (${s.points_to_next} pts)</div>
                </div>` : ''}
            </div>`;
    } catch {}
}

/* ===== Referral ===== */
async function loadReferral() {
    const el = document.getElementById('referral-content');
    if (!el || !accessToken) { if (el) el.innerHTML = '<p style="color:var(--text-secondary);">Войдите</p>'; return; }
    try {
        const res = await api('/api/referral/stats');
        if (!res.ok) return;
        const s = await res.json();
        el.innerHTML = `
            <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;margin-bottom:1rem;">
                <div style="font-size:0.85rem;color:var(--text-secondary);">${t('referral_code')}</div>
                <div style="font-size:1.3rem;font-weight:bold;font-family:monospace;color:var(--primary-color);cursor:pointer;" onclick="navigator.clipboard.writeText('${s.referral_code}');showToast('Скопировано!')">${s.referral_code} <i class="fas fa-copy" style="font-size:0.9rem;"></i></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">
                <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;text-align:center;">
                    <div style="font-size:0.85rem;color:var(--text-secondary);">${t('referral_count')}</div>
                    <div style="font-size:1.5rem;font-weight:bold;">${s.total_referrals}</div>
                </div>
                <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;text-align:center;">
                    <div style="font-size:0.85rem;color:var(--text-secondary);">${t('referral_earnings')}</div>
                    <div style="font-size:1.5rem;font-weight:bold;color:#22c55e;">${s.referral_earnings.toLocaleString()} ₽</div>
                </div>
            </div>
            <div style="display:flex;gap:0.5rem;">
                <input type="text" id="referral-input" placeholder="${t('referral_redeem')}" style="flex:1;padding:0.6rem 1rem;border-radius:8px;border:1px solid var(--border-color);background:var(--darker-bg);color:var(--text-primary);">
                <button class="btn-sm primary" onclick="redeemReferral()"><i class="fas fa-gift"></i></button>
            </div>`;
    } catch {}
}

async function redeemReferral() {
    const code = document.getElementById('referral-input')?.value;
    if (!code) { showToast('Введите код', 'error'); return; }
    try {
        const res = await api('/api/referral/redeem', { method: 'POST', body: JSON.stringify({ code }) });
        if (res.ok) { const d = await res.json(); showToast(d.message); loadReferral(); loadLoyalty(); }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

/* ===== 2FA ===== */
async function load2FA() {
    const el = document.getElementById('tfa-content');
    if (!el || !accessToken) { if (el) el.innerHTML = '<p style="color:var(--text-secondary);">Войдите</p>'; return; }
    try {
        const res = await api('/api/2fa/status');
        if (!res.ok) return;
        const s = await res.json();
        el.innerHTML = s.enabled
            ? `<p style="color:#22c55e;"><i class="fas fa-shield-alt"></i> 2FA активна</p>
               <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
                   <input type="text" id="tfa-disable-code" placeholder="${t('tfa_code')}" style="flex:1;padding:0.6rem;border-radius:8px;border:1px solid var(--border-color);background:var(--darker-bg);color:var(--text-primary);">
                   <button class="btn-sm danger" onclick="disable2FA()">${t('tfa_disable')}</button>
               </div>`
            : `<p style="color:var(--text-secondary);margin-bottom:1rem;">${t('tfa_scan')}</p>
               <button class="btn-sm primary" onclick="setup2FA()"><i class="fas fa-shield-alt"></i> ${t('tfa_enable')}</button>
               <div id="tfa-setup" style="margin-top:1rem;"></div>`;
    } catch {}
}

async function setup2FA() {
    try {
        const res = await api('/api/2fa/setup');
        if (!res.ok) { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); return; }
        const d = await res.json();
        document.getElementById('tfa-setup').innerHTML = `
            <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;text-align:center;">
                <p style="margin-bottom:0.5rem;">Секрет: <code>${d.secret}</code></p>
                <a href="${d.otpauth_url}" target="_blank" style="color:var(--primary-color);">Открыть в authenticator</a>
                <div style="display:flex;gap:0.5rem;margin-top:1rem;">
                    <input type="text" id="tfa-verify-code" placeholder="${t('tfa_code')}" style="flex:1;padding:0.6rem;border-radius:8px;border:1px solid var(--border-color);background:var(--darker-bg);color:var(--text-primary);">
                    <button class="btn-sm primary" onclick="verify2FA()">Подтвердить</button>
                </div>
            </div>`;
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function verify2FA() {
    const code = document.getElementById('tfa-verify-code')?.value;
    if (!code) { showToast('Введите код', 'error'); return; }
    try {
        const res = await api('/api/2fa/verify', { method: 'POST', body: JSON.stringify({ code }) });
        if (res.ok) { showToast('2FA включена!'); load2FA(); }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

async function disable2FA() {
    const code = document.getElementById('tfa-disable-code')?.value;
    if (!code) { showToast('Введите код', 'error'); return; }
    try {
        const res = await api('/api/2fa/disable', { method: 'POST', body: JSON.stringify({ code }) });
        if (res.ok) { showToast('2FA отключена'); load2FA(); }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
}

/* ===== Order Tracking ===== */
async function trackOrder(orderId) {
    const el = document.getElementById(`tracking-${orderId}`);
    if (!el) return;
    if (el.style.display === 'block') { el.style.display = 'none'; return; }
    el.style.display = 'block';
    el.innerHTML = '<div class="spinner"></div>';
    try {
        const res = await api(`/api/tracking/${orderId}`);
        if (!res.ok) throw new Error();
        const t_data = await res.json();
        el.innerHTML = `
            <div style="padding:1rem;background:var(--darker-bg);border-radius:8px;margin-top:0.5rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
                    <span class="status-badge ${t_data.status}">${t_data.status}</span>
                    ${t_data.tracking_number ? `<span style="font-size:0.85rem;color:var(--text-secondary);">${t('tracking_number')}: <code>${t_data.tracking_number}</code></span>` : ''}
                </div>
                ${t_data.history.length ? `<div style="border-left:2px solid var(--primary-color);padding-left:1rem;">
                    ${t_data.history.map(h => `
                        <div style="margin-bottom:0.75rem;position:relative;">
                            <div style="width:10px;height:10px;background:var(--primary-color);border-radius:50%;position:absolute;left:-1.55rem;top:0.3rem;"></div>
                            <div style="font-weight:600;">${h.status}</div>
                            ${h.comment ? `<div style="font-size:0.85rem;color:var(--text-secondary);">${h.comment}</div>` : ''}
                            <div style="font-size:0.75rem;color:var(--text-secondary);">${new Date(h.created_at).toLocaleString()}</div>
                        </div>
                    `).join('')}
                </div>` : '<p style="color:var(--text-secondary);">Нет данных</p>'}
            </div>`;
    } catch { el.innerHTML = '<p style="color:var(--danger-color);">Ошибка загрузки</p>'; }
}

/* ===== Browser Notifications ===== */
let notifWs = null;

function initNotifications() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    if (accessToken) connectNotifWS();
}

function connectNotifWS() {
    if (notifWs) return;
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    notifWs = new WebSocket(`${proto}//${location.host}/ws?token=${accessToken}`);
    notifWs.onmessage = e => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'order_created') {
            sendNotification(storeName, `Заказ #${msg.order_id} на сумму ${msg.total.toLocaleString()} ₽ оформлен!`);
            updateCartCount();
        } else if (msg.type === 'order_status_changed') {
            sendNotification(storeName, `Заказ #${msg.order_id}: статус изменён на "${msg.status}"`);
        }
    };
    notifWs.onclose = () => { notifWs = null; setTimeout(connectNotifWS, 5000); };
    notifWs.onerror = () => { notifWs = null; };
}

function sendNotification(title, body, url = '/') {
    if ('Notification' in window && Notification.permission === 'granted') {
        const n = new Notification(title, { body, icon: '/static/favicon.png', tag: 'myshop' });
        n.onclick = () => { window.focus(); window.open(url, '_blank'); };
    }
}

/* ===== Ad Banners ===== */
async function loadAdBanners() {
    const el = document.getElementById('ad-banners');
    if (!el) return;
    try {
        const res = await api('/api/banners/active');
        if (!res.ok) return;
        const banners = await res.json();
        if (!banners.length) { el.style.display = 'none'; return; }
        el.style.display = 'block';
        el.innerHTML = banners.map(b => `
            <a href="${b.link_url || '#'}" target="_blank" style="display:block;margin-bottom:1rem;border-radius:12px;overflow:hidden;">
                <img src="${b.image_url}" alt="${b.title}" style="width:100%;height:120px;object-fit:cover;">
            </a>
        `).join('');
    } catch { el.style.display = 'none'; }
}

/* ===== Wishlist Alerts ===== */
async function checkWishlistAlerts() {
    if (!accessToken) return;
    try {
        const res = await api('/api/wishlist/alerts');
        if (!res.ok) return;
        const alerts = await res.json();
        alerts.forEach(a => {
            const type = a.type === 'price_drop' ? 'success' : a.type === 'low_stock' ? 'warning' : 'error';
            showToast(a.message, type);
            sendNotification(storeName, a.message, `/product/${a.product_id}`);
        });
    } catch {}
}

/* ===== Buyer Level Display ===== */
function getBuyerLevelLabel(level) {
    const labels = { new: 'Новичок', regular: 'Постоянный', vip: 'VIP', premium: 'Премиум' };
    return labels[level] || level;
}

function getBuyerLevelColor(level) {
    const colors = { new: '#94a3b8', regular: '#3b82f6', vip: '#f59e0b', premium: '#ec4899' };
    return colors[level] || '#94a3b8';
}

/* ===== Period Comparison ===== */
async function loadPeriodComparison() {
    const el = document.getElementById('period-comparison');
    if (!el) return;
    try {
        const res = await api('/api/admin/analytics/period-comparison');
        if (!res.ok) return;
        const d = await res.json();
        const ordersArrow = d.diff_orders >= 0 ? '↑' : '↓';
        const revenueArrow = d.diff_revenue >= 0 ? '↑' : '↓';
        const ordersColor = d.diff_orders >= 0 ? '#22c55e' : '#ef4444';
        const revenueColor = d.diff_revenue >= 0 ? '#22c55e' : '#ef4444';
        el.innerHTML = `
            <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;margin-top:1rem;">
                <h4 style="margin:0 0 0.75rem;">📊 Эта неделя vs прошлая</h4>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
                    <div>
                        <div style="font-size:0.85rem;color:var(--text-secondary);">Заказы</div>
                        <div style="font-size:1.3rem;font-weight:bold;">${d.current.orders}</div>
                        <div style="color:${ordersColor};font-size:0.9rem;">${ordersArrow} ${Math.abs(d.diff_orders_pct)}% (${d.diff_orders >= 0 ? '+' : ''}${d.diff_orders})</div>
                    </div>
                    <div>
                        <div style="font-size:0.85rem;color:var(--text-secondary);">Выручка</div>
                        <div style="font-size:1.3rem;font-weight:bold;">${d.current.revenue.toLocaleString()} ₽</div>
                        <div style="color:${revenueColor};font-size:0.9rem;">${revenueArrow} ${Math.abs(d.diff_revenue_pct)}% (${d.diff_revenue >= 0 ? '+' : ''}${d.diff_revenue.toLocaleString()} ₽)</div>
                    </div>
                </div>
            </div>`;
    } catch {}
}

/* ===== Orders Map ===== */
let ordersMapInstance = null;

async function loadOrdersMap() {
    const el = document.getElementById('orders-map');
    if (!el || typeof L === 'undefined') return;
    try {
        const res = await api('/api/admin/analytics/map');
        if (!res.ok) return;
        const points = await res.json();

        if (ordersMapInstance) { ordersMapInstance.remove(); ordersMapInstance = null; }
        el.innerHTML = '';

        ordersMapInstance = L.map(el, { attributionControl: false, zoomControl: true }).setView([55.7558, 37.6173], 3);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
        }).addTo(ordersMapInstance);

        if (!points.length) {
            el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary);">Нет данных для отображения</div>';
            return;
        }

        const maxOrders = Math.max(...points.map(p => p.orders), 1);
        points.forEach(p => {
            const radius = Math.max(8, (p.orders / maxOrders) * 30);
            const marker = L.circleMarker([p.lat, p.lng], {
                radius,
                fillColor: '#3b82f6',
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.7,
            }).addTo(ordersMapInstance);
            marker.bindPopup(`
                <div style="text-align:center;min-width:120px;">
                    <strong style="font-size:1.1rem;">${p.city}</strong><br>
                    <span style="color:#3b82f6;">${p.orders} заказов</span><br>
                    <span style="color:#22c55e;">${p.revenue.toLocaleString()} ₽</span>
                </div>
            `);
        });

        setTimeout(() => ordersMapInstance.invalidateSize(), 100);
    } catch {}
}
async function loadFunnel() {
    const el = document.getElementById('funnel-chart');
    if (!el) return;
    try {
        const res = await api('/api/admin/analytics/funnel');
        if (!res.ok) return;
        const d = await res.json();
        const maxCount = Math.max(...d.stages.map(s => s.count), 1);
        el.innerHTML = `
            <div style="background:var(--darker-bg);padding:1rem;border-radius:8px;margin-top:1rem;">
                <h4 style="margin:0 0 0.75rem;">🔻 Воронка конверсии (${d.overall_conversion}% overall)</h4>
                ${d.stages.map((s, i) => `
                    <div style="margin-bottom:0.5rem;">
                        <div style="display:flex;justify-content:space-between;font-size:0.85rem;">
                            <span>${s.name}</span>
                            <span style="color:var(--text-secondary);">${s.count} (${s.conversion_from_prev}%)</span>
                        </div>
                        <div style="background:var(--border-color);height:8px;border-radius:4px;overflow:hidden;">
                            <div style="background:linear-gradient(90deg,var(--primary-color),var(--secondary-color));height:100%;width:${Math.max(s.count / maxCount * 100, 2)}%;border-radius:4px;transition:width 0.5s;"></div>
                        </div>
                    </div>
                `).join('')}
            </div>`;
    } catch {}
}
/* ===== Modal close handlers ===== */
document.getElementById('auth-modal')?.addEventListener('click', function (e) {
    if (e.target === this) closeAuthModal();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAuthModal(); });

/* ===== Theme Switcher ===== */
const THEMES = ['midnight', 'light', 'nature', 'rose', 'cyber', 'minimal'];

function setTheme(theme) {
    if (!THEMES.includes(theme)) theme = 'midnight';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('myshop-theme', theme);
    const link = document.getElementById('theme-css');
    if (link) link.href = `/static/css/themes/${theme}.css`;
    document.querySelectorAll('.theme-option').forEach(o => {
        o.classList.toggle('active', o.dataset.theme === theme);
    });
    document.querySelectorAll('.theme-pick').forEach(p => {
        p.classList.toggle('active', p.dataset.theme === theme);
    });
    document.getElementById('theme-menu')?.classList.remove('active');
}

function toggleThemeMenu() {
    document.getElementById('theme-menu')?.classList.toggle('active');
}

function loadTheme() {
    const saved = localStorage.getItem('myshop-theme') || 'midnight';
    setTheme(saved);
}

document.addEventListener('click', e => {
    const menu = document.getElementById('theme-menu');
    const toggle = document.querySelector('.theme-toggle');
    if (menu && !menu.contains(e.target) && !toggle?.contains(e.target)) {
        menu.classList.remove('active');
    }
});

loadTheme();
