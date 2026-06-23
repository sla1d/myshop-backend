const API_BASE = '';

let accessToken = localStorage.getItem('accessToken') || '';
let currentUser = localStorage.getItem('currentUser') || '';
let currentRole = localStorage.getItem('currentRole') || '';

document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
    loadCategories();
    loadBrands();
    updateHeader();
    updateCartCount();
});

/* ===== API Helper ===== */
async function api(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }
    return fetch(`${API_BASE}${url}`, { ...options, headers });
}

/* ===== Navigation ===== */
function showSection(sectionId) {
    document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(sectionId);
    if (target) target.classList.add('active');

    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const link = document.querySelector(`.nav-links a[onclick*="'${sectionId}'"]`);
    if (link) link.classList.add('active');

    if (sectionId === 'cart') loadCart();
    if (sectionId === 'profile') { loadProfile(); loadProfileOrders(); }
    if (sectionId === 'wishlist') loadWishlist();
    if (sectionId === 'catalog') loadFilteredProducts();
    if (sectionId === 'catalog') loadFilteredProducts();
}

/* ===== Products & Search ===== */
let searchTimeout = null;

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadFilteredProducts, 300);
}

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
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    if (brand) params.set('brand', brand);
    if (minRating) params.set('min_rating', minRating);
    if (sort) params.set('sort', sort);
    const qs = params.toString();
    const url = '/api/products' + (qs ? '?' + qs : '');

    const grid = document.getElementById('products-grid');
    grid.innerHTML = '';
    try {
        const res = await api(url);
        if (!res.ok) throw new Error();
        const products = await res.json();
        if (!products.length) {
            grid.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-secondary);">
                <i class="fas fa-search" style="font-size:3rem;margin-bottom:1rem;"></i>
                <p>Товары не найдены</p></div>`;
            return;
        }
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card fade-in';
            card.style.animationDelay = `${p.id * 0.05}s`;
            card.style.cursor = 'pointer';
            card.onclick = () => showProductDetail(p.id);
            card.innerHTML = `
                <div class="product-image">
                    <img src="${p.image}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover;">
                    <button class="wishlist-btn" onclick="toggleWishlist(${p.id}, event)"><i class="far fa-heart"></i></button>
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
        grid.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--danger-color);">
            <i class="fas fa-exclamation-triangle" style="font-size:3rem;margin-bottom:1rem;"></i>
            <p>Не удалось загрузить товары.</p></div>`;
    }
}

/* ===== Product Detail & Reviews ===== */
let currentProductId = null;
let selectedRating = 0;

async function showProductDetail(productId) {
    currentProductId = productId;
    showSection('product-detail');
    const content = document.getElementById('product-detail-content');
    const reviewsEl = document.getElementById('product-reviews');
    content.innerHTML = '<div class="spinner"></div>';
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
                <img src="${product.image}" alt="${product.name}">
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
        } else {
            const err = await res.json();
            showToast(err.detail || 'Ошибка', 'error');
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-shopping-cart"></i> В корзину'; }
        }
    } catch {
        showToast('Ошибка сервера', 'error');
    }
}

async function loadCart() {
    const container = document.getElementById('cart-items');
    const totalBlock = document.getElementById('cart-total');
    const totalAmount = document.getElementById('total-amount');
    const totalItems = document.getElementById('total-items');

    if (!accessToken) {
        container.innerHTML = `<div class="empty-cart"><i class="fas fa-lock"></i>
            <p>Войдите, чтобы увидеть корзину</p>
            <button class="cta-button" onclick="showAuthModal()">Войти</button></div>`;
        totalBlock.style.display = 'none';
        return;
    }
    try {
        const res = await api('/api/cart');
        if (!res.ok) throw new Error();
        const data = await res.json();
        const items = data.items;
        if (!items.length) {
            container.innerHTML = `<div class="empty-cart"><i class="fas fa-shopping-cart"></i><p>Корзина пуста</p></div>`;
            totalBlock.style.display = 'none';
            return;
        }
        container.innerHTML = '';
        items.forEach(item => {
            const el = document.createElement('div');
            el.className = 'cart-item fade-in';
            el.innerHTML = `
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.name}</div>
                    <div class="cart-item-price">${item.price.toLocaleString()} ₽ × ${item.quantity} = <strong>${(item.price * item.quantity).toLocaleString()} ₽</strong></div>
                    <div class="cart-item-quantity">
                        <button class="quantity-btn" onclick="updateQuantity(${item.id}, ${item.quantity - 1})"><i class="fas fa-minus"></i></button>
                        <input type="text" class="quantity-input" value="${item.quantity}" readonly>
                        <button class="quantity-btn" onclick="updateQuantity(${item.id}, ${item.quantity + 1})"><i class="fas fa-plus"></i></button>
                    </div>
                </div>
                <button class="remove-btn" onclick="removeFromCart(${item.id})"><i class="fas fa-trash"></i></button>`;
            container.appendChild(el);
        });
        totalAmount.textContent = `${data.total.toLocaleString()} ₽`;
        if (totalItems) totalItems.textContent = data.count;
        totalBlock.style.display = 'block';
    } catch {
        container.innerHTML = `<div class="empty-cart"><i class="fas fa-wifi"></i><p>Ошибка соединения</p></div>`;
    }
}

async function updateQuantity(productId, qty) {
    if (qty < 1) return removeFromCart(productId);
    try {
        const res = await api(`/api/cart/item/${productId}`, {
            method: 'PUT',
            body: JSON.stringify({ product_id: productId, quantity: qty })
        });
        if (res.ok) loadCart();
    } catch {
        showToast('Ошибка сервера', 'error');
    }
}

async function removeFromCart(productId) {
    try {
        const res = await api(`/api/cart/remove?product_id=${productId}`, { method: 'DELETE' });
        if (res.ok) { showToast('Товар удалён'); loadCart(); }
    } catch {
        showToast('Ошибка сервера', 'error');
    }
}

async function clearCart() {
    if (!confirm('Очистить корзину?')) return;
    try {
        const res = await api('/api/cart/clear', { method: 'DELETE' });
        if (res.ok) { showToast('Корзина очищена'); loadCart(); }
    } catch {
        showToast('Ошибка сервера', 'error');
    }
}

function updateCartCount() {
    const el = document.getElementById('cart-count');
    if (!accessToken) { el.textContent = '0'; return; }
    api('/api/cart').then(r => r.json()).then(data => {
        el.textContent = data.count;
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
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');
    let hasError = false;
    if (!username || !validateEmail(username)) { document.getElementById('login-email-error').style.display = 'block'; hasError = true; }
    if (!password) { document.getElementById('login-password-error').style.display = 'block'; hasError = true; }
    if (hasError) return;

    try {
        const res = await api('/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        if (res.ok) {
            const data = await res.json();
            accessToken = data.access_token;
            currentUser = data.username;
            currentRole = data.role;
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('currentUser', currentUser);
            localStorage.setItem('currentRole', currentRole);
            showToast('Вход выполнен!');
            closeAuthModal();
            updateHeader();
            updateCartCount();
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
        const res = await api('/register', {
            method: 'POST',
            body: JSON.stringify({ username: loginVal, password })
        });
        if (res.ok) {
            showToast('Регистрация выполнена!');
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
    accessToken = '';
    currentUser = '';
    currentRole = '';
    localStorage.removeItem('accessToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('currentRole');
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
    if (accessToken && currentUser) {
        authLink.style.display = 'none';
        userInfo.style.display = 'flex';
        headerUser.textContent = currentUser;
        if (adminLink) {
            adminLink.style.display = currentRole === 'admin' ? 'list-item' : 'none';
        }
        if (profileLink) {
            profileLink.style.display = 'list-item';
        }
        if (wishlistLink) {
            wishlistLink.style.display = 'list-item';
        }
    } else {
        authLink.style.display = 'list-item';
        userInfo.style.display = 'none';
        if (adminLink) adminLink.style.display = 'none';
        if (profileLink) profileLink.style.display = 'none';
        if (wishlistLink) wishlistLink.style.display = 'none';
    }
}

/* ===== Checkout ===== */
async function checkout() {
    if (!accessToken) { showToast('Войдите для оформления', 'error'); showAuthModal(); return; }
    const address = prompt('Введите адрес доставки:');
    if (!address) return;
    const promoCode = document.getElementById('promo-input')?.value || null;
    try {
        const res = await api('/api/order', {
            method: 'POST',
            body: JSON.stringify({ address, promo_code: promoCode })
        });
        if (res.ok) {
            const data = await res.json();
            let msg = `Заказ #${data.order_id} на сумму ${data.total.toLocaleString()} ₽ оформлен!`;
            if (data.discount > 0) msg += ` (Скидка: ${data.discount.toLocaleString()} ₽)`;
            showToast(msg);
            document.getElementById('promo-input').value = '';
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
            showToast(data.message);
        } else {
            const err = await res.json();
            showToast(err.detail || 'Ошибка', 'error');
        }
    } catch { showToast('Ошибка сервера', 'error'); }
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
    } catch {}
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
    if (!oldPw || !newPw) { showToast('Заполните оба поля', 'error'); return; }
    if (newPw.length < 6) { showToast('Минимум 6 символов', 'error'); return; }
    try {
        const res = await api('/api/profile/change-password', {
            method: 'POST', body: JSON.stringify({ old_password: oldPw, new_password: newPw })
        });
        if (res.ok) { showToast('Пароль изменён'); document.getElementById('pw-old').value = ''; document.getElementById('pw-new').value = ''; }
        else { const e = await res.json(); showToast(e.detail || 'Ошибка', 'error'); }
    } catch { showToast('Ошибка сервера', 'error'); }
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
            </div>`).join('');
    } catch { el.innerHTML = ''; }
}

/* ===== Admin ===== */
let adminCurrentTab = 'stats';

function adminTab(tab) {
    adminCurrentTab = tab;
    document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.admin-tab[onclick="adminTab('${tab}')"]`).classList.add('active');
    if (tab === 'stats') loadAdminStats();
    else if (tab === 'products') loadAdminProducts();
    else if (tab === 'users') loadAdminUsers();
    else if (tab === 'orders') loadAdminOrders();
}

