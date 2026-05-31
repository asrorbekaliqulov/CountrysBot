/* NMED HOME LAB — User WebApp */
(function () {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) tg.setHeaderColor('#0a1128');
    if (tg.setBackgroundColor) tg.setBackgroundColor('#0a1128');
  }

  const params = new URLSearchParams(location.search);
  const initialPage = params.get('page') || 'home';
  let currentLang = (params.get('lang') || '').split('-')[0];
  if (!['uz', 'ru', 'en'].includes(currentLang)) currentLang = '';

  let tgId = params.get('tg_id') || '';
  if (!tgId && tg?.initDataUnsafe?.user?.id) {
    tgId = String(tg.initDataUnsafe.user.id);
  }

  let appSettings = {};
  let servicesData = [];
  let districtsData = [];
  let wizardStep = 1;
  let wizardTotal = 9;
  let map, marker;
  let lastOrderCode = '';

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
    payment_method: null,
    locationServed: null,
    detectedAddress: '',
  };

  const T = window.NMED_I18N || { uz: {}, ru: {}, en: {} };

  function tr(key) {
    const L = T[currentLang] || T.uz;
    const val = L[key];
    if (typeof val === 'function') return val;
    return val || T.uz[key] || key;
  }

  function serviceName(s) {
    if (!s) return '—';
    if (currentLang === 'ru') return s.name_ru || s.name_uz || s.name || '—';
    if (currentLang === 'en') return s.name_en || s.name_uz || s.name || '—';
    return s.name_uz || s.name || '—';
  }

  function applyI18n() {
    document.documentElement.lang = currentLang || 'uz';
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.dataset.i18n;
      const val = tr(key);
      if (val && typeof val === 'string') el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-ph]').forEach((el) => {
      const val = tr(el.dataset.i18nPh);
      if (val && typeof val === 'string') el.placeholder = val;
    });
    const backBtn = document.getElementById('btnBack');
    if (backBtn) backBtn.setAttribute('aria-label', tr('back'));
  }

  async function initLang() {
    const urlLang = params.get('lang');
    if (urlLang && ['uz', 'ru', 'en'].includes(urlLang.split('-')[0])) {
      currentLang = urlLang.split('-')[0];
      return;
    }
    if (tgId) {
      try {
        const p = await api('/api/webapp/profile/');
        if (p.lang && ['uz', 'ru', 'en'].includes(p.lang)) {
          currentLang = p.lang;
          return;
        }
      } catch (e) {
        console.warn('Profile lang', e);
      }
    }
    const tgLang = tg?.initDataUnsafe?.user?.language_code;
    if (tgLang) {
      const code = tgLang.split('-')[0];
      if (['uz', 'ru', 'en'].includes(code)) {
        currentLang = code;
        return;
      }
    }
    currentLang = 'uz';
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
    const header = document.querySelector('.app-header');
    if (header) header.classList.toggle('hidden', name === 'home');
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
    applyI18n();
  }

  /* ── WIZARD ── */
  function startWizard() {
    wizardStep = 1;
    orderState.payment_method = null;
    orderState.tg_id = tgId;
    document.getElementById('methodTpay')?.classList.remove('selected');
    document.getElementById('methodAdmin')?.classList.remove('selected');
    document.getElementById('adminPayBlock')?.classList.add('hidden');
    document.getElementById('screenshotError')?.classList.add('hidden');
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
    const dots = document.getElementById('wizardDots');
    if (dots) {
      dots.innerHTML = Array.from({ length: wizardTotal }, (_, i) => {
        const n = i + 1;
        let cls = '';
        if (n < wizardStep) cls = 'done';
        else if (n === wizardStep) cls = 'active';
        return `<span class="${cls}"></span>`;
      }).join('');
    }
    const btn = document.getElementById('wizardNextBtn');
    if (btn) {
      btn.classList.remove('btn-pay');
      if (wizardStep === wizardTotal) {
        btn.textContent =
          orderState.payment_method === 'tpay'
            ? '🔒 ' + tr('pay')
            : '🔒 ' + tr('confirm_order');
        btn.classList.add('btn-pay');
      } else {
        btn.textContent = tr('continue') + ' →';
      }
    }
    applyI18n();
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
      alert(tr('alert_select_service'));
      return false;
    }
    if (wizardStep === 2 && !orderState.patient_type) {
      alert(tr('alert_select_patient'));
      return false;
    }
    if (wizardStep === 3) {
      orderState.patient_name = document.getElementById('patientName')?.value.trim() || '';
      orderState.patient_age = document.getElementById('patientAge')?.value || '';
      if (!orderState.patient_name || !orderState.patient_age || !orderState.patient_gender) {
        alert(tr('alert_fill_data'));
        return false;
      }
    }
    if (wizardStep === 4 && orderState.patient_type === 'child') {
      if (!orderState.child_timing || orderState.uses_diaper === null) {
        alert(tr('alert_child_params'));
        return false;
      }
    }
    if (wizardStep === 6 && !orderState.pickup_slot) {
      alert(tr('alert_select_time'));
      return false;
    }
    if (wizardStep === 7) {
      if (orderState.locationServed === null) {
        alert(tr('alert_send_location'));
        return false;
      }
      const served = orderState.locationServed === true;
      const phoneEl = served ? document.getElementById('phoneInput') : document.getElementById('phoneInputExtra');
      const phoneErr = served ? document.getElementById('phoneError') : document.getElementById('phoneErrorExtra');
      const phoneRaw = (phoneEl?.value || '').replace(/\D/g, '');
      if (phoneRaw.length !== 9) {
        phoneErr?.classList.remove('hidden');
        return false;
      }
      phoneErr?.classList.add('hidden');
      orderState.phone = '+998' + phoneRaw;
      orderState.address_note = served
        ? document.getElementById('addressNote')?.value.trim() || ''
        : document.getElementById('addressNoteExtra')?.value.trim() || '';
      if (orderState.detectedAddress && !orderState.address_note) {
        orderState.address_note = orderState.detectedAddress;
      }
      const dst = districtsData.find((d) => String(d.id) === String(orderState.district));
      if (!orderState.district || !isDistrictServed(dst)) {
        alert(tr('alert_select_district'));
        return false;
      }
    }
    if (wizardStep === 8) {
      /* xulosa — faqat ko'rish */
    }
    if (wizardStep === 9) {
      if (!orderState.payment_method) {
        alert(tr('alert_select_pay'));
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
    list.innerHTML = '<div class="empty-state">' + tr('loading') + '</div>';
    try {
      const data = await api('/api/services/');
      servicesData = Array.isArray(data) ? data : data.results || [];
      list.innerHTML = servicesData
        .filter((s) => s.is_active !== false)
        .map((s, idx) => {
          const icCls = ['ic-green', 'ic-purple', 'ic-blue', 'ic-amber'][idx % 4];
          const iconHtml = s.icon_url
            ? `<img src="${s.icon_url}" alt="">`
            : `<span>🧪</span>`;
          const subtitle = s.description
            ? `<div class="srv-subtitle">${s.description}</div>`
            : '';
          return `
        <div class="card-white" id="srv_${s.id}" onclick="window.NMED.selectService(${s.id})">
          <div class="srv-row">
            <div class="srv-icon-wrap ${icCls}">${iconHtml}</div>
            <div class="srv-info">
              <div class="srv-name">${serviceName(s)}</div>
              ${subtitle}
              <div class="srv-price">${Number(s.price).toLocaleString()} ${tr('currency')}</div>
            </div>
            <span class="srv-chevron">›</span>
          </div>
        </div>`;
        })
        .join('');
    } catch (e) {
      list.innerHTML = '<div class="empty-state">' + tr('services_fail') + '</div>';
    }
  }

  async function fetchDistricts() {
    try {
      const data = await api('/api/districts/');
      districtsData = Array.isArray(data) ? data : data.results || [];
      const sel = document.getElementById('districtSelect');
      if (sel) {
        sel.innerHTML =
          '<option value="">' + tr('select_district') + '</option>' +
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
      { id: 'morning', t: tr('ct_morning') },
      { id: 'day', t: tr('ct_day') },
      { id: 'evening', t: tr('ct_evening') },
      { id: 'irregular', t: tr('ct_irregular') },
    ];
    grid.innerHTML = items
      .map(
        (x) =>
          `<button type="button" class="choice-block" id="ct_${x.id}" onclick="window.NMED.selectChildTiming('${x.id}')">${x.t}</button>`
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
    const list = tr('complaints') || [];
    box.innerHTML = list
      .map(
        (c) => `
      <label class="choice-card">
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
    const slotLabel = '18:00 — 22:00';
    const slotValue = '18:00 — 22:00';
    box.innerHTML = `
      <div class="slot-card" id="slot_evening" onclick="window.NMED.selectSlot('${slotValue}', document.getElementById('slot_evening'))">
        <div>
          <div class="slot-time">🌆 ${slotLabel}</div>
          <div class="slot-hint">${tr('slot_hint')}</div>
        </div>
      </div>`;
    orderState.pickup_slot = '';
  }

  function selectSlot(s, el) {
    orderState.pickup_slot = s;
    document.querySelectorAll('.slot-card').forEach((n) => n.classList.remove('selected'));
    if (el) el.classList.add('selected');
  }

  function selectPayMethod(m) {
    orderState.payment_method = m;
    document.getElementById('methodTpay')?.classList.toggle('selected', m === 'tpay');
    document.getElementById('methodAdmin')?.classList.toggle('selected', m === 'admin');
    document.getElementById('adminPayBlock')?.classList.toggle('hidden', m !== 'admin');
    if (wizardStep === wizardTotal) updateWizardUI();
  }

  function fillSummary() {
    const srv = servicesData.find((s) => s.id == orderState.service);
    const sP = srv ? parseFloat(srv.price) : 0;
    const set = (id, t) => {
      const el = document.getElementById(id);
      if (el) el.textContent = t;
    };
    set('summaryService', serviceName(srv));
    set('summaryPatient', `${orderState.patient_name}, ${orderState.patient_age} ${tr('years')}`);
    set('summaryTime', orderState.pickup_slot || '—');
    set('summaryDelivery', tr('delivery_free'));
    set('summaryTotal', `${sP.toLocaleString()} ${tr('currency')}`);
  }

  function isDistrictServed(d) {
    if (!d) return false;
    if (d.is_active === false || d.is_active === 'false' || d.is_active === 0) return false;
    return true;
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

  function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const toRad = (x) => (x * Math.PI) / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function setLocSpinner(on) {
    document.getElementById('locSpinner')?.classList.toggle('hidden', !on);
  }

  function showServedBlock(district, humanAddress) {
    orderState.locationServed = true;
    orderState.district = String(district.id);
    document.getElementById('districtSelect').value = district.id;
    document.getElementById('locServedBlock')?.classList.remove('hidden');
    document.getElementById('locUnservedBlock')?.classList.add('hidden');
    const addr = document.getElementById('detectedAddressText');
    const fee = document.getElementById('deliveryFeeText');
    if (addr) addr.textContent = humanAddress || district.name;
    if (fee) fee.textContent = `${tr('delivery_label')} ${tr('delivery_free')}`;
    orderState.detectedAddress = humanAddress || district.name;
  }

  function showUnservedBlock(humanAddress) {
    orderState.locationServed = false;
    orderState.district = null;
    document.getElementById('districtSelect').value = '';
    document.getElementById('locServedBlock')?.classList.add('hidden');
    document.getElementById('locUnservedBlock')?.classList.remove('hidden');
    const t = document.getElementById('unservedAddressText');
    if (t) t.textContent = humanAddress || tr('unserved_hint');
    renderUnservedDistricts();
  }

  function renderUnservedDistricts() {
    const box = document.getElementById('unservedDistrictList');
    if (!box) return;
    const served = districtsData.filter((d) => isDistrictServed(d));
    if (!served.length) {
      box.innerHTML = '<div class="empty-state">' + tr('no_districts') + '</div>';
      return;
    }
    box.innerHTML = served
      .map(
        (d) => `
      <button type="button" class="district-pick ${orderState.district == d.id ? 'selected' : ''}"
        onclick="window.NMED.selectUnservedDistrict(${d.id})">
        <span>🏘️ ${d.name}</span>
        <span class="district-pick-meta">${tr('delivery_free')}</span>
      </button>`
      )
      .join('');
  }

  function selectUnservedDistrict(id) {
    const d = districtsData.find((x) => x.id == id);
    if (!d) return;
    orderState.district = String(id);
    document.getElementById('districtSelect').value = id;
    if (d.latitude && d.longitude && map) {
      map.setView([parseFloat(d.latitude), parseFloat(d.longitude)], 13);
      marker.setLatLng([parseFloat(d.latitude), parseFloat(d.longitude)]);
      orderState.latitude = parseFloat(d.latitude);
      orderState.longitude = parseFloat(d.longitude);
    }
    renderUnservedDistricts();
  }

  async function onLocOk(pos) {
    setLocSpinner(false);
    const lat = pos.coords.latitude;
    const lng = pos.coords.longitude;
    orderState.latitude = lat;
    orderState.longitude = lng;
    if (map) {
      map.setView([lat, lng], 14);
      marker.setLatLng([lat, lng]);
      setTimeout(() => map.invalidateSize(), 200);
    }

    if (!districtsData.length) {
      alert(tr('alert_districts_fail'));
      return;
    }

    let humanAddress = null;
    try {
      const geo = await fetch(
        `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&zoom=16&addressdetails=1`,
        { headers: { 'Accept-Language': 'uz,ru;q=0.8' } }
      );
      const geoData = await geo.json();
      if (geoData?.address) {
        const a = geoData.address;
        const parts = [
          a.road || a.pedestrian,
          a.suburb || a.neighbourhood || a.quarter,
          a.city_district,
          a.city || a.town,
        ].filter(Boolean);
        humanAddress = parts.join(', ') || geoData.display_name?.split(',').slice(0, 3).join(', ');
      }
    } catch (e) {
      console.warn('reverse geocode', e);
    }

    const ranked = [];
    districtsData.forEach((d) => {
      if (d.latitude == null || d.longitude == null) return;
      ranked.push({ d, dist: haversine(lat, lng, parseFloat(d.latitude), parseFloat(d.longitude)) });
    });
    ranked.sort((a, b) => a.dist - b.dist);
    const detected = ranked[0];
    if (!detected) {
      showUnservedBlock(humanAddress);
      return;
    }

    if (detected.dist > 35) {
      document.getElementById('locResult').innerHTML =
        '<div class="info-card warn"><div class="info-card-title">' + tr('out_of_area') + '</div><div class="info-card-body">' + tr('out_of_area_body') + '</div></div>';
      showUnservedBlock(humanAddress);
      return;
    }

    const best = detected.d;
    if (isDistrictServed(best)) {
      document.getElementById('locResult').innerHTML = '';
      showServedBlock(best, humanAddress || best.name);
    } else {
      document.getElementById('locResult').innerHTML =
        '<div class="info-card warn"><div class="info-card-body">' + tr('no_service_here') + '</div></div>';
      showUnservedBlock(humanAddress || best.name);
    }
  }

  function onLocErr() {
    setLocSpinner(false);
    document.getElementById('locResult').innerHTML =
      '<div class="info-card warn"><div class="info-card-body">' + tr('gps_error') + '</div></div>';
    showUnservedBlock(null);
  }

  async function requestLocation() {
    if (!navigator.geolocation) {
      alert(tr('alert_geo_unsupported'));
      showUnservedBlock(null);
      return;
    }
    setLocSpinner(true);
    navigator.geolocation.getCurrentPosition(onLocOk, onLocErr, {
      enableHighAccuracy: true,
      timeout: 25000,
      maximumAge: 0,
    });
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
        alert(data.detail || tr('error'));
        btn.disabled = false;
        updateWizardUI();
        return;
      }
      if (orderState.payment_method === 'admin') {
        showOrderSuccess(data.order_code);
        return;
      }
      if (data.payment_url) {
        sessionStorage.setItem('tspay_cheque_id', data.cheque_id);
        sessionStorage.setItem('tspay_order_id', String(data.order_id));
        sessionStorage.setItem('tspay_order_code', data.order_code || '');
        if (tg?.openLink) tg.openLink(data.payment_url);
        else window.location.href = data.payment_url;
        return;
      }
    } catch (e) {
      alert(tr('error') + ': ' + e.message);
    }
    btn.disabled = false;
    updateWizardUI();
  }

  function showOrderSuccess(orderCode, subtitle) {
    lastOrderCode = orderCode || '';
    const now = new Date();
    const dateStr = now.toLocaleDateString('uz-UZ');
    const timeStr = now.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' });
    const code = orderCode || '—';
    const body = document.getElementById('wizardBody');
    body.innerHTML = `
      <div class="order-success-screen">
        <div class="success-top-label">${tr('success_label')}</div>
        <div class="success-card-premium">
          <div class="success-check-ring">✓</div>
          <h2>${subtitle || tr('success_accepted')}</h2>
          <ul class="success-steps-list">
            <li><span class="ss-ic">🧫</span><span>${tr('success_step1')}</span></li>
            <li><span class="ss-ic">👤</span><span>${tr('success_step2')}</span></li>
            <li><span class="ss-ic">🔬</span><span>${tr('success_step3')}</span></li>
            <li><span class="ss-ic">📄</span><span>${tr('success_step4')}</span></li>
          </ul>
          <div class="success-order-box">
            <div class="success-order-label">${tr('order_number')}</div>
            <div class="success-order-id">#${code}</div>
            <div class="success-order-date">${dateStr} · ${timeStr}</div>
          </div>
        </div>
        <button type="button" class="btn-primary success-close-btn" onclick="window.NMED.goHome()">${tr('close')}</button>
      </div>`;
    document.querySelector('.wizard-footer')?.classList.add('hidden');
    showScreen('wizard');
  }

  /* ── ORDERS ── */
  async function loadOrders() {
    const el = document.getElementById('ordersList');
    if (!el) return;
    el.innerHTML = '<div class="empty-state">' + tr('loading') + '</div>';
    try {
      const orders = await api('/api/webapp/orders/');
      if (!orders.length) {
        el.innerHTML = '<div class="empty-state"><div class="emoji">📭</div><p>' + tr('no_orders') + '</p></div>';
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
          <div style="margin-top:8px;font-weight:700">${Number(o.total_price).toLocaleString()} ${tr('currency')}</div>
        </div>`
        )
        .join('');
    } catch (e) {
      el.innerHTML = '<div class="empty-state">' + tr('error') + '</div>';
    }
  }

  function statusText(s) {
    const m = tr('status') || {};
    return m[s] || s;
  }

  async function openOrder(id) {
    showScreen('order-detail');
    const el = document.getElementById('orderDetailContent');
    el.innerHTML = '<div class="empty-state">' + tr('loading') + '</div>';
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
          <div style="font-size:13px;margin-top:8px">👤 ${o.patient_name || '—'}, ${o.patient_age || '—'} ${tr('years')}</div>
          <div style="font-size:13px">📍 ${o.district_name || '—'}</div>
          <div style="font-size:13px">🕐 ${o.pickup_slot || '—'}</div>
          <div style="font-weight:700;margin-top:12px">${Number(o.total_price).toLocaleString()} ${tr('currency')}</div>
        </div>
        <h3 style="font-size:15px">${tr('order_status_title')}</h3>
        <div class="timeline">${tlHtml}</div>
        ${
          o.result_url
            ? `<a href="${o.result_url}" target="_blank" class="btn-primary" style="display:block;text-align:center;text-decoration:none;margin-top:16px">${tr('view_result')}</a>`
            : ''
        }`;
    } catch (e) {
      el.innerHTML = '<div class="empty-state">' + tr('not_found') + '</div>';
    }
  }

  /* ── RESULTS ── */
  async function loadResults() {
    const el = document.getElementById('resultsList');
    if (!el) return;
    el.innerHTML = '<div class="empty-state">' + tr('loading') + '</div>';
    try {
      const items = await api('/api/webapp/results/');
      if (!items.length) {
        el.innerHTML = '<div class="empty-state"><div class="emoji">📭</div><p>' + tr('no_results') + '</p></div>';
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
          <a href="${r.result_url}" target="_blank" class="btn-primary" style="display:block;text-align:center;text-decoration:none;margin-top:12px;font-size:14px;padding:12px">${tr('download_result')}</a>
        </div>`
        )
        .join('');
    } catch (e) {
      el.innerHTML = '<div class="empty-state">' + tr('error') + '</div>';
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
          <div style="margin-top:16px">⭐️ ${p.bonus_points} ${tr('profile_bonus')}</div>
          <div class="bonus-bar">${bar}</div>
          <div style="font-size:12px">${typeof tr('profile_free_after') === 'function' ? tr('profile_free_after')(p.next_free_in) : p.next_free_in}</div>
        </div>
        <div class="order-card" style="cursor:default">
          <div>📦 ${tr('profile_total')} <b>${p.total_orders}</b></div>
          <div style="margin-top:8px">✅ ${tr('profile_completed')} <b>${p.completed_orders}</b></div>
        </div>`;
    } catch (e) {
      el.innerHTML = '<div class="empty-state">' + tr('profile_fail') + '</div>';
    }
  }

  async function submitAppeal() {
    const msg = document.getElementById('appealText')?.value?.trim();
    if (!msg) return alert(tr('alert_write_message'));
    try {
      await api('/api/webapp/appeal/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tg_id: tgId, message: msg }),
      });
      alert(tr('alert_thanks'));
      document.getElementById('appealText').value = '';
      goHome();
    } catch (e) {
      alert(tr('error'));
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
    selectUnservedDistrict,
    openOrder,
    goHome,
    startWizard,
  };

  initLang().then(() => {
    applyI18n();
    loadSettings().then(() => {
      initHome();
      orderState.tg_id = tgId;
      if (initialPage === 'order') showScreen('home');
      else if (initialPage !== 'home') showScreen(initialPage);
      else showScreen('home');

      if (wizardStep === 8) fillSummary();
      checkTspayReturn();
    });
  });

  async function checkTspayReturn() {
    const chequeId = sessionStorage.getItem('tspay_cheque_id');
    const orderId = sessionStorage.getItem('tspay_order_id');
    const orderCode = sessionStorage.getItem('tspay_order_code');
    if (!chequeId || !orderId) return;
    sessionStorage.removeItem('tspay_cheque_id');
    sessionStorage.removeItem('tspay_order_id');
    sessionStorage.removeItem('tspay_order_code');
    showScreen('wizard');
    const fallbackCode = orderCode || `NMED-${String(orderId).padStart(5, '0')}`;
    try {
      const r = await fetch(`/tspay/orders/${orderId}/check_payment/?tg_id=${tgId || ''}`);
      const result = await r.json();
      if (result.status === 'paid' || result.success) {
        showOrderSuccess(fallbackCode);
      } else {
        showOrderSuccess(fallbackCode, tr('pay_checking'));
      }
    } catch (e) {
      showOrderSuccess(fallbackCode);
    }
  }
})();
