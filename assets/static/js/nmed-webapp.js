/* NMED HOME LAB — User WebApp */
(function () {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) tg.setHeaderColor('#0c1a33');
    if (tg.setBackgroundColor) tg.setBackgroundColor('#0c1a33');
  }

  const params = new URLSearchParams(location.search);
  const initialPage = params.get('page') || 'home';
  let currentLang = (params.get('lang') || 'uz').split('-')[0];
  if (!['uz', 'ru', 'en'].includes(currentLang)) currentLang = 'uz';

  let tgId = params.get('tg_id') || '';
  if (!tgId && tg?.initDataUnsafe?.user?.id) {
    tgId = String(tg.initDataUnsafe.user.id);
  }

  let appSettings = {};
  let servicesData = [];
  let districtsData = [];
  let wizardStep = 1;
  let wizardTotal = 8;
  let map, marker;

  const orderState = {
    tg_id: tgId,
    service: null,
    patient_type: null,
    patient_name: '',
    patient_age: '',
    patient_gender: null,
    child_timing: null,
    uses_diaper: null,
    complaints: [],
    custom_complaint: '',
    pickup_slot: '',
    district: null,
    address_note: '',
    phone: '',
    latitude: 41.31108,
    longitude: 69.24056,
    payment_method: 'tpay',
  };

  const T = {
    uz: {
      home_title: 'Laboratoriya endi uyingizda',
      order_btn: 'Tahlil buyurtma qilish',
      my_results: 'Natijalarim',
      order_status: 'Buyurtma holati',
      profile: 'Profilim',
      feedback: 'Fikr & taklif',
      trust: 'Nega bizga ishonishadi?',
      support: "Qo'llab-quvvatlash",
      continue: 'Davom etish',
      pay: "To'lash",
      back: 'Orqaga',
      step_of: (a, b) => `${a} / ${b}`,
    },
    ru: {
      home_title: 'Лаборатория теперь у вас дома',
      order_btn: 'Заказать анализ',
      my_results: 'Мои результаты',
      order_status: 'Статус заказа',
      profile: 'Мой профиль',
      feedback: 'Отзыв & предложение',
      trust: 'Почему нам доверяют?',
      support: 'Поддержка',
      continue: 'Продолжить',
      pay: 'Оплатить',
      back: 'Назад',
      step_of: (a, b) => `${a} / ${b}`,
    },
    en: {
      home_title: 'Laboratory at your home',
      order_btn: 'Order analysis',
      my_results: 'My results',
      order_status: 'Order status',
      profile: 'My profile',
      feedback: 'Feedback',
      trust: 'Why trust us?',
      support: 'Support',
      continue: 'Continue',
      pay: 'Pay',
      back: 'Back',
      step_of: (a, b) => `${a} / ${b}`,
    },
  };

  function tr(key) {
    const L = T[currentLang] || T.uz;
    return L[key] || T.uz[key] || key;
  }

  async function api(url, opts = {}) {
    const sep = url.includes('?') ? '&' : '?';
    const withId = tgId && !url.includes('tg_id=') ? `${url}${sep}tg_id=${tgId}` : url;
    const r = await fetch(withId, opts);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const ct = r.headers.get('content-type') || '';
    if (ct.includes('application/json')) return r.json();
    return r.text();
  }

  function showScreen(name) {
    document.querySelectorAll('.screen').forEach((s) => s.classList.remove('active'));
    const el = document.getElementById(`screen-${name}`);
    if (el) el.classList.add('active');
    const backBtn = document.getElementById('btnBack');
    if (backBtn) backBtn.classList.toggle('visible', name !== 'home');
    if (name === 'orders') loadOrders();
    if (name === 'results') loadResults();
    if (name === 'profile') loadProfile();
    if (name === 'order-detail') { /* filled by openOrder */ }
    if (name === 'wizard') updateWizardUI();
  }

  function goHome() {
    showScreen('home');
    history.replaceState(null, '', location.pathname + `?lang=${currentLang}${tgId ? '&tg_id=' + tgId : ''}`);
  }

  async function loadSettings() {
    try {
      appSettings = await api('/api/webapp/settings/');
      applyPaymentCardUI();
    } catch (e) {
      console.warn('Settings', e);
    }
  }

  function applyPaymentCardUI() {
    const num = document.getElementById('cardNumberDisplay');
    const holder = document.getElementById('cardHolderDisplay');
    if (num) num.textContent = appSettings.payment_card_number || '—';
    if (holder) holder.textContent = appSettings.payment_card_holder || '—';
  }

  /* ── HOME ── */
  function initHome() {
    document.getElementById('heroTitle').textContent = tr('home_title');
    document.getElementById('btnOrderMain').textContent = '🧪 ' + tr('order_btn');
    document.querySelectorAll('[data-menu]').forEach((el) => {
      const k = el.dataset.menu;
      if (k && T.uz[k]) el.querySelector('.mi-label').textContent = tr(k);
    });
  }

  /* ── WIZARD ── */
  function startWizard() {
    wizardStep = 1;
    orderState.tg_id = tgId;
    showScreen('wizard');
    fetchServices();
    fetchDistricts();
    if (!map) setTimeout(initMap, 300);
    renderChildTimings();
    renderComplaints('adult');
    renderSlots('adult');
  }

  function updateWizardUI() {
    document.querySelectorAll('.wizard-step').forEach((p, i) => {
      p.classList.toggle('active', i === wizardStep - 1);
    });
    const pct = (wizardStep / wizardTotal) * 100;
    const bar = document.getElementById('wizardProgress');
    if (bar) bar.style.width = pct + '%';
    const lbl = document.getElementById('wizardStepLabel');
    if (lbl) lbl.textContent = tr('step_of')(wizardStep, wizardTotal);
    const btn = document.getElementById('wizardNextBtn');
    if (btn) {
      btn.textContent = wizardStep === wizardTotal ? '🔒 ' + tr('pay') : tr('continue') + ' →';
      btn.classList.toggle('success', wizardStep === wizardTotal);
    }
  }

  function wizardNext() {
    if (!validateWizard()) return;
    if (wizardStep === wizardTotal) {
      submitOrder();
      return;
    }
    if (wizardStep === 3 && orderState.patient_type === 'adult') wizardStep = 5;
    else wizardStep++;
    if (wizardStep === 8) fillSummary();
    updateWizardUI();
  }

  function wizardPrev() {
    if (wizardStep === 5 && orderState.patient_type === 'adult') wizardStep = 3;
    else if (wizardStep > 1) wizardStep--;
    updateWizardUI();
  }

  function validateWizard() {
    if (wizardStep === 1 && !orderState.service) {
      alert('Xizmat turini tanlang');
      return false;
    }
    if (wizardStep === 2 && !orderState.patient_type) {
      alert('Bemor turini tanlang');
      return false;
    }
    if (wizardStep === 3) {
      orderState.patient_name = document.getElementById('patientName')?.value.trim() || '';
      orderState.patient_age = document.getElementById('patientAge')?.value || '';
      if (!orderState.patient_name || !orderState.patient_age || !orderState.patient_gender) {
        alert("Ma'lumotlarni to'liq kiriting");
        return false;
      }
    }
    if (wizardStep === 4 && orderState.patient_type === 'child') {
      if (!orderState.child_timing || orderState.uses_diaper === null) {
        alert('Bola parametrlarini to\'liq kiriting');
        return false;
      }
    }
    if (wizardStep === 6 && !orderState.pickup_slot) {
      alert('Vaqtni tanlang');
      return false;
    }
    if (wizardStep === 7) {
      orderState.district = document.getElementById('districtSelect')?.value;
      orderState.address_note = document.getElementById('addressNote')?.value.trim() || '';
      const phoneRaw = (document.getElementById('phoneInput')?.value || '').replace(/\D/g, '');
      if (phoneRaw.length !== 9) {
        document.getElementById('phoneError')?.classList.remove('hidden');
        return false;
      }
      document.getElementById('phoneError')?.classList.add('hidden');
      orderState.phone = '+998' + phoneRaw;
      const dst = districtsData.find((d) => String(d.id) === String(orderState.district));
      if (!orderState.district || !isDistrictServed(dst)) {
        alert('Tumanni tanlang yoki xizmat mavjud emas');
        return false;
      }
    }
    if (wizardStep === 8) {
      if (!orderState.payment_method) {
        alert("To'lov turini tanlang");
        return false;
      }
      if (orderState.payment_method === 'admin') {
        const fi = document.getElementById('paymentScreenshot');
        if (!fi?.files?.length) {
          document.getElementById('screenshotError')?.classList.remove('hidden');
          return false;
        }
      }
    }
    return true;
  }

  async function fetchServices() {
    const list = document.getElementById('servicesList');
    if (!list) return;
    list.innerHTML = '<div class="empty-state">Yuklanmoqda...</div>';
    try {
      const data = await api('/api/services/');
      servicesData = Array.isArray(data) ? data : data.results || [];
      list.innerHTML = servicesData
        .filter((s) => s.is_active !== false)
        .map(
          (s) => `
        <div class="card-white" id="srv_${s.id}" onclick="window.NMED.selectService(${s.id})">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <div style="font-weight:700">🧪 ${s.name_uz || s.name}</div>
              <div class="price">${Number(s.price).toLocaleString()} so'm</div>
            </div>
            <span style="color:#94a3b8">›</span>
          </div>
        </div>`
        )
        .join('');
    } catch (e) {
      list.innerHTML = '<div class="empty-state">Xizmatlar yuklanmadi</div>';
    }
  }

  async function fetchDistricts() {
    try {
      const data = await api('/api/districts/');
      districtsData = Array.isArray(data) ? data : data.results || [];
      const sel = document.getElementById('districtSelect');
      if (sel) {
        sel.innerHTML =
          '<option value="">— Tuman tanlang —</option>' +
          districtsData.map((d) => `<option value="${d.id}">${d.name}</option>`).join('');
      }
    } catch (e) {
      console.warn(e);
    }
  }

  function selectService(id) {
    orderState.service = id;
    document.querySelectorAll('[id^="srv_"]').forEach((el) => el.classList.remove('selected'));
    document.getElementById(`srv_${id}`)?.classList.add('selected');
  }

  function selectPatientType(type) {
    orderState.patient_type = type;
    document.getElementById('pTypeAdult')?.classList.toggle('selected', type === 'adult');
    document.getElementById('pTypeChild')?.classList.toggle('selected', type === 'child');
    renderComplaints(type);
    renderSlots(type);
  }

  function selectGender(g) {
    orderState.patient_gender = g;
    document.getElementById('genderMale')?.classList.toggle('selected', g === 'male');
    document.getElementById('genderFemale')?.classList.toggle('selected', g === 'female');
  }

  function renderChildTimings() {
    const grid = document.getElementById('childTimingsGrid');
    if (!grid) return;
    const items = [
      { id: 'morning', t: '🌅 Ertalab' },
      { id: 'day', t: '☀️ Kunduzi' },
      { id: 'evening', t: '🌙 Kechki' },
      { id: 'irregular', t: '🔄 Har xil' },
    ];
    grid.innerHTML = items
      .map(
        (x) =>
          `<button type="button" class="pill-btn" id="ct_${x.id}" onclick="window.NMED.selectChildTiming('${x.id}')">${x.t}</button>`
      )
      .join('');
  }

  function selectChildTiming(id) {
    orderState.child_timing = id;
    document.querySelectorAll('[id^="ct_"]').forEach((el) => el.classList.remove('selected'));
    document.getElementById(`ct_${id}`)?.classList.add('selected');
    renderSlots('child');
  }

  function selectDiaper(v) {
    orderState.uses_diaper = v;
    document.getElementById('diaperYes')?.classList.toggle('selected', v === true);
    document.getElementById('diaperNo')?.classList.toggle('selected', v === false);
  }

  function renderComplaints(type) {
    const box = document.getElementById('complaintsBox');
    if (!box) return;
    const list = [
      'Ich qotishi',
      'Ich ketishi',
      'Qorin dam',
      "Qorin og'rig'i",
      "Ko'ngil aynishi",
      'Allergiya',
      'Parazit gumoni',
    ];
    box.innerHTML = list
      .map(
        (c) => `
      <label style="display:flex;align-items:center;gap:8px;padding:10px;border:1px solid #e2e8f0;border-radius:12px;margin-bottom:8px;cursor:pointer">
        <input type="checkbox" value="${c}" onchange="window.NMED.toggleComplaint(this)"/>
        <span>${type === 'child' ? '👶' : '🧑'} ${c}</span>
      </label>`
      )
      .join('');
    orderState.complaints = [];
  }

  function toggleComplaint(cb) {
    if (cb.checked) orderState.complaints.push(cb.value);
    else orderState.complaints = orderState.complaints.filter((v) => v !== cb.value);
  }

  function renderSlots(type) {
    const box = document.getElementById('slotsBox');
    if (!box) return;
    let slots = [];
    if (type === 'adult') slots = ['📞 Operator bilan kelishiladi'];
    else if (orderState.child_timing === 'morning') slots = ['🌅 07:00 — 10:00'];
    else if (orderState.child_timing === 'day') slots = ['☀️ 12:00 — 15:00'];
    else if (orderState.child_timing === 'evening') slots = ['🌙 18:00 — 20:00'];
    else slots = ['📞 Operator bilan kelishiladi'];
    box.innerHTML = slots
      .map((s, i) => {
        const sid = 'slot_' + i;
        const esc = s.replace(/'/g, "\\'");
        return `<div class="card-white" id="${sid}" onclick="window.NMED.selectSlot('${esc}', document.getElementById('${sid}'))">${s}</div>`;
      })
      .join('');
  }

  function selectSlot(s, el) {
    orderState.pickup_slot = s;
    document.querySelectorAll('[id^="slot_"]').forEach((n) => n.classList.remove('selected'));
    if (el) el.classList.add('selected');
  }

  function selectPayMethod(m) {
    orderState.payment_method = m;
    document.getElementById('methodTpay')?.classList.toggle('selected', m === 'tpay');
    document.getElementById('methodAdmin')?.classList.toggle('selected', m === 'admin');
    document.getElementById('adminPayBlock')?.classList.toggle('hidden', m !== 'admin');
  }

  function fillSummary() {
    const srv = servicesData.find((s) => s.id == orderState.service);
    const dst = districtsData.find((d) => String(d.id) === String(orderState.district));
    const sP = srv ? parseFloat(srv.price) : 0;
    const dP = dst ? parseFloat(dst.delivery_price) : 0;
    const set = (id, t) => {
      const el = document.getElementById(id);
      if (el) el.textContent = t;
    };
    set('summaryService', srv?.name_uz || '—');
    set('summaryPatient', `${orderState.patient_name}, ${orderState.patient_age} yosh`);
    set('summaryTime', orderState.pickup_slot || '—');
    set('summaryDelivery', `${dP.toLocaleString()} so'm`);
    set('summaryTotal', `${(sP + dP).toLocaleString()} so'm`);
  }

  function isDistrictServed(d) {
    if (!d) return false;
    if (d.is_active === false || d.is_active === 'false' || d.is_active === 0) return false;
    const p = Number(d.delivery_price);
    return !isNaN(p) && p >= 0;
  }

  function initMap() {
    const el = document.getElementById('map');
    if (!el || typeof L === 'undefined') return;
    map = L.map('map').setView([orderState.latitude, orderState.longitude], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    marker = L.marker([orderState.latitude, orderState.longitude], { draggable: true }).addTo(map);
    marker.on('dragend', () => {
      const c = marker.getLatLng();
      orderState.latitude = c.lat;
      orderState.longitude = c.lng;
    });
  }

  async function requestLocation() {
    if (!navigator.geolocation) return alert('Joylashuv qo\'llab-quvvatlanmaydi');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        orderState.latitude = pos.coords.latitude;
        orderState.longitude = pos.coords.longitude;
        if (map) {
          map.setView([orderState.latitude, orderState.longitude], 14);
          marker.setLatLng([orderState.latitude, orderState.longitude]);
        }
      },
      () => alert('Joylashuv ruxsati kerak')
    );
  }

  async function submitOrder() {
    const extra = document.getElementById('extraComplaint')?.value?.trim();
    if (extra) orderState.custom_complaint = extra;
    fillSummary();

    const btn = document.getElementById('wizardNextBtn');
    btn.disabled = true;
    btn.textContent = '⏳ ...';

    const fd = new FormData();
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrf) fd.append('csrfmiddlewaretoken', csrf);
    for (const [k, v] of Object.entries(orderState)) {
      if (v == null) continue;
      if (k === 'complaints') fd.append(k, JSON.stringify(v));
      else fd.append(k, v);
    }
    if (orderState.payment_method === 'admin') {
      const fi = document.getElementById('paymentScreenshot');
      if (fi?.files?.[0]) fd.append('screenshot', fi.files[0]);
    }

    try {
      const res = await fetch('/tspay/orders/', { method: 'POST', body: fd });
      const data = await res.json();
      if (!data.success) {
        alert(data.detail || 'Xatolik');
        btn.disabled = false;
        btn.textContent = tr('pay');
        return;
      }
      if (orderState.payment_method === 'admin') {
        showSuccess('Buyurtmangiz qabul qilindi!');
        return;
      }
      if (data.payment_url) {
        sessionStorage.setItem('tspay_cheque_id', data.cheque_id);
        sessionStorage.setItem('tspay_order_id', String(data.order_id));
        location.href = data.payment_url;
        return;
      }
    } catch (e) {
      alert('Server xatosi: ' + e.message);
    }
    btn.disabled = false;
    btn.textContent = tr('pay');
  }

  function showSuccess(msg) {
    const body = document.getElementById('wizardBody');
    body.innerHTML = `
      <div class="success-screen">
        <div class="check">✅</div>
        <h2>Muvaffaqiyatli!</h2>
        <p>${msg}</p>
        <p style="font-size:13px;color:#64748b">Buyurtma: <b>NMED-${sessionStorage.getItem('tspay_order_id') || '—'}</b></p>
        <button class="btn-primary" style="margin-top:24px;max-width:280px" onclick="window.NMED.goHome()">Yopish</button>
      </div>`;
    document.querySelector('.wizard-footer')?.classList.add('hidden');
  }

  /* ── ORDERS ── */
  async function loadOrders() {
    const el = document.getElementById('ordersList');
    if (!el) return;
    el.innerHTML = '<div class="empty-state">Yuklanmoqda...</div>';
    try {
      const orders = await api('/api/webapp/orders/');
      if (!orders.length) {
        el.innerHTML = '<div class="empty-state"><div class="emoji">📭</div><p>Hozircha buyurtmalar yo\'q</p></div>';
        return;
      }
      el.innerHTML = orders
        .map(
          (o) => `
        <div class="order-card" onclick="window.NMED.openOrder(${o.id})">
          <div class="code">${o.order_code}</div>
          <div class="title">${o.service_name}</div>
          <div style="font-size:13px;color:#64748b">${o.created_at}</div>
          <span class="status-badge status-${o.status}">${statusText(o.status)}</span>
          <div style="margin-top:8px;font-weight:700">${Number(o.total_price).toLocaleString()} so'm</div>
        </div>`
        )
        .join('');
    } catch (e) {
      el.innerHTML = '<div class="empty-state">Xatolik</div>';
    }
  }

  function statusText(s) {
    const m = {
      pending: '⏳ Kutilmoqda',
      paid: "💳 To'langan",
      delivering: "🚚 Yo'lda",
      done: '✅ Yetkazildi',
      result_pending: '🔬 Laboratoriyada',
      result_sent: '📊 Natija tayyor',
      canceled: '❌ Bekor',
    };
    return m[s] || s;
  }

  async function openOrder(id) {
    showScreen('order-detail');
    const el = document.getElementById('orderDetailContent');
    el.innerHTML = '<div class="empty-state">Yuklanmoqda...</div>';
    try {
      const o = await api(`/api/webapp/orders/${id}/`);
      let tlHtml = (o.timeline || [])
        .map(
          (s) => `
        <div class="timeline-item ${s.state}">
          <div class="tl-dot">${s.icon}</div>
          <div class="tl-text ${s.state === 'pending' ? 'muted' : ''}">${s.label}</div>
        </div>`
        )
        .join('');
      el.innerHTML = `
        <h2 style="margin:0 0 4px">${o.order_code}</h2>
        <p style="color:#64748b;font-size:13px;margin:0 0 16px">${o.created_at}</p>
        <div class="order-card" style="cursor:default">
          <div><b>${o.service_name}</b></div>
          <div style="font-size:13px;margin-top:8px">👤 ${o.patient_name || '—'}, ${o.patient_age || '—'} yosh</div>
          <div style="font-size:13px">📍 ${o.district_name || '—'}</div>
          <div style="font-size:13px">🕐 ${o.pickup_slot || '—'}</div>
          <div style="font-weight:700;margin-top:12px">${Number(o.total_price).toLocaleString()} so'm</div>
        </div>
        <h3 style="font-size:15px">Buyurtma holati</h3>
        <div class="timeline">${tlHtml}</div>
        ${
          o.result_url
            ? `<a href="${o.result_url}" target="_blank" class="btn-primary" style="display:block;text-align:center;text-decoration:none;margin-top:16px">📄 Natijani ko'rish</a>`
            : ''
        }`;
    } catch (e) {
      el.innerHTML = '<div class="empty-state">Topilmadi</div>';
    }
  }

  /* ── RESULTS ── */
  async function loadResults() {
    const el = document.getElementById('resultsList');
    if (!el) return;
    el.innerHTML = '<div class="empty-state">Yuklanmoqda...</div>';
    try {
      const items = await api('/api/webapp/results/');
      if (!items.length) {
        el.innerHTML = '<div class="empty-state"><div class="emoji">📭</div><p>Natijalar hali mavjud emas</p></div>';
        return;
      }
      el.innerHTML = items
        .map(
          (r) => `
        <div class="order-card">
          <div class="code">${r.order_code}</div>
          <div class="title">${r.service_name}</div>
          <div style="font-size:13px;color:#64748b">📅 ${r.created_at}</div>
          ${r.doctor_conclusion ? `<p style="font-size:13px;margin-top:8px"><i>${r.doctor_conclusion}</i></p>` : ''}
          <a href="${r.result_url}" target="_blank" class="btn-primary" style="display:block;text-align:center;text-decoration:none;margin-top:12px;font-size:14px;padding:12px">📄 Natijani yuklab olish</a>
        </div>`
        )
        .join('');
    } catch (e) {
      el.innerHTML = '<div class="empty-state">Xatolik</div>';
    }
  }

  /* ── PROFILE ── */
  async function loadProfile() {
    const el = document.getElementById('profileContent');
    if (!el) return;
    try {
      const p = await api('/api/webapp/profile/');
      const bar =
        '🟦'.repeat(p.cycle_position) + '⬜'.repeat(Math.max(0, 6 - p.cycle_position));
      el.innerHTML = `
        <div class="profile-card">
          <div style="font-size:12px;opacity:.8">MED ID</div>
          <div style="font-size:22px;font-weight:800;margin:4px 0">${p.patient_id}</div>
          <div style="font-size:15px">${p.first_name || '—'}</div>
          <div style="font-size:12px;opacity:.7;margin-top:8px">📅 ${p.date_joined}</div>
          <div style="margin-top:16px">⭐️ ${p.bonus_points} bonus</div>
          <div class="bonus-bar">${bar}</div>
          <div style="font-size:12px">Yana <b>${p.next_free_in}</b> ta buyurtmadan keyin bepul</div>
        </div>
        <div class="order-card" style="cursor:default">
          <div>📦 Jami buyurtmalar: <b>${p.total_orders}</b></div>
          <div style="margin-top:8px">✅ Yakunlangan: <b>${p.completed_orders}</b></div>
        </div>`;
    } catch (e) {
      el.innerHTML = '<div class="empty-state">Profil yuklanmadi</div>';
    }
  }

  async function submitAppeal() {
    const msg = document.getElementById('appealText')?.value?.trim();
    if (!msg) return alert('Xabar yozing');
    try {
      await api('/api/webapp/appeal/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tg_id: tgId, message: msg }),
      });
      alert('Rahmat! Murojaatingiz qabul qilindi.');
      document.getElementById('appealText').value = '';
      goHome();
    } catch (e) {
      alert('Xatolik');
    }
  }

  function openSupport() {
    const phone = appSettings.support_phone || '';
    const tgLink = appSettings.support_telegram || '';
    if (tgLink) tg.openTelegramLink?.(tgLink) || window.open(tgLink);
    else if (phone) tg.openLink?.('tel:' + phone);
  }

  /* ── INIT ── */
  document.getElementById('btnBack')?.addEventListener('click', () => {
    if (document.getElementById('screen-wizard')?.classList.contains('active') && wizardStep > 1) {
      wizardPrev();
    } else goHome();
  });

  document.getElementById('btnOrderMain')?.addEventListener('click', startWizard);
  document.querySelectorAll('[data-goto]').forEach((el) => {
    el.addEventListener('click', () => {
      const page = el.dataset.goto;
      if (page === 'order') startWizard();
      else showScreen(page);
    });
  });

  document.getElementById('wizardNextBtn')?.addEventListener('click', wizardNext);
  document.getElementById('btnAppealSend')?.addEventListener('click', submitAppeal);
  document.getElementById('btnSupportTg')?.addEventListener('click', openSupport);
  document.getElementById('btnLoc')?.addEventListener('click', requestLocation);

  document.getElementById('paymentScreenshot')?.addEventListener('change', function () {
    if (this.files?.[0]) {
      const r = new FileReader();
      r.onload = (e) => {
        const img = document.getElementById('screenshotPreviewImg');
        const box = document.getElementById('screenshotPreview');
        if (img) img.src = e.target.result;
        box?.classList.remove('hidden');
      };
      r.readAsDataURL(this.files[0]);
    }
  });

  window.NMED = {
    selectService,
    selectPatientType,
    selectGender,
    selectChildTiming,
    selectDiaper,
    toggleComplaint,
    selectSlot,
    selectPayMethod,
    openOrder,
    goHome,
    startWizard,
  };

  loadSettings().then(() => {
    initHome();
    orderState.tg_id = tgId;
    if (initialPage === 'order') startWizard();
    else if (initialPage !== 'home') showScreen(initialPage);
    else showScreen('home');

    if (wizardStep === 8) fillSummary();
    checkTspayReturn();
  });

  async function checkTspayReturn() {
    const chequeId = sessionStorage.getItem('tspay_cheque_id');
    const orderId = sessionStorage.getItem('tspay_order_id');
    if (!chequeId || !orderId) return;
    sessionStorage.removeItem('tspay_cheque_id');
    sessionStorage.removeItem('tspay_order_id');
    startWizard();
    try {
      const r = await fetch(`/tspay/orders/${orderId}/confirm_payment/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cheque_id: chequeId }),
      });
      const result = await r.json();
      if (result.status === 'paid' || result.success) showSuccess("To'lov muvaffaqiyatli!");
      else showSuccess("To'lov tekshirilmoqda. Tez orada bog'lanamiz.");
    } catch (e) {
      showSuccess('Buyurtma qabul qilindi.');
    }
  }

  if (wizardStep === 8) {
    /* noop - filled on step enter */
  }
})();