async function loadAdminStats() {
    const content = document.getElementById('admin-content');
    content.innerHTML = '<div class="spinner"></div>';
    try {
        const res = await api('/api/admin/stats');
        if (!res.ok) throw new Error();
        const s = await res.json();
        content.innerHTML = `
            <div class="admin-panel">
                <div class="admin-card"><h3>Пользователей</h3><p style="font-size:2rem;">${s.total_users}</p></div>
                <div class="admin-card"><h3>Товаров</h3><p style="font-size:2rem;">${s.total_products}</p></div>
                <div class="admin-card"><h3>Заказов</h3><p style="font-size:2rem;">${s.total_orders}</p></div>
                <div class="admin-card"><h3>Выручка</h3><p style="font-size:2rem;">${s.total_revenue.toLocaleString()} ₽</p></div>
            </div>`;
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Нет прав или ошибка</p>';
    }
}

/* ─── Products CRUD ─── */
async function loadAdminProducts() {
    const content = document.getElementById('admin-content');
    content.innerHTML = '<div class="spinner"></div>';
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
    content.innerHTML = '<div class="spinner"></div>';
    try {
        const res = await api('/api/admin/users');
        if (!res.ok) throw new Error();
        const users = await res.json();
        content.innerHTML = `
            <h3 style="margin-bottom:1rem;">Пользователи (${users.length})</h3>
            <table class="admin-table">
                <thead><tr><th>ID</th><th>Логин</th><th>Роль</th><th>Действия</th></tr></thead>
                <tbody>
                    ${users.map(u => `<tr>
                        <td>${u.id}</td><td>${u.username}</td><td><span class="status-badge ${u.role === 'admin' ? 'processing' : ''}">${u.role}</span></td>
                        <td>
                            ${u.username !== 'admin' ? `<button class="btn-sm ${u.role==='user'?'warning':'primary'}" onclick="toggleRole(${u.id},'${u.role}')">${u.role==='user'?'Сделать админом':'Снять админа'}</button>` : '<span style="color:var(--text-secondary);">—</span>'}
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>`;
    } catch {
        content.innerHTML = '<p style="color:var(--danger-color);">Нет прав или ошибка</p>';
    }
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

/* ─── Orders ─── */
async function loadAdminOrders() {
    const content = document.getElementById('admin-content');
    content.innerHTML = '<div class="spinner"></div>';
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
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

/* ===== Modal close handlers ===== */
document.getElementById('auth-modal')?.addEventListener('click', function (e) {
    if (e.target === this) closeAuthModal();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAuthModal(); });
