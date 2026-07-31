// purchase.js
// author sreevidya
console.log("purchase.js loaded ✅");



const form = document.getElementById('purchase-form');
let lastvendorSearchTerm = '';
let lastpurchasepersonSearchTerm = '';
let lastItemSearchTerm = '';



function initializeLocationSelectsIn(root) {
  function runInit() {
    if (window.LyraLocationSelects) {
      window.LyraLocationSelects.init(root || document);
    }
  }

  if (window.LyraLocationSelects) {
    runInit();
    return;
  }

  if (window.__lyraLocationSelectsLoading) {
    document.addEventListener('lyra:location-selects-ready', runInit, { once: true });
    return;
  }

  window.__lyraLocationSelectsLoading = true;
  document.addEventListener('lyra:location-selects-ready', runInit, { once: true });
  var script = document.createElement('script');
  script.src = '/static/js/location_selects.js';
  script.onload = function () {
    window.__lyraLocationSelectsLoading = false;
    document.dispatchEvent(new Event('lyra:location-selects-ready'));
  };
  script.onerror = function () {
    window.__lyraLocationSelectsLoading = false;
    console.warn('Could not load location_selects.js');
  };
  document.head.appendChild(script);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function () {
    initializeLocationSelectsIn(document);
  });
} else {
  initializeLocationSelectsIn(document);
}

const DEFAULT_CURRENCY_SYMBOL = '₹';
const currencySymbolMap = new Map();
let currencySymbolMapReady = false;

function ensureCurrencySymbolMap() {
  if (currencySymbolMapReady) return;
  rebuildCurrencySymbolMap();
}

function rebuildCurrencySymbolMap() {
  currencySymbolMap.clear();
  const docSel = document.getElementById('document_currency');
  if (!docSel) {
    currencySymbolMapReady = true;
    return;
  }
  const baseSymbol =
    (docSel.dataset && docSel.dataset.baseSymbol) ||
    docSel.getAttribute('data-base-symbol') ||
    DEFAULT_CURRENCY_SYMBOL;
  currencySymbolMap.set('', baseSymbol);
  Array.from(docSel.options || []).forEach(function (option) {
    registerCurrencyOption(option, { skipEnsure: true });
  });
  currencySymbolMapReady = true;
}

function registerCurrencyOption(option, opts = {}) {
  if (!option) return;
  if (!opts.skipEnsure) ensureCurrencySymbolMap();
  const value = option.value || '';
  const symbol =
    (option.dataset && option.dataset.symbol) ||
    option.getAttribute('data-symbol');
  if (symbol) {
    currencySymbolMap.set(value, symbol);
    return;
  }
  const text = option.textContent ? option.textContent.trim() : '';
  if (text && text.toLowerCase() !== 'choose currency') {
    currencySymbolMap.set(value, text);
  }
}

function getDocumentCurrencySymbol() {
  const docSel = document.getElementById('document_currency');
  if (!docSel) return DEFAULT_CURRENCY_SYMBOL;
  ensureCurrencySymbolMap();
  const value = docSel.value || '';
  if (currencySymbolMap.has(value)) {
    return currencySymbolMap.get(value);
  }
  const selected = docSel.options && docSel.selectedIndex >= 0 ? docSel.options[docSel.selectedIndex] : null;
  return (
    (selected && selected.dataset && selected.dataset.symbol) ||
    (selected && selected.getAttribute('data-symbol')) ||
    (docSel.dataset && docSel.dataset.baseSymbol) ||
    docSel.getAttribute('data-base-symbol') ||
    DEFAULT_CURRENCY_SYMBOL
  );
}

function getBaseCurrencySymbol() {
  const docSel = document.getElementById('document_currency');
  if (!docSel) return DEFAULT_CURRENCY_SYMBOL;
  return (
    (docSel.dataset && docSel.dataset.baseSymbol) ||
    docSel.getAttribute('data-base-symbol') ||
    DEFAULT_CURRENCY_SYMBOL
  );
}

function ensureBaseCurrencyVisibilityStyles() {
  if (document.getElementById('base-currency-visibility-styles')) return;
  const style = document.createElement('style');
  style.id = 'base-currency-visibility-styles';
  style.textContent = [
    '.lyra-hide-base-currency .base-price,',
    '.lyra-hide-base-currency .base-currency-column {',
    '  display: none !important;',
    '}'
  ].join('\n');
  document.head.appendChild(style);
}

function getSelectedDocumentCurrencyCode() {
  const docSel = document.getElementById('document_currency');
  if (!docSel) return '';
  const selected = docSel.options && docSel.selectedIndex >= 0 ? docSel.options[docSel.selectedIndex] : null;
  return String(
    (selected && selected.dataset && selected.dataset.code) ||
    (selected && selected.getAttribute('data-code')) ||
    (selected && selected.textContent) ||
    ''
  ).trim().split(/\s+/)[0].toUpperCase();
}

function getBaseCurrencyCode() {
  const summary = document.getElementById('base-transaction-summary');
  const docSel = document.getElementById('document_currency');
  return String(
    (summary && summary.dataset && summary.dataset.baseCode) ||
    (docSel && docSel.dataset && docSel.dataset.baseCode) ||
    (document.querySelector('.base-currency-code') || {}).textContent ||
    ''
  ).trim().split(/\s+/)[0].toUpperCase();
}

function shouldHideBaseCurrencyUi() {
  const docCode = getSelectedDocumentCurrencyCode();
  const baseCode = getBaseCurrencyCode();
  const fxRate = parseFloat($('#fx_rate_to_base').val());
  if (docCode && baseCode) return docCode === baseCode;
  return Number.isFinite(fxRate) && Math.abs(fxRate - 1) < 0.000001;
}

function markBaseCurrencyTableHeaders() {
  $('table').each(function () {
    const $table = $(this);
    if (!$table.find('.base-price').length) return;
    $table.find('thead th').each(function () {
      const label = $(this).text().replace(/\s+/g, ' ').trim().toLowerCase();
      if (label === 'base currency price' || label.indexOf('price (base') !== -1 || label.indexOf('amount (base') !== -1) {
        $(this).addClass('base-currency-column');
      }
    });
  });
}

function updateBaseCurrencyVisibility() {
  ensureBaseCurrencyVisibilityStyles();
  markBaseCurrencyTableHeaders();
  const hideBase = shouldHideBaseCurrencyUi();
  document.body.classList.toggle('lyra-hide-base-currency', hideBase);
  $('#exchange_rate_container, #exchange_rate_date_container, #base_currency_transaction_section, #base-transaction-summary')
    .toggle(!hideBase);
}

function updateFlatDiscountSymbols() {
  const symbol = getDocumentCurrencySymbol();
  document.querySelectorAll('.discount-type option[value="flat"], select.rupee-sign option[value="flat"]').forEach(function (option) {
    option.textContent = symbol;
  });
}

function updateDocumentCurrencySymbolInput(symbol) {
  let symInput = document.getElementById('document_currency_symbol');
  if (!symInput) {
    symInput = document.createElement('input');
    symInput.type = 'hidden';
    symInput.id = 'document_currency_symbol';
    symInput.name = 'document_currency_symbol';
    const formEl = document.querySelector('form');
    if (formEl) formEl.appendChild(symInput);
  }
  if (symInput) symInput.value = symbol || getDocumentCurrencySymbol();
}

function refreshCurrencyUi() {
  rebuildCurrencySymbolMap();
  const symbol = getDocumentCurrencySymbol();
  $('.currency-symbol').text(symbol);
  updateFlatDiscountSymbols();
  updateDocumentCurrencySymbolInput(symbol);
  const docSel = document.getElementById('document_currency');
  const mirror = document.getElementById('document_currency_locked_value');
  if (docSel && mirror) {
    mirror.value = docSel.value || '';
  }
  updateBaseCurrencyVisibility();
  try { calculateTotals(); } catch (e) { }
}

function applyInitialPurchaseFxState() {
  const docSel = document.getElementById('document_currency');
  const rateEl = document.getElementById('fx_rate_to_base');
  const dateEl = document.getElementById('fx_rate_date');
  const initialCurrencyId = window.initialPurchaseCurrencyId;
  const initialFxRate = window.initialPurchaseFxRate;
  const initialFxDate = window.initialPurchaseFxDate;

  if (docSel && initialCurrencyId) {
    const selectedOption =
      docSel.querySelector('option[value="' + initialCurrencyId + '"]') ||
      (docSel.options && docSel.selectedIndex >= 0 ? docSel.options[docSel.selectedIndex] : null);
    setDocumentCurrencyValue(
      initialCurrencyId,
      selectedOption?.dataset?.code || selectedOption?.textContent || '',
      selectedOption?.dataset?.symbol || ''
    );
  }
  if (rateEl && initialFxRate) {
    rateEl.value = initialFxRate;
  }
  if (dateEl && initialFxDate) {
    dateEl.value = initialFxDate;
  }
  refreshCurrencyUi();
}

function setDocumentCurrencyValue(currencyId, currencyCode, currencySymbol) {
  const docSel = document.getElementById('document_currency');
  if (!docSel || currencyId === undefined || currencyId === null) return false;
  const cid = currencyId.toString();
  if (window.lockPurchaseOrderCurrency && docSel.dataset.lockedByVendor === '1' && cid !== (docSel.value || '')) {
    return false;
  }
  const wasLocked = docSel.dataset.lockedByVendor === '1';
  if (wasLocked && window.jQuery) {
    $(docSel).prop('disabled', false);
  } else if (wasLocked) {
    docSel.disabled = false;
  }
  let option = docSel.querySelector('option[value="' + cid + '"]');
  const symbol = currencySymbol || currencyCode || getBaseCurrencySymbol();
  if (!option) {
    option = document.createElement('option');
    option.value = cid;
    option.text = currencyCode || currencySymbol || cid;
    docSel.appendChild(option);
  }
  option.dataset.symbol = symbol;
  registerCurrencyOption(option);

  window.isAutoFillingCurrency = true;
  const $docSel = window.jQuery ? $(docSel) : null;
  if ($docSel) $docSel.data('ignore-change', true);
  try { docSel.value = cid; } catch (e) { }
  try {
    if ($docSel && typeof $docSel.val === 'function') {
      $docSel.val(cid).trigger('change');
    } else {
      docSel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  } catch (e) { }
  setTimeout(function () {
    try {
      if ($docSel) {
        if ($docSel.data('select2')) {
          $docSel.trigger('change.select2');
        }
        $docSel.data('ignore-change', false);
      }
    } catch (e) { }
    window.isAutoFillingCurrency = false;
    refreshCurrencyUi();
    if (docSel.dataset.lockedByVendor === '1') {
      setDocumentCurrencyLocked(true);
    } else if (wasLocked) {
      setDocumentCurrencyLocked(true);
    }
  }, 0);
  return true;
}


// Initialize shipping state dropdown with all Indian states
function getCompanyPrefix() {
  const pathParts = window.location.pathname.split('/');
  return pathParts[1] || '';
}

function setBasePriceDisplay($row, basePriceValue) {
  var $displayInput = $row.find('.o_price_display');
  if ($displayInput.length) {
    var baseSymbol = document.getElementById('base-transaction-summary')?.dataset.baseSymbol || document.getElementById('document_currency')?.dataset.baseSymbol || '';
    if (baseSymbol && !baseSymbol.trim().endsWith(' ')) baseSymbol += ' ';
    var formatted = Number.isFinite(basePriceValue) ? basePriceValue.toFixed(2) : '0.00';
    $displayInput.val(baseSymbol + formatted);
  }
}
function parseBasePriceFromRow($row) {
  var $displayInput = $row.find('.o_price_display');
  if ($displayInput.length) {
    var val = $displayInput.val() || '';
    return parseFloat(val.replace(/[^\d.-]/g, '')) || 0;
  }
  return 0;
}

function refreshPricesFromBase() {
  let fx = parseFloat($('#fx_rate_to_base').val()) || 1;
  $('#items-table tbody tr').each(function () {
    const $row = $(this);
    let priceBaseRaw = $row.data('price_base');
    let oPriceBaseRaw = $row.data('o_price_base');
    let priceBase = (priceBaseRaw !== undefined && priceBaseRaw !== null) ? parseFloat(priceBaseRaw) : NaN;
    let oPriceBase = (oPriceBaseRaw !== undefined && oPriceBaseRaw !== null) ? parseFloat(oPriceBaseRaw) : NaN;

    if (!Number.isFinite(priceBase) || priceBase === 0) {
      const displayBase = parseBasePriceFromRow($row);
      const hiddenBase = parseFloat($row.find('.o_price').val()) || displayBase || 0;
      if (displayBase > 0) {
        priceBase = displayBase;
      } else {
        const docPrice = parseFloat($row.find('.price').val()) || 0;
        if (docPrice > 0) {
          priceBase = docPrice * fx;
        }
      }
      if (hiddenBase > 0) {
        oPriceBase = hiddenBase;
      } else if (Number.isFinite(priceBase) && priceBase > 0) {
        oPriceBase = priceBase;
      }
      if (Number.isFinite(priceBase) && priceBase > 0) {
        $row.data('price_base', priceBase);
      }
      if (Number.isFinite(oPriceBase) && oPriceBase > 0) {
        $row.data('o_price_base', oPriceBase);
      }
    }

    if (Number.isFinite(priceBase) && priceBase >= 0) {
      let converted = (fx && fx !== 1) ? (priceBase / fx) : priceBase;
      $row.find('.price').val(converted.toFixed(4));
      if (Number.isFinite(oPriceBase) && oPriceBase >= 0) {
        $row.find('.o_price').val(oPriceBase.toFixed(4));
      }
      try { setBasePriceDisplay($row, priceBase); } catch (e) { }
      try { updateRowAmount($row); } catch (e) { }
    }
  });
  calculateTotals();
}


function seedBasePriceData() {
  $('#items-table tbody tr').each(function () {
    const $row = $(this);
    const hasBaseData = Number.isFinite(parseFloat($row.data('price_base')));
    if (hasBaseData && $row.data('price_base') !== 0) return;
    const basePriceValue = parseBasePriceFromRow($row);
    if (basePriceValue > 0) {
      $row.data('price_base', basePriceValue);
    }
    const oPriceInput = $row.find('.o_price');
    if (oPriceInput.length) {
      const oPriceValue = parseFloat(oPriceInput.val()) || basePriceValue || 0;
      if (oPriceValue > 0) {
        $row.data('o_price_base', oPriceValue);
      }
    }
  });
}


function ensureDocumentCurrencyLockStyles() {
  if (document.getElementById('document-currency-lock-styles')) return;
  const style = document.createElement('style');
  style.id = 'document-currency-lock-styles';
  style.textContent = [
    '#document_currency.document-currency-locked {',
    '  appearance: none;',
    '  -webkit-appearance: none;',
    '  -moz-appearance: none;',
    '  background-image: none;',
    '  padding-right: 0.75rem;',
    '}',
    '#document_currency.document-currency-locked + .select2-container .select2-selection__arrow {',
    '  display: none !important;',
    '}',
    '#document_currency.document-currency-locked + .select2-container .select2-selection--single {',
    '  padding-right: 0.75rem;',
    '  background-color: #e9ecef;',
    '  cursor: not-allowed;',
    '}',
    '#document_currency.document-currency-locked ~ .select2-container .select2-selection--single {',
    '  background-color: #e9ecef;',
    '  cursor: not-allowed;',
    '}'
  ].join('\n');
  document.head.appendChild(style);
}

function getDocumentCurrencySelect2Containers(sel) {
  if (!window.jQuery || !sel) return $();
  return $(sel)
    .next('.select2-container')
    .add($(sel).siblings('.select2-container'))
    .add($('#select2-document_currency-container').closest('.select2-container'));
}

function setDocumentCurrencyLocked(locked) {
  var sel = document.getElementById('document_currency');
  if (!sel) return;
  if (window.lockPurchaseOrderCurrency && !locked) {
    locked = true;
  }
  ensureDocumentCurrencyLockStyles();
  let mirror = document.getElementById('document_currency_locked_value');

  if (locked) {
    if (!mirror) {
      mirror = document.createElement('input');
      mirror.type = 'hidden';
      mirror.id = 'document_currency_locked_value';
      mirror.name = sel.name || 'document_currency';
      const formEl = sel.closest('form') || document.querySelector('form');
      if (formEl) formEl.appendChild(mirror);
    }
    mirror.value = sel.value || '';
    sel.classList.add('document-currency-locked');
    sel.dataset.lockedByVendor = '1';
    sel.setAttribute('aria-readonly', 'true');
    sel.disabled = true;
    if (window.jQuery) {
      $(sel).prop('disabled', true).trigger('change.select2');
    }
    getDocumentCurrencySelect2Containers(sel)
      .css('pointer-events', 'none')
      .find('.select2-selection')
      .attr('aria-disabled', 'true')
      .css('background-color', '#e9ecef');
  } else {
    sel.classList.remove('document-currency-locked');
    sel.dataset.lockedByVendor = '0';
    sel.removeAttribute('aria-readonly');
    sel.disabled = false;
    if (mirror) mirror.remove();
    if (window.jQuery) {
      $(sel).prop('disabled', false).trigger('change.select2');
    }
    getDocumentCurrencySelect2Containers(sel)
      .css('pointer-events', 'auto')
      .find('.select2-selection')
      .removeAttr('aria-disabled')
      .css('background-color', '');
  }
}

$(document).off('select2:opening.purchaseCurrencyLock', '#document_currency')
  .on('select2:opening.purchaseCurrencyLock', '#document_currency', function (event) {
    if (this.dataset.lockedByVendor === '1') {
      event.preventDefault();
      return false;
    }
  });

function updateExchangeRate(vendorId, currencyId, date, opts = {}) {
  const company = getCompanyPrefix();
  const url = `/${company}/currencies/api/vendor_rate/`;
  const params = new URLSearchParams();
  if (vendorId) params.append('vendor_id', vendorId);
  if (currencyId) params.append('currency_id', currencyId);
  if (date) params.append('date', date);

  fetch(`${url}?${params.toString()}`)
    .then(response => response.json())
    .then(data => {
      if (data.ok) {
        var docSel = document.getElementById('document_currency');
        if (data.currency_id && docSel && (opts.forceDocumentCurrency || !currencyId)) {
          setDocumentCurrencyValue(data.currency_id, data.currency_code, data.currency_symbol);
          setDocumentCurrencyLocked(true);
        } else if (data.currency_id && docSel) {
          const existingOption = docSel.querySelector('option[value="' + data.currency_id.toString() + '"]');
          if (existingOption && data.currency_symbol) {
            existingOption.dataset.symbol = data.currency_symbol;
            registerCurrencyOption(existingOption);
          }
        }

        $('#fx_rate_to_base').val(data.rate);
        $('#fx_rate_date').val(data.rate_effective_from || data.date);
        try { $('#fx_rate_to_base').trigger('input'); } catch (e) { }

        // Update UI based on currency
        const baseCode = $('#exchange_rate_container .base-currency-code').first().text();
        updateBaseCurrencyVisibility();


        // Update symbols
        if (data.currency_symbol) {
          $('.currency-symbol').text(data.currency_symbol);
        }
        $('.doc-currency-code').text(data.currency_code);
        refreshCurrencyUi();

        setTimeout(function () {
          try { refreshPricesFromBase(); } catch (e) { calculateTotals(); }
        }, 50);
      }
    })
    .catch(error => console.error('Error fetching exchange rate:', error));
}

function applyVendorPaymentTerms(data) {
  var terms = data && data.payment_terms ? data.payment_terms : null;
  var $payTerms = $('#pay-terms, select[name="payment_term"]').first();

  if (!$payTerms.length) {
    window.applyVendorDefaultPaymentTerms = false;
    return;
  }

  var shouldApply = !!window.applyVendorDefaultPaymentTerms || !$payTerms.val();
  if (!shouldApply) {
    return;
  }

  if (terms && terms.id) {
    var label = terms.name || terms.id;
    if (terms.days !== null && terms.days !== undefined && terms.name) {
      label = terms.name + ' (' + terms.days + ' days)';
    }
    $payTerms.find('option[value="' + terms.id + '"]').remove();
    $payTerms.append(new Option(label, terms.id, true, true)).trigger('change');
  } else {
    $payTerms.val(null).trigger('change');
  }

  window.applyVendorDefaultPaymentTerms = false;
}

$(document).on('change', '#document_currency', function (e) {
  if (window.isAutoFillingCurrency) return;
  if ($(this).data('ignore-change') === true) return;
  if (this.dataset.lockedByVendor === '1') {
    refreshCurrencyUi();
    return;
  }
  // Skip if triggered internally to avoid loops
  if (e.namespace === 'select2-internal') return;
  this.dataset.userSelected = '1';

  const currencyId = $(this).val();
  const vendorId = $('#vendor_select').val();
  const date = $('#id_date').val() || $('input[name="date"]').val();

  refreshCurrencyUi();
  updateExchangeRate(vendorId, currencyId, date);
});

$(document).on('input change', '#fx_rate_to_base', function () {
  updateBaseCurrencyVisibility();
  refreshPricesFromBase();
});

$(document).on('change', '#fx_rate_date', function () {
  calculateTotals();
});

$(document).on('change', '#id_date, input[name="date"]', function () {
  const vendorId = $('#vendor_select').val();
  const currencyId = $('#document_currency').val();
  const date = $(this).val();
  updateExchangeRate(vendorId, currencyId, date);
});

function initializeShippingStateDropdown() {
  const stateSelect = document.getElementById('sa_state');
  if (!stateSelect) {
    console.warn('sa_state element not found');
    return;
  }

  if (window.LyraLocationSelects && typeof window.LyraLocationSelects.init === 'function') {
    window.LyraLocationSelects.init(document.getElementById('shippingAddressModal') || document);
    return;
  }

  const states = [
    'Andaman and Nicobar Islands', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar',
    'Chandigarh', 'Chhattisgarh', 'Dadra and Nagar Haveli', 'Daman and Diu', 'Delhi',
    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
    'Ladakh', 'Lakshadweep', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya',
    'Mizoram', 'Nagaland', 'Odisha', 'Puducherry', 'Punjab', 'Rajasthan', 'Sikkim',
    'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
  ];

  // Check if Select2 is available
  const hasSelect2 = window.jQuery && $.fn.select2;

  // Destroy existing Select2 instance if it exists
  if (hasSelect2 && $(stateSelect).hasClass('select2-hidden-accessible')) {
    try {
      $(stateSelect).select2('destroy');
    } catch (e) {
      console.warn('Error destroying Select2:', e);
    }
  }

  // Clear existing options
  stateSelect.innerHTML = '<option value="">Select State</option>';

  // Add state options
  states.forEach(state => {
    const option = document.createElement('option');
    option.value = state;
    option.textContent = state;
    stateSelect.appendChild(option);
  });

  // Initialize Select2 if available
  if (hasSelect2) {
    try {
      $(stateSelect).select2({
        placeholder: 'Select State',
        allowClear: true,
        width: '100%',
        dropdownAutoWidth: true,
        dropdownParent: $('#shippingAddressModal')
      });
    } catch (e) {
      console.warn('Error initializing Select2 for state dropdown:', e);
    }
  }
}
$('#pay-terms').select2({
  placeholder: '',
  allowClear: true,
  minimumInputLength: 0,
  ajax: {
    url: '/PayTerms/payterm_list/',
    dataType: 'json',
    // delay: 250,

    processResults: function (data) {
      let results = data.map(function (item) {
        return { id: item.id, text: item.name };
      });
      results.push({
        id: 'new',
        text: '+ New',
        isNew: true // custom flag to identify this special option
      });
      return { results: results };
    },
    cache: true
  },

});

$('#pay-terms').on('select2:select', function (e) {
  var data = e.params.data;
  if (data.isNew) {

    $('#paymentTermsModal').modal('show');

    $('#pay-terms').val(null).trigger('change');
  }
});


function loadPaymentTerms() {
  $.ajax({
    url: '/PayTerms/payterm_list/',
    type: 'GET',
    dataType: 'json',
    success: function (data) {
      let tbody = $('#paymentTermsModal table tbody');
      tbody.empty();

      data.forEach(function (term) {
        let row = `<tr data-id="${term.id}">
            <td><input type="text" class="form-control term-name" value="${term.name}"></td>
            <td><input type="number" class="form-control term-days" value="${term.days}"></td>
            <td class="text-center">
              <button type="button" class="btn btn-danger btn-sm delete-row" style="display:none;">Delete</button>
            </td>
          </tr>`;
        tbody.append(row);
      });

      // Add an empty row for new entry - optional, user can also use Add New button
      // tbody.append(newRow);
    },
    error: function () {
      console.error("Failed to load payment terms");
    }
  });
}

$('#paymentTermsModal').on('show.bs.modal', loadPaymentTerms);

$('#paymentTermsModal').on('click', '.delete-row', function (event) {
  event.preventDefault();
  event.stopImmediatePropagation();

  let id = $(this).closest('tr').data('id');
  if (id) {
    deletedTerms.push(id); // track for backend
  }

  $(this).closest('tr').remove();
});

let deletedTerms = [];



// Add new row on Add New button click (supports multiple pages/templates)
// Delegated handler so it works whether the modal was rendered in purchase, quotation, or other pages
$(document).on('click', '#paymentTermsModal #addNew, #addNew', function (e) {
  e.preventDefault();
  var newRow = '<tr data-id="">' +
    '<td><input type="text" class="form-control term-name" placeholder="Term Name"></td>' +
    '<td><input type="number" class="form-control term-days" placeholder="Number of days"></td>' +
    '<td class="text-center"><button type="button" class="btn btn-danger btn-sm delete-row" style="display:none;">Delete</button></td>' +
    '</tr>';
  $('#paymentTermsModal table tbody').append(newRow);
  // Show delete buttons once there is more than one row to allow removal
  var $rows = $('#paymentTermsModal table tbody tr');
  if ($rows.length > 1) {
    $rows.find('.delete-row').show();
  }
});


// Save button ajax save all changes
$(document).on('click', '#paymentTermsModal .btn-primary', function (e) {//byadarsh
  e.preventDefault();

  let terms = [];

  $('#paymentTermsModal table tbody tr').each(function () {
    let id = $(this).attr('data-id');
    let name = $(this).find('.term-name').val();
    let days = $(this).find('.term-days').val();

    if (name && days !== "") {
      terms.push({
        id: id,     // empty string if new row
        name: name,
        days: parseInt(days)
      });
    }
  });
  // Build company-prefixed URL for payment terms save
  var pathParts = window.location.pathname.split('/');
  var companyCode = pathParts[1] || '';
  var payTermsUrl = '/' + companyCode + '/PayTerms/save_payterms/';

  // Helper to read CSRF token from cookie
  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  $.ajax({
    url: payTermsUrl,
    method: 'POST',
    contentType: 'application/json',
    data: JSON.stringify({ terms: terms, deleted: deletedTerms }),
    // include CSRF token for JSON POST
    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') },
    success: function (response) {
      alert("Payment terms saved successfully");
      deletedTerms = [];

      //by adarsh Get the newly created payment term ID and name from response
      let newTermId = response.last_created_id;
      let newTermName = response.last_created_name;

      // Close the modal
      var paymentModal = bootstrap.Modal.getInstance(document.getElementById('paymentTermsModal'));
      if (paymentModal) {
        paymentModal.hide();
      }

      // Select the newly created payment term in the select2 field
      if (newTermId && newTermName) {
        setTimeout(function () {
          // Create a new option and add it to select2
          var newOption = new Option(newTermName, newTermId, true, true);
          $('#pay-terms').append(newOption).trigger('change');
        }, 100);
      }//byadarsh
    },
    error: function () {
      alert("Error saving payment terms");
    }
  });

});


$('#vendor_select').select2({
  placeholder: '',
  allowClear: true,
  minimumInputLength: 1,
  ajax: {
    url: '/purchase/vendor/',
    dataType: 'json',
    delay: 250,
    data: function (params) {
      lastVendorSearchTerm = params.term || '';

      return { q: params.term };
    },
    processResults: function (data) {
      let results = data.map(function (item) {
        return {
          id: item.id,
          text: item.name,
          payment_terms_id: item.payment_terms_id,
          payment_terms_name: item.payment_terms_name,
          payment_terms_days: item.payment_terms_days
        };
      });
      results.push({
        id: 'new',
        text: '+ New',
        isNew: true // custom flag to mark special option
      });
      return { results: results };
    },
    cache: true
  }
});


$('#purchase_person_select').select2({
  placeholder: '',
  allowClear: true,
  minimumInputLength: 1,
  ajax: {
    url: '/purchase/purchase_person/',
    dataType: 'json',
    delay: 250,
    data: function (params) {
      lastpurchasepersonSearchTerm = params.term || '';

      return { q: params.term };
    },
    processResults: function (data) {
      let results = data.map(function (item) {
        return { id: item.id, text: item.name };
      });
      results.push({
        id: 'new',
        text: '+ New',
        isNew: true // custom flag to mark special option
      });
      return { results: results };
    },
    cache: true
  }
});

// $('#customer_select').on('select2:select', function (e) {
//     var data = e.params.data;
//     if (data.isNew) {
//         saveFormData();

//         var currentUrl = window.location.href; // remember current page
//         // redirect to customer create page, pass current page as 'next'
//         window.location.href = '/purchase/customers/add/?next=' + encodeURIComponent(currentUrl);
//     }
// });


$('#vendor_select').on('select2:select', function (e) {
  var data = e.params.data;
  if (data.isNew) {
    // Build company-prefixed URL for vendor create form
    var pathParts = window.location.pathname.split('/');
    var companyCode = pathParts[1] || '';
    var vendorFormUrl = '/' + companyCode + '/purchase/vendor_createform/';

    $.get(vendorFormUrl, function (formHtml) {
      var $mb = $('#addVendorModal .modal-body');
      // Clear any previous content/errors to avoid leftover messages from earlier attempts
      $mb.empty();
      $mb.html(formHtml);


      // ✅ After form is injected, generate code from search term
      setTimeout(function () {
        var nameToUse = $mb.find('input[name="company_name"]').val().trim() ||
          $mb.find('input[name="first_name"]').val().trim();
        if (nameToUse) {
          autoGenerateVendorCode(nameToUse);
        }
      }, 300);
      // Initialize by adarsh select2 for any selects injected into the vendor modal
      try {
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
          $mb.find('.select2').each(function () {
            var $el = $(this);
            // destroy any previous instance to be safe
            try { $el.select2('destroy'); } catch (e) { }
            $el.select2({
              placeholder: $el.data('placeholder') || 'Select',
              allowClear: true,
              width: 'resolve',
              dropdownParent: $('#addVendorModal')
            });
          });
        }
      } catch (initErr) { console.warn('Select2 init failed in vendor modal:', initErr); }//byadarsh
      try {
        // Ensure injected form doesn't trigger native browser validation UI
        var $injectedForm = $mb.find('form').first();
        if ($injectedForm.length) {
          $injectedForm.attr('novalidate', 'novalidate');
          // Ensure form action uses company-prefixed URL
          try {
            var pathParts = window.location.pathname.split('/');
            var companyCode = pathParts[1] || '';
            // If form has an action and it's a module-relative path, replace with company-prefixed path
            var origAction = $injectedForm.attr('action') || '';
            if (origAction.indexOf('/purchase/') === 0 || origAction.indexOf('/Items/add_vendor') === 0 || origAction.indexOf('/Items/add_vendor/') === 0) {
              $injectedForm.attr('action', '/' + companyCode + '/purchase/add_vendor/');
            } else if (!origAction) {
              // default to company-prefixed add_vendor
              $injectedForm.attr('action', '/' + companyCode + '/purchase/add_vendor/');
            }
          } catch (e) { /* ignore */ }
        }
        // Hide any server-rendered or previously-inserted error elements until user submits
        $mb.find('.text-danger.small, .text-danger, .invalid-feedback, .alert.alert-danger').hide();
        // Also hide any nodes that exactly equal the common required text
        $mb.find('*').filter(function () { return $(this).text().trim() === 'This field is required.'; }).hide();
        // mark modal as not-yet-submitted
        $('#addVendorModal').data('vendorFormSubmitted', false);

        var bsModalEl = document.getElementById('addVendorModal');
        var bsModal = new bootstrap.Modal(bsModalEl);
        bsModal.show();
        $('#addVendorModal').find('input[name="first_name"]').val(lastVendorSearchTerm);
        $('#addVendorModal').find('input[name="company_name"]').val(lastVendorSearchTerm);
        // ✅ Auto-generate vendor code when modal opens
        if (lastVendorSearchTerm) {
          autoGenerateVendorCode(lastVendorSearchTerm);
        }
        console.log("lastVendorSearchTerm:", lastVendorSearchTerm);
      } catch (err) {
        // Fallback to jQuery modal if available
        console.warn('Bootstrap Modal API not available, falling back to jQuery modal', err);
        $('#addVendorModal').modal('show');
      }
    });
    // Reset selection after opening modal
    $('#vendor_select').val(null).trigger('change');
  } else {
    window.applyVendorDefaultPaymentTerms = true;
    loadVendorDetails(data.id);
  }
});

// AJAX submit for vendor modal: supports JSON success {id, name} or returns HTML with form (validation errors)
$(document).on('submit', '#addVendorModal form', function (ev) {
  console.log("submitting addVendorModal form");
  ev.preventDefault();
  var $form = $(this);
  var action = $form.attr('action') || window.location.href;
  var method = ($form.attr('method') || 'POST').toUpperCase();

  var formData = new FormData(this);

  $.ajax({
    url: action,
    type: method,
    data: formData,
    processData: false,
    contentType: false,
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    success: function (response, status, xhr) {
      // Try to parse JSON
      var ct = xhr.getResponseHeader('Content-Type') || '';
      // Accept JSON responses even if content-type mismatches
      var parsed = null;
      try {
        parsed = (typeof response === 'object') ? response : JSON.parse(response);
      } catch (err) {
        // ignore parse error
      }
      if (parsed && (parsed.success === true || (parsed.id && parsed.name))) {
        var data = parsed;
        // Close modal reliably: prefer existing instance, fallback to creating one, then jQuery
        var modalEl = document.getElementById('addVendorModal');
        try {
          var modalEl = document.getElementById('addVendorModal');

          if (window.bootstrap && bootstrap.Modal) {
            var instance = bootstrap.Modal.getInstance(modalEl);
            if (instance) {
              instance.hide();
            }
          } else {
            $('#addVendorModal').modal('hide');
          }

        } catch (e) {
          try { $('#addVendorModal').modal('hide'); } catch (ee) { /* ignore */ }
        }

        // Remove any previous errors and clear modal body
        $('#addVendorModal .modal-body .alert.alert-danger').remove();
        $('#addVendorModal .modal-body .text-danger.small').remove();

        var displayName = data.name || (data.first_name ? (data.first_name + (data.last_name ? ' ' + data.last_name : '')) : 'New');
        var newOption = new Option(displayName, data.id, true, true);
        var $sel = $('#vendor_select');
        // Remove any existing option with same value to avoid duplicates
        $sel.find('option[value="' + data.id + '"]').remove();
        $sel.append(newOption).trigger('change');
        console.log("just befor loadVendorDetails");
        //added by neha on 4-2-26 
        loadVendorDetails(data.id);
        // Also trigger select2 select programmatically
        // $sel.val(data.id).trigger('select2:select');
        $sel.append(newOption).val(data.id).trigger('change');

        // Clear modal content after short delay to avoid race if Bootstrap animates
        setTimeout(function () { $('#addVendorModal .modal-body').empty(); }, 300);
        return;
      }

      // Otherwise assume HTML returned (form with errors or full form) - replace modal body
      $('#addVendorModal .modal-body').html(response);
      // Initialize by adarshselect2 for any selects injected into the modal (validation/error case)
      try {
        var $mbv = $('#addVendorModal .modal-body');
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
          $mbv.find('.select2').each(function () {
            var $el = $(this);
            try { $el.select2('destroy'); } catch (e) { }
            $el.select2({ placeholder: $el.data('placeholder') || 'Select', allowClear: true, width: 'resolve', dropdownParent: $('#addVendorModal') });
          });
        }
      } catch (ie) { console.warn('Select2 init failed after vendor submit response:', ie); }//byadarsh
      // Reveal errors because this was a submit attempt
      try {
        $('#addVendorModal').data('VendorFormSubmitted', true);
        var $mb = $('#addVendorModal .modal-body');
        $mb.find('.text-danger.small, .text-danger, .invalid-feedback, .alert.alert-danger').show();
        $mb.find('*').filter(function () { return $(this).text().trim() === 'This field is required.'; }).show();
      } catch (e) { }
    },
    error: function (xhr) {
      // Better error handling: if server returned JSON errors, render them in modal
      var ct = xhr.getResponseHeader('Content-Type') || '';
      var handled = false;
      try {
        var json = xhr.responseJSON || JSON.parse(xhr.responseText || '{}');
        if (json && json.errors) {
          // Clear any previous field errors
          $('#addVendorModal .text-danger.small').remove();
          $('#addVendorModal .alert.alert-danger').remove();

          // Render non-field errors
          if (json.errors.__all__ || json.errors.non_field_errors) {
            var nf = json.errors.__all__ || json.errors.non_field_errors;
            $('#addVendorModal .modal-body').prepend('<div class="alert alert-danger">' + nf.join('<br>') + '</div>');
          }

          // Render field-specific errors next to inputs
          Object.keys(json.errors).forEach(function (field) {
            if (field === '__all__' || field === 'non_field_errors') return;
            var msgs = json.errors[field];
            // Try to find input/select/textarea with that name
            var $field = $('#addVendorModal').find('[name="' + field + '"]');
            if ($field.length) {
              // Append error messages after the field (avoid duplicates)
              $field.each(function () {
                var $el = $(this);
                msgs.forEach(function (m) {
                  $el.after('<div class="text-danger small">' + m + '</div>');
                });
              });
            } else {
              // If not found, show at top
              $('#addVendorModal .modal-body').prepend('<div class="alert alert-danger"><strong>' + field + ':</strong> ' + msgs.join(', ') + '</div>');
            }
          });

          // Mark that the user attempted to submit so we reveal errors
          $('#addVendorModal').data('VendorFormSubmitted', true);
          // Reveal any errors we just added (CSS hides them by default inside the modal)
          try {
            var $mb_errors = $('#addVendorModal .modal-body');
            $mb_errors.find('.text-danger.small, .text-danger, .invalid-feedback, .alert.alert-danger').show();
            // scroll to first error
            var $firstErr = $mb_errors.find('.text-danger.small, .alert.alert-danger').first();
            if ($firstErr.length) {
              // if modal body is scrollable, scroll that; otherwise scroll document
              var $scrollParent = $mb_errors;
              $scrollParent.animate({ scrollTop: ($firstErr.position().top - 20) }, 250);
            }
          } catch (ee) { }

          handled = true;
        }
      } catch (err) {
        // ignore parse errors
      }

      if (!handled) {
        if (ct.indexOf('text/html') !== -1) {
          $('#addVendorModal .modal-body').html(xhr.responseText);
          try { //byadarsh
            var $mb3 = $('#addVendorModal .modal-body');
            if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
              $mb3.find('.select2').each(function () {
                var $el = $(this);
                try { $el.select2('destroy'); } catch (e) { }
                $el.select2({ placeholder: $el.data('placeholder') || 'Select', allowClear: true, width: 'resolve', dropdownParent: $('#addVendorModal') });
              });
            }
          } catch (ee) { console.warn('Select2 init failed for error HTML:', ee); }//byadarsh
          // Reveal errors since this is response after failed submit
          try {
            $('#addVendorModal').data('VendorFormSubmitted', true);
            var $mb2 = $('#addVendorModal .modal-body');
            $mb2.find('.text-danger.small, .text-danger, .invalid-feedback, .alert.alert-danger').show();
            $mb2.find('*').filter(function () { return $(this).text().trim() === 'This field is required.'; }).show();
          } catch (ee) { }
        } else {
          alert('Error saving vendor. See console for details.');
          console.error('Vendor save error', xhr);
        }
      }
    }
  });
});

// by adarshLoad and display selected vendor details in billing/shipping area
document.addEventListener('DOMContentLoaded', function () {
  console.log('DOMContentLoaded fired for vendor details');
  function qs(selector) { return document.querySelector(selector); }
  const select = qs('#id_vendor') || qs('#vendor_select') || qs('select[name="vendor"]');
  console.log('Vendor select element found:', select);
  const vendorInfo = qs('#vendor-info');
  console.log('Vendor info element found:', vendorInfo);
  const billingName = qs('#billing-name');
  const billingAddress = qs('#billing-address');
  const billingContact = qs('#billing-contact');
  const billingGst = qs('#billing-gst');
  const placeOfSupplyDiv = qs('#place-of-supply');

  function clearVendor() {
    if (!vendorInfo) return;
    vendorInfo.style.display = 'none';
    if (billingName) billingName.innerText = '';
    if (billingAddress) billingAddress.innerText = '';
    if (billingContact) billingContact.innerText = '';
    if (billingGst) billingGst.innerText = '';
    // clear any shipping info the user may have previously entered
    const shipNameEl = document.getElementById('shipping-name');
    const shipAddrEl = document.getElementById('shipping-address');
    const shipContactEl = document.getElementById('shipping-contact');
    if (shipNameEl) shipNameEl.innerText = '';
    if (shipAddrEl) shipAddrEl.innerText = 'New Address';
    if (shipContactEl) shipContactEl.innerText = '';
    // clear hidden shipping inputs so previous vendor's data doesn't persist
    ['shipping_attention', 'shipping_email', 'shipping_phone', 'shipping_country', 'shipping_address1', 'shipping_address2', 'shipping_city', 'shipping_state', 'shipping_postal_code'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    if (placeOfSupplyDiv) placeOfSupplyDiv.innerText = '';

    // Unlock currency if vendor is cleared
    if (typeof setDocumentCurrencyLocked === 'function') {
      setDocumentCurrencyLocked(false);
    }
    const docSel = document.getElementById('document_currency');
    if (docSel) {
      docSel.dataset.userSelected = '0';
      setDocumentCurrencyValue('', '', getBaseCurrencySymbol());
      refreshCurrencyUi();
    }
  }

  // Clear inputs inside the Shipping Address modal so previous vendor's values don't persist
  function clearShippingModal() {
    const ids = ['sa_attention', 'sa_email', 'sa_phone', 'sa_country', 'sa_address1', 'sa_address2', 'sa_city', 'sa_state', 'sa_postal'];
    ids.forEach(function (id) {
      const el = document.getElementById(id);
      if (el) {
        if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') el.value = '';
        else el.innerText = '';
      }
    });
  }

  // function fillVendor(data){
  //   console.log('fillVendor 1 called with data:', data);
  //   if(!vendorInfo) return;
  //   if(!data || data.error){ clearVendor(); return; }
  //   vendorInfo.style.display = 'block';
  //   const b = data.billing || {};
  //   if(billingName) billingName.innerText = b.name || '';
  //   let addr = '';
  //   if(b.address_line_1) addr += b.address_line_1 + ', ';
  //   if(b.address_line_2) addr += b.address_line_2 + ', ';
  //   if(b.city) addr += b.city + ', ';
  //   if(b.postal_code) addr += b.postal_code + ', ';
  //   if(b.country) addr += b.country;
  //   if(billingAddress) billingAddress.innerText = addr.replace(/, $/, '');
  //   if(billingContact) billingContact.innerText = (b.email ? b.email + (b.phone ? ' | ' + b.phone : '') : (b.phone||''));
  //   if(billingGst) billingGst.innerText = b.tax_number ? ('Tax Number: ' + b.tax_number) : '';
  //   if(placeOfSupplyDiv){
  //     const savedPlaceField = document.querySelector('input[name="place_of_supply"]');
  //     const savedVal = savedPlaceField ? (savedPlaceField.value || '').trim() : '';
  //     const state = (savedVal || data.place_of_supply || '').toLowerCase();
  //     console.log('Place of Supply - saved:', savedVal, 'from data:', data.place_of_supply, 'final state:', state);

  //     // Find the properly cased state value from the states array
  //     const states = [
  //       'Andaman and Nicobar Islands', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar',
  //       'Chandigarh', 'Chhattisgarh', 'Dadra and Nagar Haveli', 'Daman and Diu', 'Delhi',
  //       'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
  //       'Ladakh', 'Lakshadweep', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya',
  //       'Mizoram', 'Nagaland', 'Odisha', 'Puducherry', 'Punjab', 'Rajasthan', 'Sikkim',
  //       'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
  //     ];
  //     const properCasedState = states.find(s => s.toLowerCase() === state) || (savedVal || data.place_of_supply || '');
  //     placeOfSupplyDiv.innerText = properCasedState;

  //     // Also update hidden field
  //     const hiddenField = document.querySelector('input[name="place_of_supply"]');
  //     if(hiddenField && properCasedState) {
  //       hiddenField.value = properCasedState;
  //     }
  //   }
  // }

  function loadVendorDetails(vendorId) {
    console.log('loadVendorDetails called with vendorId:', vendorId);
    if (!vendorId) { clearVendor(); return; }
    const docSel = document.getElementById('document_currency');
    if (docSel) {
      docSel.dataset.userSelected = '0';
    }
    const companyPrefix = getCompanyPrefix();
    const url = companyPrefix
      ? `/${companyPrefix}/purchase/vendor/${vendorId}/detail/`
      : `/purchase/vendor/${vendorId}/detail/`;
    console.log('Fetching vendor details from:', url);
    fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(r => {
        console.log('Fetch response status:', r.status);
        if (!r.ok) {
          throw new Error(`Vendor detail request failed with status ${r.status}`);
        }
        return r.json();
      })
      .then(data => {
        // Check if we have saved shipping data from the purchase order
        const hasSavedShipping = window.hasSavedShippingData || false;
        console.log('Has saved shipping data:', hasSavedShipping);

        // Pass the flag to fillVendor function
        fillVendor(data, hasSavedShipping);
      })
      .catch(err => {
        console.error('Error loading vendor details:', err);
        clearVendor();
      });

  }

  if (select) {
    console.log('Setting up vendor select event listeners');
    select.addEventListener('change', function () {
      console.log('Vendor select change event, value:', this.value);
      // Clear any shipping modal fields so they don't show previous vendor's data
      try { clearShippingModal(); } catch (err) { console.warn('clearShippingModal failed', err); }
      // Also by adarsh clear the shipping display area when vendor changes
      const shipNameEl = document.getElementById('shipping-name');
      const shipAddrEl = document.getElementById('shipping-address');
      if (shipNameEl) shipNameEl.innerText = '';
      if (shipAddrEl) shipAddrEl.innerText = 'New Address';
      // Clear the hidden shipping input fields so old vendor data doesn't persist
      ['shipping_attention', 'shipping_email', 'shipping_phone', 'shipping_country', 'shipping_address1', 'shipping_address2', 'shipping_city', 'shipping_state', 'shipping_postal_code'].forEach(function (id) {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });//by adarsh
      window.applyVendorDefaultPaymentTerms = true;
      loadVendorDetails(this.value);
    });

    // Also handle select2 selection event
    if (window.jQuery) {
      console.log('jQuery found, setting up Select2 event handlers');
      $(select).on('select2:select', function (e) {
        var id = $(this).val();
        console.log('Select2 select event, id:', id);
        // Clear//by adarsh shipping modal and hidden inputs when vendor changes
        try { clearShippingModal(); } catch (err) { console.warn('clearShippingModal failed', err); }
        ['shipping_attention', 'shipping_email', 'shipping_phone', 'shipping_country', 'shipping_address1', 'shipping_address2', 'shipping_city', 'shipping_state', 'shipping_postal_code'].forEach(function (fieldId) {
          const el = document.getElementById(fieldId);
          if (el) el.value = '';
        }); //by adarsh
        if (id) {
          window.applyVendorDefaultPaymentTerms = true;
          loadVendorDetails(id);
          loadVendorPreferredItems(id);//added by sree on 19-02-26 fro preferred items
        }
      });

      // When Select2 dropdown is closed without a selection, hide vendor info if no vendor selected
      $(select).on('select2:close', function (e) {
        try {
          if (!$(this).val() || $(this).val() === '') {
            clearVendor();
          }
        } catch (err) { console.warn('Error handling select2:close', err); }
      });
      // When an option is unselected (clear), hide vendor info immediately
      $(select).on('select2:unselect', function (e) {
        clearVendor();
      });
    }

    // Load initial vendor if present
    const init = select.value;
    console.log('Initial vendor value:', init);
    if (init) loadVendorDetails(init);

    // Also set up a fallback timer to load vendor if select2 initialization delays it
    setTimeout(function () {
      const currentVal = select.value || $(select).val();
      console.log('Fallback check - current vendor value:', currentVal);
      if (currentVal && !document.getElementById('vendor-info').style.display || document.getElementById('vendor-info').style.display === 'none') {
        console.log('Fallback: loading vendor details for:', currentVal);
        loadVendorDetails(currentVal);
      }
    }, 1000);
  } else {
    console.log('Vendor select element not found!');
  }



  // Also initialize on page load in case modal exists
  setTimeout(initializeShippingStateDropdown, 500);
});  //by adarsh

$('#purchase_person_select').on('select2:select', function (e) {
  var data = e.params.data;
  if (data.isNew) {
    $.get('/purchase/purchaseperson_createform/', function (formHtml) {
      $('#purchasepersonCreateModal .modal-body').html(formHtml);
      try {
        var spModalEl = document.getElementById('purchasepersonCreateModal');
        var spModal = new bootstrap.Modal(spModalEl);
        spModal.show();
        $('#purchasepersonCreateModal').find('input[name="name"]').val(lastpurchasepersonSearchTerm);
        console.log("lastpurchasepersonSearchTerm:", lastpurchasepersonSearchTerm);
      } catch (err) {
        console.warn('Bootstrap Modal API not available, falling back to jQuery modal', err);
        $('#purchasepersonCreateModal').modal('show');
      }
    });
    // Reset selection after opening modal
    $('#purchase_person_select').val(null).trigger('change');
  }
});



// $(document).ready(function() {
// $('.item_select').select2({
//       placeholder: '',
//       allowClear: true,
//       minimumInputLength: 1,
//       ajax: {
//         url: '/sales/get_item_sales/',
//         dataType: 'json',
//         delay: 250,
//         data: function(params) {
//           return { q: params.term };
//         },
//         processResults: function(data) {
//           let results = data.map(function(item) {
//             return { id: item.id, text: item.name,description: item.sell_desc,
//             price: item.sl_price,uom:item.unit };
//           });
//           results.push({
//             id: 'new',
//             text: '+ New',
//             isNew: true // custom flag to mark special option
//           });
//           console.log("this working");
//           return { results: results };
//         },
//         cache: true
//       }
//     });
//  });
// $('.item_select').on('select2:select', function (e) {
//     var data = e.params.data;
//     if (data.isNew) {
//         saveFormData();

//         var currentUrl = window.location.href; // remember current page
//         // redirect to vendor create page, pass current page as 'next'
//         window.location.href = '/Items/add_item/?next=' + encodeURIComponent(currentUrl);
//     }

//   // Save data periodically or on input changes (optional)
//    // form.addEventListener('input', saveFormData);

//     // Clear saved data on successful submission
//     // form.addEventListener('submit', () => {
//     //     sessionStorage.removeItem('savedPurchaseForm');
//     // });
// });





function initItemSelect($el) {
  $el.select2({
    placeholder: 'Select Item',
    allowClear: true,
    minimumInputLength: 1,
    // multiple: false,              // ✅ ensure single select
    // closeOnSelect: true,          // ✅ close dropdown when selected
    ajax: {
      url: '/purchase/get_item_purchase/',
      dataType: 'json',
      delay: 250,
      data: params => {
        lastItemSearchTerm = params.term || '';
        return {
          q: params.term
        };
      },
      processResults: function (data, params) {
        let results = data.map(item => ({
          id: item.id + '_' + (item.b_id || ''),
          text: item.name + ' ' + item.unit,
          description: item.sell_desc,
          price: item.sl_price,
          gstinclude: item.gstinclude,
          o_price: item.o_price,
          uom: item.unit,
          hsn_code: item.hsn_code || item.sac_code || '',
          tax_id: item.tax_id,
          tax_name: item.tax_name,
          tax_rate: item.tax_rate,
          tax_pref: item.tax_pref
        }));

        // ✅ Only add "+ New Item" option if no results found
        if (params.term && results.length === 0) {
          results.push({
            id: 'new',
            text: '+ Create new item',
            isNew: true
          });
        }

        return { results: results };
      }
    },
    // Custom template to show "+ New" with search term
    templateResult: function (item) {
      if (item.isNew) {
        return $('<span style="color: #dce2f9; font-weight: 500;"><i class="bi bi-plus-circle"></i> Create new item</span>');
      }
      return item.text;
    },


  });

  // $row.find('.qty').val(1);
  // $row.find('.price').val(data.price || 0);
  // $row.find('.item-discount').val(0);       // ✅ ensures 0 after loading item
  // $row.find('.discount-type').val('flat'); 


  // Handle selection of item
  $el.on('select2:select', function (e) {
    if (!e.params || !e.params.data) {
      return;
    }
    const data = e.params.data;
    const $sel = $(this);
    const $row = $sel.closest('tr');

    if (data.isNew) {
      const searchTerm = lastItemSearchTerm || '';
      $('#item_name').val(searchTerm);

      // Get the current row index
      const rowIndex = $row.index();

      // Set the global currentRowIndex
      if (window.setCurrentRowIndex) {
        window.setCurrentRowIndex(rowIndex);
      }

      console.log('Captured search term:', searchTerm);

      // Reset the select
      $(this).val(null).trigger('change');

      // Reset form
      document.getElementById('addItemForm').reset();

      // Pre-fill the item name with the search term if available
      if (searchTerm) {
        $('#item_name').val(searchTerm);
      }

      // Set default states
      $('#item_tax_fields').show();
      $('#item_tax_pref').val('taxable');

      // Clear and reinitialize Select2
      $('#addItemModal select').each(function () {
        if ($(this).hasClass('select2-hidden-accessible')) {
          $(this).val(null).trigger('change');
        }
      });

      // Open the add item modal
      $('#addItemModal').modal('show');

      $('#addItemModal').one('shown.bs.modal', function () {
        initializeItemModalSelects();
        setTimeout(function () {
          $('#item_name').focus().select();
        }, 150);
      });
      return;
    }

    // Existing Item Selection Logic
    // prices from the item API are in company base currency; convert to document currency
    let priceBase = parseFloat(data.price) || 0;
    let oPriceBase = parseFloat(data.o_price) || priceBase;

    let fx = parseFloat($('#fx_rate_to_base').val()) || 1;
    let convertedPrice = (fx && fx !== 1) ? (priceBase / fx) : priceBase;

    // 1. Set description
    $row.find('.desc').val(data.description || '');

    // 2. Set hidden fields
    let gstIncludeValue = false;
    if (data.gstinclude === true || data.gstinclude === 'true' || data.gstinclude === 1 || data.gstinclude === '1') {
      gstIncludeValue = true;
    }
    $row.find('.gstinclude').val(gstIncludeValue);

    // 3. Set price and quantity
    $row.find('.price').val(convertedPrice.toFixed(4));
    $row.find('.o_price').val(oPriceBase.toFixed(4));
    $row.find('.qty').val(1);

    // 4. Store tax_pref as data attribute on the row
    $row.data('tax-pref', data.tax_pref || '');

    // 5. Handle tax select based on tax preference
    let $taxSelect = $row.find('.tax-select');
    $taxSelect.empty();

    if (data.tax_pref === 'non_taxable') {
      let nonTaxOption = new Option('Non-taxable', '', true, true);
      $(nonTaxOption).data('rate', 0);
      $taxSelect.append(nonTaxOption);
      $taxSelect.prop('disabled', true);
      $taxSelect.addClass('bg-light');
      $taxSelect.data('rate', 0);
      if ($taxSelect.hasClass('select2-hidden-accessible')) {
        $taxSelect.select2('destroy');
      }
    } else {
      $taxSelect.prop('disabled', false);
      $taxSelect.removeClass('bg-light');

      if (data.tax_id && data.tax_name) {
        let taxOption = new Option(data.tax_name, data.tax_id, true, true);
        $(taxOption).data('rate', data.tax_rate || 0);
        $(taxOption).attr('data-rate', data.tax_rate || 0);
        $taxSelect.append(taxOption);
        $taxSelect.data('rate', data.tax_rate || 0);
      } else {
        $taxSelect.data('rate', 0);
      }

      if (!$taxSelect.hasClass('select2-hidden-accessible')) {
        initTaxSelect($taxSelect);
      } else {
        $taxSelect.trigger('change');
      }
    }

    // 6. Set discount to 0
    $row.find('.item-discount').val(0);
    $row.find('.discount-type').val('flat');

    // 7. Update HSN if present
    if (data.hsn_code) {
      $row.find('.hsn-input').val(data.hsn_code);
      $row.find('.hsn-display').text(data.hsn_code);
    }

    // show company/base currency price in a visible column
    try { setBasePriceDisplay($row, priceBase); } catch (e) { }

    // keep original company-base price on the row for re-calculation when FX changes
    $row.data('price_base', priceBase);
    $row.data('o_price_base', oPriceBase);

    updateRowAmount($row);
    calculateTotals();
  });
}


// initItemSelect($('.item_select'));


function initTaxSelect($el) {
  $el.select2({
    placeholder: 'Select Tax',
    ajax: {
      url: '/purchase/get_tax/',
      dataType: 'json',
      delay: 250,
      processResults: function (data) {
        return {
          results: data.map(function (tax) {
            return { id: tax.id, text: tax.name, rate: tax.rate };
          })
        };
      }
    }
  });


}




initTaxSelect($('.tax-select'));


$('#items-table').on('select2:select', '.tax-select', function (e) {
  let data = e.params.data;
  $(this).find('option[value="' + data.id + '"]').data('rate', data.rate || 0);
  let $row = $(this).closest('tr');
  updateRowAmount($row);
  calculateTotals();
});


function updateRowAmount($row) {
  let qty = parseFloat($row.find('.qty').val()) || 1;
  let price = parseFloat($row.find('.price').val()) || 0;
  console.log("price" + price);

  let taxPref = $row.data('tax-pref') || '';


  // let baseAmount = qty * price;

  // Get tax rate - for non-taxable items, this will be 0
  let taxRate = 0;
  if (taxPref !== 'non_taxable' && taxPref !== 'non_taxable') {
    taxRate = parseFloat($row.find('.tax-select').data('rate')) || 0;
  }

  // let taxRate = parseFloat($row.find('.tax-select').data('rate')) || 0;

  let discount = parseFloat($row.find('.item-discount').val()) || 0;
  let discountType = $row.find('.discount-type').val(); // 'flat' or 'percent'
  let baseAmount = getDocumentTaxableLineAmount($row, qty, price, taxRate);
  let grossAmount = getDocumentGrossLineAmount($row, qty, price, baseAmount, taxRate);

  // // Apply discount based on type
  //   let discountedAmount;
  //   if (discountType === 'percent') {
  //       discountedAmount = baseAmount - (baseAmount * discount / 100);
  //   } else {
  //       discountedAmount = baseAmount - discount;
  //   }
  //   if (discountedAmount < 0) discountedAmount = 0;

  let discountedAmount;
  if (discountType === 'percent') {
    discountedAmount = baseAmount - (baseAmount * discount / 100);
  } else {
    // Flat discount applies to the full row amount, not each unit price
    discountedAmount = baseAmount - discount;
  }
  if (discountedAmount < 0) discountedAmount = 0;

  // let taxAmount = baseAmount * (taxRate / 100);
  let taxAmount = discountedAmount * (taxRate / 100);
  console.log("taxAmount" + taxAmount);

  let displayAmount = isGstIncludedRow($row)
    ? applyLineDiscount(grossAmount, discount, discountType)
    : discountedAmount;

  // let  finalAmount;
  // if(gstval == 'true')
  // {
  //      finalAmount = baseAmount;

  // }
  // else
  // {
  //  finalAmount = baseAmount + taxAmount;

  // }

  // // let finalAmount = baseAmount + taxAmount;
  // console.log("finalAmount"+finalAmount);


  // $row.find('.amount').text('₹' + finalAmount.toFixed(2));
  const symbol = getDocumentCurrencySymbol();
  $row.find('.amount').text(symbol + displayAmount.toFixed(2));


  // Save values for totals
  // Use individual setters to avoid overwriting price_base/o_price_base
  $row.data('baseAmount', discountedAmount);
  $row.data('taxAmount', taxAmount);
  $row.data('isNonTaxable', (taxPref === 'non_taxable' || taxPref === 'non_taxable'));
}

function applyLineDiscount(lineAmount, discount, discountType) {
  let discountedAmount;
  if (discountType === 'percent') {
    discountedAmount = lineAmount - (lineAmount * discount / 100);
  } else {
    discountedAmount = lineAmount - discount;
  }
  if (discountedAmount < 0) discountedAmount = 0;
  return discountedAmount;
}

function isGstIncludedValue(rawValue) {
  if (typeof rawValue === 'boolean') return rawValue;
  const normalized = String(rawValue || '').trim().toLowerCase();
  return normalized === 'true' || normalized === '1' || normalized === 'yes';
}

function isGstIncludedRow($row) {
  return isGstIncludedValue($row.find('.gstinclude').val());
}

function getDocumentTaxableUnitPrice($row, visiblePrice, taxRate) {
  if (!isGstIncludedRow($row)) return visiblePrice;

  const fxRate = parseFloat($('#fx_rate_to_base').val()) || 1;
  const oPriceBase = parseFloat($row.data('o_price_base'));
  if (Number.isFinite(oPriceBase) && oPriceBase > 0 && fxRate > 0) {
    return oPriceBase / fxRate;
  }

  const postedOPrice = parseFloat($row.find('.o_price').val());
  if (Number.isFinite(postedOPrice) && postedOPrice > 0 && fxRate > 0) {
    return postedOPrice / fxRate;
  }

  if (taxRate > 0) {
    return visiblePrice / (1 + (taxRate / 100));
  }
  return visiblePrice;
}

function getDocumentTaxableLineAmount($row, qty, visiblePrice, taxRate) {
  return qty * getDocumentTaxableUnitPrice($row, visiblePrice, taxRate);
}

function getDocumentGrossLineAmount($row, qty, visiblePrice, taxableLineAmount, taxRate) {
  if (isGstIncludedRow($row)) {
    const fxRate = parseFloat($('#fx_rate_to_base').val()) || 1;
    const priceBase = parseFloat($row.data('price_base'));
    if (Number.isFinite(priceBase) && priceBase > 0 && fxRate > 0) {
      return qty * (priceBase / fxRate);
    }
    return qty * visiblePrice;
  }
  return taxableLineAmount + (taxableLineAmount * (taxRate || 0) / 100);
}

function getStoredBaseLineAmount($row, qty, documentLineAmount) {
  const fxRate = parseFloat($('#fx_rate_to_base').val()) || 1;
  const priceBase = parseFloat($row.data('price_base'));
  const oPriceBase = parseFloat($row.data('o_price_base'));

  if (isGstIncludedRow($row) && Number.isFinite(oPriceBase) && oPriceBase > 0) {
    return qty * oPriceBase;
  }
  if (Number.isFinite(priceBase) && priceBase > 0) {
    return qty * priceBase;
  }
  if (Number.isFinite(oPriceBase) && oPriceBase > 0) {
    return qty * oPriceBase;
  }
  return documentLineAmount * fxRate;
}



function calculateTotals() {
  let subtotal = 0;
  // let allitmtotal = 0;
  let totalTax = 0;
  let totalDiscount = 0; // Track total item-level discount
  let baseSubtotal = 0;
  let baseTax = 0;
  let baseItemDiscount = 0;
  const fxRate = parseFloat($('#fx_rate_to_base').val()) || 1;


  document.querySelectorAll("#items-table tbody tr").forEach(function (row) {
    // Skip rows hidden or marked deleted added by neha on 23-12-25
    const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
    if ((deleteCheckbox && deleteCheckbox.checked) || row.style.display === 'none') {
      return; // Skip this row from calculations
    }
    let $row = $(row);
    let qty = parseFloat(row.querySelector(".qty").value) || 0;
    let price = parseFloat(row.querySelector(".price").value) || 0;
    let taxPref = $row.data('tax-pref') || '';
    let baseAmount = qty * price;
    let storedBaseAmount = getStoredBaseLineAmount($row, qty, baseAmount);
    console.log("baseAmount1" + baseAmount);

    // allitmtotal+=baseAmount;
    // console.log("allitmtotal1"+allitmtotal);


    // Item-level discount
    let discount = parseFloat($(row).find(".item-discount").val()) || 0;
    let discountType = $(row).find(".discount-type").val();

    // let discountedAmount;
    // if (discountType === 'percent') {
    //     discountedAmount = baseAmount - (baseAmount * discount / 100);
    // } else {
    //     discountedAmount = baseAmount - discount;
    // }
    // if (discountedAmount < 0) discountedAmount = 0;
    var taxRate = 0;
    if (taxPref !== 'non_taxable' && taxPref !== 'non_taxable') {
      let $taxSelect = $row.find(".tax-select");
      if ($taxSelect.length) {
        let selected = $taxSelect.find(":selected");
        if (selected.length) {
          taxRate = parseFloat($(selected).data("rate")) || 0;
        }
      }
    }
    baseAmount = getDocumentTaxableLineAmount($row, qty, price, taxRate);
    let grossAmount = getDocumentGrossLineAmount($row, qty, price, baseAmount, taxRate);
    storedBaseAmount = getStoredBaseLineAmount($row, qty, baseAmount);
    let discountedAmount = applyLineDiscount(baseAmount, discount, discountType);
    let displayAmount = isGstIncludedRow($row)
      ? applyLineDiscount(grossAmount, discount, discountType)
      : discountedAmount;
    let baseDiscountInput = discountType === 'percent' ? discount : (discount * fxRate);
    let baseDiscountedAmount = applyLineDiscount(storedBaseAmount, baseDiscountInput, discountType);

    totalDiscount += baseAmount - discountedAmount;
    baseItemDiscount += storedBaseAmount - baseDiscountedAmount;

    // ✅ NEW: Subtotal is sum of discounted amounts (before tax)
    subtotal += discountedAmount;
    baseSubtotal += baseDiscountedAmount;

    // tax-select handling
    // let $taxSelect = $(row).find(".tax-select");
    // let taxRate = 0;
    // Calculate tax
    taxRate = taxRate || 0;
    let taxAmount = 0;

    if (taxPref !== 'non_taxable' && taxPref !== 'non_taxable') {
      let $taxSelect = $row.find(".tax-select");
      if ($taxSelect.length) {
        let selected = $taxSelect.find(":selected");
        if (selected.length) {
          taxRate = parseFloat($(selected).data("rate")) || 0;
        }
      }
      taxAmount = (discountedAmount * taxRate) / 100;
      baseTax += (baseDiscountedAmount * taxRate) / 100;
    }

    console.log("discountedAmount1" + discountedAmount);
    // let taxAmount = (discountedAmount  * taxRate) / 100;

    console.log("taxAmount1" + taxAmount);
    totalTax += taxAmount;


    //   let  rowTotal;
    // if(gstval == 'true')
    // {
    //      rowTotal = discountedAmount;

    // }
    // else
    // {
    //  rowTotal = discountedAmount + taxAmount;

    // }
    // console.log("discountedAmount1"+discountedAmount);
    //   // let rowTotal = discountedAmount  + taxAmount;
    //   console.log("rowTotal"+rowTotal);

    // // update row amount cell
    // row.querySelector(".amount").innerText = "₹" + rowTotal.toFixed(2);

    // Update row amount cell - show only discounted amount (no tax)
    const rowSymbol = getDocumentCurrencySymbol();
    row.querySelector(".amount").innerText = rowSymbol + ' ' + displayAmount.toFixed(2);
    // subtotal += discountedAmount;
    // totalTax += taxAmount;
  });

  // let total = subtotal + totalTax;
  // console.log("allitmtotal"+allitmtotal);
  // document.getElementById("subtotal").innerText = "₹" + allitmtotal.toFixed(2);

  // ✅ NEW: Display subtotal (sum of discounted amounts, before tax)
  const symbol = getDocumentCurrencySymbol();
  document.getElementById("subtotal").innerText = symbol + ' ' + subtotal.toFixed(2);

  // // document.getElementById("subtotal").innerText = "₹" + subtotal.toFixed(2);
  // if (document.getElementById("tax-total")) {
  //   document.getElementById("tax-total").innerText = "₹" + totalTax.toFixed(2);
  // }
  // India: split GST into CGST/SGST. Other countries: show a single VAT total (no split).
  const vatEl = document.getElementById("tax-total-vat");
  if (vatEl) {
    vatEl.innerText = symbol + ' ' + (totalTax || 0).toFixed(2);
  } else {
    // Split total tax into CGST and SGST (even split for intra-state)
    var cgst = (totalTax / 2) || 0;
    var sgst = (totalTax / 2) || 0;
    if (document.getElementById("tax-total-cgst")) {
      document.getElementById("tax-total-cgst").innerText = symbol + ' ' + cgst.toFixed(2);
    }
    if (document.getElementById("tax-total-sgst")) {
      document.getElementById("tax-total-sgst").innerText = symbol + ' ' + sgst.toFixed(2);
    }
  }

  // $('#discount-amount').text(totalDiscount.toFixed(2));
  // ✅ NEW: Total before grand discount = subtotal + CGST + SGST
  let totalBeforeDiscount = subtotal + totalTax;


  // Apply Grand Discount
  let grandDiscount = parseFloat($('#grand-discount').val()) || 0;
  let grandDiscountType = $('#grand-discount-type').val();
  let grandDiscountValue = 0;

  if (grandDiscountType === 'percent') {
    grandDiscountValue = totalBeforeDiscount * (grandDiscount / 100);
    // grandDiscountValue = total * (grandDiscount / 100);
  } else {
    grandDiscountValue = grandDiscount;
  }
  if (grandDiscountValue > totalBeforeDiscount) grandDiscountValue = totalBeforeDiscount; // prevent negative

  // Display the grand discount value in the grandDiscountValue element
  $('#grandDiscountValue').text(symbol + ' ' + grandDiscountValue.toFixed(2));

  // if (grandDiscountValue > total) grandDiscountValue = total; // prevent negative
  // $('#discount-amount').text(discountValue.toFixed(2));
  // let grandTotal = total - grandDiscountValue;

  let grandTotal = totalBeforeDiscount - grandDiscountValue;
  let TotalDiscount = grandDiscountValue + totalDiscount;
  $('#discount-amount').text(symbol + ' ' + TotalDiscount.toFixed(2));

  syncTdsTcsDefinitionState();
  const tdsTcsType = document.querySelector('input[name="tds_tcs_type"]:checked')?.value || 'tds';
  const tdsTcsRate = parseFloat(document.getElementById('tds_tcs_rate')?.value) || 0;
  let tdsTcsAmount = 0;
  if (tdsTcsRate > 0) {
    tdsTcsAmount = grandTotal * tdsTcsRate / 100;
  }
  const tdsTcsSignedAmount = tdsTcsType === 'tds' ? -tdsTcsAmount : tdsTcsAmount;
  let finalGrandTotalWithTdsTcs = grandTotal + tdsTcsSignedAmount;
  if (finalGrandTotalWithTdsTcs < 0) finalGrandTotalWithTdsTcs = 0;

  if (document.getElementById('tds-tcs-amount')) {
    const sign = tdsTcsType === 'tds' ? '-' : '+';
    document.getElementById('tds-tcs-amount').innerText = symbol + ' ' + sign + tdsTcsAmount.toFixed(2);
  }
  if (document.getElementById('tds_tcs_amount')) {
    document.getElementById('tds_tcs_amount').value = tdsTcsAmount.toFixed(2);
  }
  document.getElementById('grand-total').innerText = symbol + ' ' + finalGrandTotalWithTdsTcs.toFixed(2);
  document.getElementById('grandTotal').value = finalGrandTotalWithTdsTcs.toFixed(2);

  // Multi-currency calculation for base summary
  const baseSymbol = getBaseCurrencySymbol();
  let baseTotalBeforeDiscount = baseSubtotal + baseTax;
  let baseGrandDiscountValue = 0;
  if (grandDiscountType === 'percent') {
    baseGrandDiscountValue = baseTotalBeforeDiscount * (grandDiscount / 100);
  } else {
    baseGrandDiscountValue = grandDiscount * fxRate;
  }
  if (baseGrandDiscountValue > baseTotalBeforeDiscount) baseGrandDiscountValue = baseTotalBeforeDiscount;
  const baseTotal = baseTotalBeforeDiscount - baseGrandDiscountValue;
  const baseTdsTcsAmount = tdsTcsRate > 0 ? (baseTotal * tdsTcsRate / 100) : 0;
  const baseTdsTcsSignedAmount = tdsTcsType === 'tds' ? -baseTdsTcsAmount : baseTdsTcsAmount;
  let baseGrandTotal = baseTotal + baseTdsTcsSignedAmount;
  if (baseGrandTotal < 0) baseGrandTotal = 0;
  const baseTotalDiscount = baseItemDiscount + baseGrandDiscountValue;

  const baseSubtotalEl = document.getElementById('base-subtotal');
  const baseCgstEl = document.getElementById('base-tax-cgst');
  const baseSgstEl = document.getElementById('base-tax-sgst');
  const baseVatEl = document.getElementById('base-tax-vat');
  const baseTotalDiscountEl = document.getElementById('base-total-discount');
  const baseTdsTcsAmountEl = document.getElementById('base-tds-tcs-amount');
  const baseTdsTcsLabelEl = document.getElementById('base-tds-tcs-label');
  const baseGrandTotalEl = document.getElementById('base-grand-total');

  const formatBase = (val) => baseSymbol + ' ' + (Number.isFinite(val) ? val : 0).toFixed(2);

  if (baseSubtotalEl) baseSubtotalEl.innerText = formatBase(baseSubtotal);
  if (baseCgstEl) baseCgstEl.innerText = formatBase(baseTax / 2);
  if (baseSgstEl) baseSgstEl.innerText = formatBase(baseTax / 2);
  if (baseVatEl) baseVatEl.innerText = formatBase(baseTax);
  if (baseTotalDiscountEl) baseTotalDiscountEl.innerText = formatBase(baseTotalDiscount);
  if (baseTdsTcsLabelEl) baseTdsTcsLabelEl.innerText = tdsTcsType === 'tds' ? 'TDS Amount' : 'TCS Amount';
  if (baseTdsTcsAmountEl) baseTdsTcsAmountEl.innerText = formatBase(baseTdsTcsAmount);
  if (baseGrandTotalEl) baseGrandTotalEl.innerText = formatBase(baseGrandTotal);

}


// --- On qty or price change ---
$('#items-table').on('input change', '.qty, .price, .item-discount, .discount-type', function () {
  let $row = $(this).closest('tr');

  // When user edits visible document-currency price, update stored base price and hidden input
  if ($(this).hasClass('price')) {
    const docPrice = parseFloat($row.find('.price').val()) || 0;
    const fx = parseFloat($('#fx_rate_to_base').val()) || 1;
    const priceBase = docPrice * fx;
    $row.data('price_base', priceBase);
    $row.data('o_price_base', priceBase);
    $row.find('.o_price').val(priceBase.toFixed(4));
    try { setBasePriceDisplay($row, priceBase); } catch (e) { }
  }

  updateRowAmount($row);
  calculateTotals();
});

$('#grand-discount, #grand-discount-type').on('input change', calculateTotals);

function syncTdsTcsDefinitionState() {
  const selectedType = document.querySelector('input[name="tds_tcs_type"]:checked')?.value || 'tds';
  const tdsSelect = document.getElementById('tds_definition_select');
  const tcsSelect = document.getElementById('tcs_definition_select');
  const tdsManage = document.getElementById('tds_manage_button');
  const tcsManage = document.getElementById('tcs_manage_button');
  const tdsAdd = document.getElementById('tds_add_button');
  const tcsAdd = document.getElementById('tcs_add_button');
  const hiddenRate = document.getElementById('tds_tcs_rate');
  const hiddenId = document.getElementById('tds_tcs_definition_id');

  if (tdsSelect) {
    tdsSelect.style.display = selectedType === 'tds' ? 'inline-block' : 'none';
  }
  if (tcsSelect) {
    tcsSelect.style.display = selectedType === 'tcs' ? 'inline-block' : 'none';
  }
  if (tdsManage) {
    tdsManage.style.display = selectedType === 'tds' ? 'inline-flex' : 'none';
  }
  if (tcsManage) {
    tcsManage.style.display = selectedType === 'tcs' ? 'inline-flex' : 'none';
  }
  if (tdsAdd) {
    tdsAdd.style.display = selectedType === 'tds' ? 'inline-flex' : 'none';
  }
  if (tcsAdd) {
    tcsAdd.style.display = selectedType === 'tcs' ? 'inline-flex' : 'none';
  }

  let selectedOption = null;
  let selectedValue = '';
  
  if (selectedType === 'tds' && tdsSelect) {
    selectedValue = tdsSelect.value;
    selectedOption = tdsSelect.options[tdsSelect.selectedIndex];
  } else if (selectedType === 'tcs' && tcsSelect) {
    selectedValue = tcsSelect.value;
    selectedOption = tcsSelect.options[tcsSelect.selectedIndex];
  }

  // ✅ FIXED: Properly extract rate and ID from selected option
  let rate = 0;
  let taxId = selectedValue || '';
  
  if (selectedOption && selectedOption.value) {
    // Try to get data-rate attribute first
    if (selectedOption.dataset && selectedOption.dataset.rate) {
      rate = parseFloat(selectedOption.dataset.rate) || 0;
    }
    // If we still don't have a rate, try to parse from text (fallback)
    if (rate === 0 && selectedOption.text) {
      const match = selectedOption.text.match(/\(([0-9.]+)%\)/);
      if (match && match[1]) {
        rate = parseFloat(match[1]) || 0;
      }
    }
  }

  // Debug logging
  console.debug('syncTdsTcsDefinitionState - Type:', selectedType, 'Value:', selectedValue, 'Rate:', rate, 'Option:', selectedOption);

  if (hiddenRate) {
    hiddenRate.value = Number.isFinite(rate) ? rate : 0;
  }
  if (hiddenId) {
    hiddenId.value = taxId;
  }
}

// ✅ FIXED: Expose function globally so inline scripts can call it
window.syncTdsTcsDefinitionState = syncTdsTcsDefinitionState;

$(document).on('change', 'input[name="tds_tcs_type"], #tds_definition_select, #tcs_definition_select', function () {
  syncTdsTcsDefinitionState();
  calculateTotals();
});

// ✅ FIXED: Add Select2 event listeners for TDS/TCS selects (Select2 doesn't trigger 'change' event)
$('#tds_definition_select').on('select2:select select2:clear', function () {
  syncTdsTcsDefinitionState();
  calculateTotals();
});

$('#tcs_definition_select').on('select2:select select2:clear', function () {
  syncTdsTcsDefinitionState();
  calculateTotals();
});

document.addEventListener('submit', function (e) {
  if (!e.target || e.target.tagName !== 'FORM') {
    return;
  }
  if (e.target.id === 'bill-form' || e.target.id === 'purchase-order-form' || e.target.closest('#bill-form') || e.target.closest('#purchase-order-form')) {
    try {
      syncTdsTcsDefinitionState();
    } catch (err) {
      console.warn('Failed to sync TDS/TCS before submit', err);
    }
  }
});

document.querySelectorAll('input[type="number"]').forEach(input => {
  input.addEventListener('focus', function () {
    this.select();
  });
});

document.addEventListener("DOMContentLoaded", function () {
  // ✅ FIXED: Initialize TDS/TCS state on page load (important for editing existing bills)
  try {
    syncTdsTcsDefinitionState();
    calculateTotals();
  } catch (err) {
    console.warn('Failed to initialize TDS/TCS state on page load', err);
  }

  // restoreFormData();


  const vendorSelect = document.getElementById('vendor_select');
  // const payTermsSelect = document.getElementById('pay-terms');
  const itemsTable = document.getElementById('items-table');
  // Scope the main save button to the purchase form so modal submit buttons are not affected
  const saveButton = (form && form.querySelector) ? form.querySelector('button[type="submit"].btn.btn-primary') : document.querySelector('button[type="submit"].btn.btn-primary');



  // function validateForm() { //commented by sree on 24-02-2026
  window.validateForm = function () {

    let isValid = true;

    // 1. vendor selected (not empty/null)
    if (!vendorSelect.value) {
      console.log("no vendor is selected");

      isValid = false;
    }

    // 2. Payment term selected
    // if (!payTermsSelect.value) {
    //         console.log("no pay term is selected");

    //   isValid = false;
    // }

    // 3. At least one item row with valid item selected
    const allRows = itemsTable.querySelectorAll('tbody tr');


    const rows = Array.from(allRows).filter(row => {
      const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
      const isDeleted = deleteCheckbox && deleteCheckbox.checked;
      const isHidden = row.style.display === 'none';
      return !isDeleted && !isHidden;
    });

    // const rows = itemsTable.querySelectorAll('tbody tr');
    if (rows.length === 0) {
      console.log("row length 0");
      isValid = false;
    } else {
      console.log("row length 1");

      // Check that each row has item selected
      for (const row of rows) {
        const itemSelect = row.querySelector('select.item_select');
        const qtyInput = row.querySelector('input.qty');
        const priceInput = row.querySelector('input.price');
        if (!qtyInput || !priceInput) {
          console.error('Quantity or Price input missing in row:', row);
          isValid = false;
          break;
        }

        // if (!itemSelect || !itemSelect.value || itemSelect.value === "") {
        //Check both native value and select2 value (for dynamically added options)
        const selectVal = itemSelect ? ($(itemSelect).val() || itemSelect.value) : '';
        if (!selectVal || selectVal === "") {

          console.log("no item is selected");

          isValid = false;
          break;
        }
        console.log("item is selected");

        // 4. Quantity and price minimum 1
        const qty = parseFloat(qtyInput.value);
        const price = parseFloat(priceInput.value);
        console.log("value of qty:", qty);
        console.log("value of price:", price);
        if (isNaN(qty) || isNaN(price)) {
          console.log('Quantity or Price value is not numeric:', qtyInput.value, priceInput.value);
          isValid = false;
          break;
        }

        if (isNaN(qty) || qty < 1 || isNaN(price) || price < 0) {
          console.log("value error in qty & price");

          isValid = false;
          break;
        }
      }
    }
    console.log("called validate form");

    console.log("value of isValid :" + isValid);
    saveButton.disabled = !isValid;
    if (!isValid) {
      saveButton.parentElement.title = "Fill the required fields"; // Title on wrapper div
    } else {
      saveButton.parentElement.title = "";
    }

  }

  // Attach event listeners to validate on changes
  // vendorSelect.addEventListener('change', validateForm);
  $('#vendor_select').on('select2:select select2:unselect', function () {
    validateForm();
    $('#vendor_select').on('change', validateForm);
  });

  // payTermsSelect.addEventListener('change', validateForm);
  //   $('#pay-terms').on('select2:select select2:unselect', function() {
  //   validateForm();
  // });


  // Delegate event listener for item select, qty, and price changes inside items table
  // itemsTable.addEventListener('change', function(e) {
  //   if (e.target.classList.contains('item_select') || e.target.classList.contains('qty') || e.target.classList.contains('price')) {
  //     validateForm();
  //   }
  // });
  $('#items-table').on('select2:select select2:unselect', '.item_select', function () {
    validateForm();
    $('#item_select').on('change', validateForm);

  });

  // itemsTable.addEventListener('input', function(e) {
  //   if (e.target.classList.contains('qty') || e.target.classList.contains('price')) {
  //     validateForm();
  //   }
  // });
  $('#items-table').on('input', '.qty, .price', function () {
    validateForm();
  });

  // Also check validation on page load in case of prefilled form
  validateForm();
});

// Clear Storage When Form Is Successfully Submitted
// form.addEventListener('submit', function() {
//     sessionStorage.removeItem('savedPurchaseForm');
// });



// const form = document.getElementById('purchase-form');

function saveFormData() {
  let data = {};

  // Save basic inputs/selects
  Array.from(form.elements).forEach(field => {
    if (field.name) {
      if ($(field).hasClass('select2-hidden-accessible')) {
        data[field.name] = $(field).val();
      } else {
        data[field.name] = field.value;
      }
    }
  });

  // Save item rows data
  const itemsData = [];
  $('#items-table tbody tr').each(function (index, tr) {
    const rowData = {};
    $(tr).find('input, select').each(function () {
      const name = this.name;
      if (name) {
        rowData[name] = $(this).val();
      }
    });
    itemsData.push(rowData);
  });
  data['itemsData'] = itemsData;

  // sessionStorage.setItem('savedPurchaseForm', JSON.stringify(data));
}
function restoreFormData() {
  // let saved = sessionStorage.getItem('savedPurchaseForm');
  if (!saved) return;

  let data = JSON.parse(saved);

  // Restore simple inputs and selects (including select2)
  Object.entries(data).forEach(([key, value]) => {
    if (key === 'itemsData') return; // skip items for now
    let field = form.elements.namedItem(key);
    if (field) {
      if ($(field).hasClass('select2-hidden-accessible')) {
        $(field).val(value).trigger('change');
      } else {
        field.value = value;
      }
    }
  });

  // Clear existing item rows
  $('#items-table tbody').empty();

  // Rebuild item rows
  if (data.itemsData && data.itemsData.length) {
    data.itemsData.forEach((rowData, idx) => {
      let symbol = getDocumentCurrencySymbol();
      let newRow = `
                <tr>
                    <td>
                      <select name="items[${idx}][id]" class="item_select"></select>
                      <div style="margin-top:6px;">
                        <a href="#" class="open-hsn-btn">HSN: <span class="hsn-display"></span> <small style="color:#3a7bd5;">Update</small></a>
                        <input type="hidden" name="items[${idx}][hsn_code]" class="hsn-input">
                      </div>
                    </td>
                    <td><input type="text" name="items[${idx}][description]" class="desc"></td>
                    <td><input type="number" name="items[${idx}][qty]" min="0" class="qty"></td>
                    <td><input type="number" name="items[${idx}][price]" min="0" step="0.0001" class="price"></td>
                    <td class="base-price">
                      <input type="text" class="form-control form-control-sm o_price_display" name="items[${idx}][o_price_display]" readonly>
                    </td>
                    <td style="display:none;"><input type="hidden" name="items[${idx}][gstinclude]" class="gstinclude"></td>

                    <td style="display:none;"><input type="hidden" name="items[${idx}][o_price]" min="0" step="0.0001" class="o_price"></td>
                    <td><select name="items[${idx}][tax]" class="tax-select"></select></td>
                    <td style="display:flex;gap:2px;" class="discount-item">
                        <input type="number" class="item-discount" name="items[${idx}][discount]" min="0" step="0.01">
                        <select class="discount-type rupee-sign" name="items[${idx}][discount_type]">
                            <option value="flat" class="amount">${symbol}</option>
                            <option value="percent">%</option>
                        </select>
                    </td>
                    <td class="amount">${symbol}0.00</td>
                    <td><button type="button" class="remove-item-btn">X</button></td>
                </tr>`;
      $('#items-table tbody').append(newRow);

      let $row = $('#items-table tbody tr').last();

      // Set row fields from saved data
      Object.entries(rowData).forEach(([fieldName, val]) => {
        let input = $row.find(`[name="${fieldName}"]`);
        if (input.length) {
          if (input.hasClass('select2-hidden-accessible')) {
            input.val(val).trigger('change');
          } else {
            input.val(val);
          }
        }
      });

      // Initialize select2 on dynamically added selects
      initItemSelect($row.find('select.item_select'));
      initTaxSelect($row.find('select.tax-select'));
    });
  }

  calculateTotals();
}


$(document).on('submit', '#vendorCreateForm', function (e) {
  e.preventDefault();
  var $form = $(this);
  // Construct company-prefixed URL to avoid posting to root /purchase/ endpoint
  var pathParts = window.location.pathname.split('/');
  var companyCode = pathParts[1] || '';
  var vendorUrl = '/' + companyCode + '/purchase/add_vendor/';

  $.ajax({
    method: 'POST',
    url: vendorUrl,
    data: $form.serialize(),
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    success: function (response) {
      if (response.success) {
        // close modal
        var modalEl = document.getElementById('vendorCreateModal');
        var modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();

        // add vendor to select2 and select it
        var newOption = new Option(response.name, response.id, true, true);
        $('#vendor_select').append(newOption).trigger('change');
      }
    },
    error: function (xhr) {
      var errors = xhr.responseJSON?.errors || {};
      var errorMsg = errors.name ? errors.name.join(', ') : 'Error creating vendor';
      $('#vendorCreateModal .modal-body').prepend(
        `<div class="alert alert-danger">${errorMsg}</div>`
      );
    }
  });
});

$(document).on('submit', '#purchasepersonCreateForm', function (e) {
  e.preventDefault();
  var $form = $(this);

  $.ajax({
    method: 'POST',
    url: '/purchase/add_purchaseperson/',  // matches the Django POST handler, see below
    data: $form.serialize(),
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    success: function (response) {
      if (response.success) {
        // close modal
        var modalEl = document.getElementById('purchasepersonCreateModal');
        var modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();

        // add vendor to select2 and select it
        var newOption = new Option(response.name, response.id, true, true);
        $('#purchase_person_select').append(newOption).trigger('change');
      }
    },
    error: function (xhr) {
      var errors = xhr.responseJSON?.errors || {};
      var errorMsg = errors.name ? errors.name.join(', ') : 'Error creating vendor';
      $('#purchasepersonCreateModal .modal-body').prepend(
        `<div class="alert alert-danger">${errorMsg}</div>`
      );
    }
  });
});


$(document).on('select2:open', () => {
  const searchField = $('.select2-container--open .select2-search__field');
  if (searchField.length) {
    searchField[0].focus();
  }
});



document.addEventListener("DOMContentLoaded", function () {
  // Initialize base currency price displays for existing rows
  const baseTxSum = document.getElementById('base-transaction-summary');
  const baseSymbol = baseTxSum?.dataset.baseSymbol || document.getElementById('document_currency')?.dataset.baseSymbol || '₹';
  updateFlatDiscountSymbols();

  document.querySelectorAll("#items-table tbody tr").forEach(function (row) {
    const $row = $(row);
    const oPriceInput = row.querySelector(".o_price");
    if (oPriceInput && oPriceInput.value) {
      const oPriceVal = parseFloat(oPriceInput.value) || 0;
      setBasePriceDisplay($row, oPriceVal);
    }
  });


  if (typeof calculateTotals === 'function') calculateTotals();

  const itemsTable = document.querySelector("#items-table");
  if (itemsTable) {
    itemsTable.addEventListener("change", function (e) {
      if (e.target.classList.contains("tax-select")) {
        let row = e.target.closest("tr");
        let selected = e.target.options[e.target.selectedIndex];
        let rate = selected ? parseFloat(selected.dataset.rate || 0) : 0;

        row.dataset.taxRate = rate;
        updateRowAmount(row);
        calculateTotals();
      }
    });





    // 2. Add Item Row
    $('#add-item-btn').on('click', function () {
      let idx = $('#items-table tbody tr').length;
      let symbol = getDocumentCurrencySymbol();
      let newRow = `
    <tr data-tax-pref="">
      <td>

        <select name="form-${idx}-product" class="item_select"></select>
        
        <div style="margin-top:6px;">
          <a href="#" class="open-hsn-btn">HSN: <span class="hsn-display"></span> <small style="color:#3a7bd5;">Update</small></a>
          <input type="hidden" name="form-${idx}-hsn_code" class="hsn-input">
        </div>
      </td>
      <td><input type="text" class="desc" name="form-${idx}-description"></td>
      <td><input type="number" class="qty" name="form-${idx}-quantity" value="1" min="0"></td>
      <td><input type="number" class="price" name="form-${idx}-price" min="0" step="0.0001" value="0"></td>
      <td class="base-price">
        <input type="text" class="form-control form-control-sm o_price_display" name="form-${idx}-o_price_display" value="" readonly>
      </td>
      <td style="display:none;"><input type="hidden" name="form-${idx}-gstinclude" class="gstinclude"></td>
      <td style="display:none;"><input type="hidden" name="form-${idx}-o_price" class="o_price"></td>

      <td><select class="tax-select" name="form-${idx}-prd_tax"></select></td>
      <td style="display:flex;gap:2px;" class="discount-item">
              <input type="number" class="item-discount" name="form-${idx}-prd_disvalue" value="0" min="0" step="0.01">

        <select class="discount-type rupee-sign" name="form-${idx}-prd_distype">
          <option value="flat" class="rupee-sign">${symbol}</option>
          <option value="percent">%</option>
        </select>
      </td>

     

      <td class="amount">${symbol} 0.00</td>
      <td><button type="button" class="remove-item-btn">X</button></td>
    </tr>`;
      $('#items-table tbody').append(newRow);
      initItemSelect($('#items-table tbody tr:last .item_select'));
      initTaxSelect($('#items-table tbody tr:last .tax-select'));
      updateFlatDiscountSymbols();
      calculateTotals();
      // Also update management form's TOTAL_FORMS value after adding a new row
      let totalForms = $('#id_form-TOTAL_FORMS');
      if (totalForms.length) {
        let currentCount = parseInt(totalForms.val(), 10);
        totalForms.val(currentCount + 1);
      }
    });

    // 3. Remove Item Row
    itemsTable.addEventListener("click", function (e) {
      if (e.target.classList.contains("remove-item-btn")) {
        const formRow = e.target.closest("tr");
        const deleteCheckbox = formRow.querySelector('input[type="checkbox"][name$="-DELETE"]');

        if (deleteCheckbox) {
          // Existing DB-backed row: mark for deletion and disable inputs
          deleteCheckbox.checked = true;
          formRow.querySelectorAll('input, select, textarea, button').forEach(function (el) {
            try {
              if (el === deleteCheckbox) return; // keep DELETE enabled
              el.disabled = true;
            } catch (err) { /* ignore */ }
          });
          formRow.style.display = 'none';
        } else {
          // Newly added row: remove from DOM and decrement TOTAL_FORMS if present
          formRow.remove();
          let totalForms = document.querySelector('#id_form-TOTAL_FORMS');
          if (totalForms) {
            let currentCount = parseInt(totalForms.value || '0', 10);
            totalForms.value = String(Math.max(0, currentCount - 1));
          }
        }

        calculateTotals();
        validateForm();
      }
    });

    // 4. Calculate Totals
    if (itemsTable) {
      itemsTable.addEventListener("input", calculateTotals);
    }

  }


  calculateTotals();

});

$(document).ready(function () {
  console.log("initItemSelect is called");

  $('.item_select').select2({
    // your select2 options here, e.g. placeholder, ajax data source, etc.
    placeholder: 'Select an item',
    allowClear: true

  });
  initItemSelect($('select.item_select')); // note the underscore consistent with your form widget

  // Initialize Select2 for all existing tax selects
  initTaxSelect($('select.tax-select'));
  const urlParams = new URLSearchParams(window.location.search);
  const newVendorId = urlParams.get('vendor_id');
  const newVendorName = urlParams.get('vendor_name');


  const newItemId = urlParams.get('item_id');
  const newItemName = urlParams.get('item_name');

  if (newVendorId && newVendorName) {
    var newOption = new Option(newVendorName, newVendorId, true, true);
    $('#vendor_select').append(newOption).trigger('change');
    console.log("trigerred vendor_select in html");


    // Remove query params so page refresh doesn’t repeat
    window.history.replaceState({}, document.title, window.location.pathname);
  }
  else if (newItemId && newItemName) {
    var newOption = new Option(newItemName, newItemId, true, true);
    $('.item_select').append(newOption).trigger('change');
    console.log("trigerred item_select in html");


    // Remove query params so page refresh doesn’t repeat
    window.history.replaceState({}, document.title, window.location.pathname);
  }
});


$(document).ready(function () {
  $('.items-table').on('select2:select', '.item_select', function (e) {
    if (!e.params || !e.params.data) return;

    let data = e.params.data;
    let $row = $(this).closest('tr');

    if (data.isNew) {
      // alert("Open item creation modal here!");
      $(this).val(null).trigger('change');
      return;
    }
    console.log(parseFloat(data.price) || 0);
    console.log("o_pricelt:" + parseFloat(data.o_price) || 0);

    // let newtaxRate = parseFloat(data.tax_rate) || 0;


    $row.find('.desc').val(data.description || '');
    $row.find('.gstinclude').val(data.gstinclude);
    // $row.find('.o_price').val(parseFloat(data.o_price)) || 0;
    console.log("o_price from data:", data.o_price);
    // $row.find('.o_price').val(data.o_price !== undefined ? parseFloat(data.o_price) : 0);

    // // $row.find('.o_price').val(parseFloat(data.o_price) || 0);
    // console.log("Set o_price to:", $row.find('.o_price').val());


    const $oPriceInput = $row.find('.o_price');

    if ($oPriceInput.length) {
      let priceBase2 = parseFloat(data.price) || 0;
      let oPriceBase2 = parseFloat(data.o_price) || priceBase2;
      let fx2 = parseFloat($('#fx_rate_to_base').val()) || 1;
      let convertedP = (fx2 && fx2 !== 1) ? (priceBase2 / fx2) : priceBase2;

      $oPriceInput.val(oPriceBase2.toFixed(4));
      console.log("Set o_price to:", $oPriceInput.val());
      $row.find('.price').val(convertedP.toFixed(4));
      $row.data('price_base', priceBase2);
      $row.data('o_price_base', oPriceBase2);
      try { setBasePriceDisplay($row, priceBase2); } catch (e) { }
    } else {
      console.warn("No .o_price input found in this row", $row.html());
      let priceBase = parseFloat(data.price) || 0;
      let fx = parseFloat($('#fx_rate_to_base').val()) || 1;
      let convertedP = (fx && fx !== 1) ? (priceBase / fx) : priceBase;
      $row.find('.price').val(convertedP.toFixed(4));
    }

    $row.find('.qty').val(1);
    // Store tax_pref as data attribute on the row
    $row.data('tax-pref', data.tax_pref || '');

    // Handle tax select based on tax preference
    let $taxSelect = $row.find('.tax-select');
    $taxSelect.empty();
    console.log("tax preference is:" + data.tax_pref);
    if (data.tax_pref === 'non_taxable' || data.tax_pref === 'non_taxable') {
      // For non-taxable items: disable tax select and show "Non-Taxable"
      let nonTaxOption = new Option('Non-taxable', '', true, true);
      $taxSelect.append(nonTaxOption);
      $taxSelect.prop('disabled', true);
      $taxSelect.addClass('bg-light');
      $taxSelect.data('rate', 0);

      // Also disable select2 if initialized
      if ($taxSelect.hasClass('select2-hidden-accessible')) {
        $taxSelect.select2('destroy');
      }
    } else {
      // For taxable items: enable and populate tax
      $taxSelect.prop('disabled', false);
      $taxSelect.removeClass('bg-light');

      if (data.tax_id) {
        let newOption = new Option(data.tax_name, data.tax_id, true, true);
        $(newOption).data('rate', data.tax_rate || 0);
        $taxSelect.append(newOption).trigger('change');
      } else {
        $taxSelect.data('rate', 0);
      }

      // Re-initialize select2 if needed
      if (!$taxSelect.hasClass('select2-hidden-accessible')) {
        initTaxSelect($taxSelect);
      }
    }


    // Open HSN modal and prefill with any existing hsn or the item's default
    const $currentRow = $row;


    // Store a reference to the row on the modal so save can write back
    $('#hsnModal').data('targetRow', $currentRow);
    // If the selected item has an id like '123' or '123_45', extract main id
    let itemVal = $(this).val() || '';
    let itemId = (itemVal.indexOf('_') !== -1) ? itemVal.split('_')[0] : itemVal;
    // Clear and open select2 inside modal
    $('#hsn_select').empty().trigger('change');
    // Try to fetch existing HSN for this item from server
    if (itemId) {
      $.get('/Items/get-item-hsn/', { item_id: itemId })
        .done(function (resp) {
          if (resp.hsn_id) {
            console.log("Fetched HSN from server:", resp.hsn_code);
            // create a display option using code - description (resp.hsn_text) and store code as value
            // const opt = new Option(resp.hsn_text, resp.hsn_code, true, true);
            // $('#hsn_select').append(opt).trigger('change');
            $currentRow.find('.hsn-input').val(resp.hsn_code);
            $currentRow.find('.hsn-display').text(resp.hsn_code);
          } else {
            // if the row already has an HSN value, prefill from hidden input
            const existing = $currentRow.find('.hsn-input').val() || '';
            if (existing) {
              // const opt = new Option(existing, existing, true, true);
              // $('#hsn_select').append(opt).trigger('change');
              $currentRow.find('.hsn-display').text(existing);
              const opt = new Option(existing, existing, true, true);
              $('#hsn_select').append(opt).trigger('change');
            } else {
              $currentRow.find('.hsn-display').text('');
            }
          }
          // var hsnModal = new bootstrap.Modal(document.getElementById('hsnModal'), { backdrop: true });
          // hsnModal.show();
        })
        .fail(function () {
          // Do NOT auto-open HSN modal on AJAX failure (permission denied or other error).
          // User should open HSN modal explicitly using the "HSN: Update" link.
          console.warn('Failed to fetch item HSN; skipping automatic HSN modal open.');
        });
    } else {
      // No item id — do not auto-open HSN modal here. Open only on explicit user action.
      console.info('No item id; skipping automatic HSN modal open.');
    }

    // // set tax if available
    // let $taxSelect = $row.find('.tax-select');
    // $taxSelect.empty();
    // if (data.tax_id) {
    //   // let newOption = new Option(data.tax_name, data.tax_id, true, true);
    //   // $taxSelect.append(newOption).trigger('change');
    //   // $taxSelect.data('rate', data.tax_rate || 0);
    //   let $taxSelect = $row.find('.tax-select');
    // // Create option with tax rate
    // let newOption = new Option(data.tax_name, data.tax_id, true, true);
    // $(newOption).data('rate', data.tax_rate || 0);   // ✅ attach tax rate
    // $taxSelect.append(newOption).trigger('change');
    // } else {
    //   $taxSelect.data('rate', 0);
    // }

    updateRowAmount($row);
    calculateTotals();
  });
});

//Barcode scanning of items 

function getCompanyPrefixedUrl(path) {
  var parts = window.location.pathname.split('/');
  var first = parts[1] || '';
  var modules = ['sales', 'purchase', 'inventory', 'PayTerms', 'Items', 'customer', 'vendor', 'user', 'crm', 'hr', 'masters'];
  var prefix = modules.includes(first.toLowerCase()) ? '' : '/' + first;
  return prefix + path;
}

function normalizeSalesItemForSelect(rawItem) {
  var barcodeId = rawItem.b_id || '';
  return {
    id: String(rawItem.id) + '_' + barcodeId,
    text: rawItem.name + (rawItem.unit ? ' ' + rawItem.unit : ''),
    description: rawItem.sell_desc,
    price: rawItem.sl_price,
    gstinclude: rawItem.gstinclude,
    o_price: rawItem.o_price,
    uom: rawItem.unit,
    tax_id: rawItem.tax_id,
    tax_name: rawItem.tax_name,
    tax_rate: rawItem.tax_rate,
    tax_pref: rawItem.tax_pref,
    barcode: rawItem.barcode,
    b_id: barcodeId
  };
}

function setBarcodeStatus(message, type) {
  var status = document.getElementById('invoice-barcode-status');
  if (!status) return;
  status.textContent = message || '';
  status.style.color = type === 'error' ? '#b42318' : '#198754';
}

function getActiveInvoiceRows() {
  return $('#items-table tbody tr').filter(function () {
    var deleteCheckbox = this.querySelector('input[type="checkbox"][name$="-DELETE"]');
    return this.style.display !== 'none' && !(deleteCheckbox && deleteCheckbox.checked);
  });
}

function findEmptyInvoiceRow() {
  return getActiveInvoiceRows().filter(function () {
    return !($(this).find('.item_select').val() || '').toString().trim();
  }).first();
}

function ensureInvoiceItemRow() {
  var $row = findEmptyInvoiceRow();
  if ($row.length) return $row;
  $('#add-item-btn').trigger('click');
  return $('#items-table tbody tr:last');
}

function incrementExistingScannedRow(selectValue) {
  var matched = null;
  getActiveInvoiceRows().each(function () {
    var $row = $(this);
    if (($row.find('.item_select').val() || '').toString() === selectValue) {
      matched = $row;
      return false;
    }
  });

  if (!matched) return false;

  var $qty = matched.find('.qty');
  var currentQty = parseFloat($qty.val()) || 0;
  $qty.val((currentQty + 1).toFixed(2).replace(/\.00$/, ''));
  updateRowAmount(matched);
  calculateTotals();
  return true;
}

function applyScannedItem(rawItem, scannedCode) {
  var item = normalizeSalesItemForSelect(rawItem);

  if (incrementExistingScannedRow(item.id)) {
    setBarcodeStatus('Added 1 more: ' + item.text, 'success');
    return;
  }

  var $row = ensureInvoiceItemRow();
  var $select = $row.find('.item_select');
  if (!$select.hasClass('select2-hidden-accessible')) {
    initItemSelect($select);
  }

  var option = new Option(item.text, item.id, true, true);
  $(option).data(item);
  $select.append(option).val(item.id).trigger('change');
  $select.trigger({
    type: 'select2:select',
    params: { data: item }
  });

  setBarcodeStatus('Added: ' + item.text, 'success');
}

function scanInvoiceBarcode() {
  var input = document.getElementById('invoice-barcode-scan');
  if (!input) return;
  var barcode = (input.value || '').trim();
  if (!barcode) {
    setBarcodeStatus('Scan a barcode first.', 'error');
    input.focus();
    return;
  }

  setBarcodeStatus('Searching...', 'success');
  $.ajax({
    url: getCompanyPrefixedUrl('/sales/get_item_sales/'),
    dataType: 'json',
    data: { q: barcode },
    success: function (items) {
      var exactMatch = (items || []).find(function (item) {
        return String(item.barcode || '').trim() === barcode;
      });
      if (!exactMatch) {
        setBarcodeStatus('No active sales item found for barcode ' + barcode + '.', 'error');
        input.select();
        return;
      }

      applyScannedItem(exactMatch, barcode);
      input.value = '';
      input.focus();
    },
    error: function () {
      setBarcodeStatus('Could not search barcode. Please try again.', 'error');
      input.select();
    }
  });
}

$(document).on('keydown', '#invoice-barcode-scan', function (e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    scanInvoiceBarcode();
  }
});

$(document).on('click', '#invoice-barcode-add', function () {
  scanInvoiceBarcode();
});

$(function () {
  var scanInput = document.getElementById('invoice-barcode-scan');
  if (scanInput) {
    setTimeout(function () { scanInput.focus(); }, 150);
  }
});
//

// Allow manual HSN update via the small link/button
$(document).on('click', '.open-hsn-btn', function (e) {
  e.preventDefault();
  const $row = $(this).closest('tr');
  // Prefill modal select2 with existing HSN (from hidden input)
  const existing = $row.find('.hsn-input').val() || '';
  $('#hsn_select').empty();
  if (existing) {
    const opt = new Option(existing, existing, true, true);
    $('#hsn_select').append(opt).trigger('change');
  }
  $('#hsnModal').data('targetRow', $row);
  // Allow this explicit user action to open the modal — set a short-lived flag
  try { window.__allowHsnModalShow = true; } catch (e) { window.__allowHsnModalShow = true; }
  var hsnModal = new bootstrap.Modal(document.getElementById('hsnModal'), { backdrop: true });
  hsnModal.show();
  // Reset the allow flag shortly after showing to prevent other code from opening it
  setTimeout(function () { try { window.__allowHsnModalShow = false; } catch (e) { } }, 500);
});

// Initialize HSN select2 on modal open (global init)
$(document).ready(function () {
  $('#hsn_select').select2({
    placeholder: 'Select HSN',
    allowClear: true,
    dropdownParent: $('#hsnModal'),  // Append dropdown inside modal
    ajax: {
      url: '/Items/hsn-codes/',
      dataType: 'json',
      delay: 250,
      data: function (params) { return { q: params.term }; },
      processResults: function (data) {
        return {
          results: data.map(function (h) {
            return { id: h.code, text: h.code + ' - ' + h.description };
          })
        };
      }
    }
  });

  // Save button in modal commits value to the row
  $('#hsn_save_btn').on('click', function () {
    const selection = $('#hsn_select').val() || '';
    const $targetRow = $('#hsnModal').data('targetRow');
    if ($targetRow && $targetRow.length) {
      $targetRow.find('.hsn-input').val(selection);
      $targetRow.find('.hsn-display').text(selection);
    }
    var modalEl = document.getElementById('hsnModal');
    var modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
  });
});

// Prevent automatic opening of the HSN modal unless explicitly allowed by the allow-flag.
try {
  window.__allowHsnModalShow = window.__allowHsnModalShow || false;
} catch (e) {
  window.__allowHsnModalShow = false;
}
$(document).on('show.bs.modal', '#hsnModal', function (e) {
  if (!window.__allowHsnModalShow) {
    e.preventDefault();
    console.log('Blocked automatic show of hsnModal');
  }
});

// Ensure modal does not show leftover errors when opened; reveal only after a submit attempt
$('#addvendorModal').on('show.bs.modal', function () {
  try {
    var $modal = $(this);
    var $mb = $modal.find('.modal-body');
    if (!$modal.data('vendorFormSubmitted')) {
      $mb.find('.text-danger.small, .text-danger, .invalid-feedback, .alert.alert-danger').hide();
      $mb.find('*').filter(function () { return $(this).text().trim() === 'This field is required.'; }).hide();
    }
  } catch (e) { /* ignore */ }
});


// document.addEventListener('DOMContentLoaded', function() {
//     const duplicateBtn = document.querySelector('[data-bs-target="#confirmDuplicateModal"]');
//     const modal = document.getElementById('confirmDuplicateModal');
//     const orderNumberEl = document.getElementById('orderNumber');
//     const hiddenOrderId = document.getElementById('hiddenOrderId');

//     duplicateBtn.addEventListener('click', function() {
//       console.log("duplicate button vlivked");
//         const orderId = this.getAttribute('data-order-id');
//         hiddenOrderId.value = orderId;
//         console.log("hiddenOrderId value:",hiddenOrderId);
//         orderNumberEl.textContent = 'PO-' + orderId;  // Format as needed
//     });
// });



$('#warehouse').select2({
  placeholder: '',
  allowClear: true,
  minimumInputLength: 0,
  ajax: {
    url: '/warehouse/warehouses_list/',
    dataType: 'json',
    // delay: 250,
    processResults: function (data) {
      let results = data.map(function (item) {
        return { id: item.id, text: item.name };
      });
      results.push({
        id: 'new',
        text: '+ New',
        isNew: true // custom flag to identify this special option
      });
      return { results: results };
    },
    cache: true
  },

});

$('#warehouse').on('select2:select', function (e) {
  var data = e.params.data;
  // if (data.isNew) {

  //   $('#paymentTermsModal').modal('show');

  //   $('#warehouse').val(null).trigger('change');
  // }
});

//added by neha on 29-1-26

let currentCustomerShippingData = null;
let currentBillingData = null;

function normalizeShippingData(raw) {
  const source = raw || {};
  return {
    name: source.name || source.attention || '',
    email: source.email || '',
    phone: source.phone || '',
    shipping_country: source.shipping_country || source.country || '',
    shipping_address_line_1: source.shipping_address_line_1 || source.address1 || '',
    shipping_address_line_2: source.shipping_address_line_2 || source.address2 || '',
    shipping_city: source.shipping_city || source.city || '',
    shipping_state: source.shipping_state || source.state || '',
    shipping_postal_code: source.shipping_postal_code || source.postal || '',
  };
}

function hasShippingDetails(raw) {
  const s = normalizeShippingData(raw);
  return [
    s.name,
    s.email,
    s.phone,
    s.shipping_country,
    s.shipping_address_line_1,
    s.shipping_address_line_2,
    s.shipping_city,
    s.shipping_state,
    s.shipping_postal_code,
  ].some(function (value) { return String(value || '').trim() !== ''; });
}

function buildShippingFromBilling(billing) {
  const b = billing || {};
  return normalizeShippingData({
    name: b.name || '',
    email: b.email || '',
    phone: b.phone || '',
    country: b.country || '',
    address1: b.address_line_1 || '',
    address2: b.address_line_2 || '',
    city: b.city || '',
    state: b.state || '',
    postal: b.postal_code || '',
  });
}


function populateShippingModal(shippingData) {
  if (!shippingData) return;

  const s = normalizeShippingData(shippingData);
  console.log('Populating shipping modal with:', s);

  function setSelectOrInputValue(field, value) {
    if (!field) return;
    const normalized = value || '';
    if (field.tagName === 'SELECT' && normalized && !Array.from(field.options).some(option => option.value === normalized)) {
      const option = document.createElement('option');
      option.value = normalized;
      option.textContent = normalized;
      field.appendChild(option);
    }
    field.value = normalized;
    if (normalized) field.setAttribute('data-current-value', normalized);
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
      window.jQuery(field).trigger('change');
    }
  }

  // Populate modal fields with vendor shipping data
  const saAttention = document.getElementById('sa_attention');
  const saEmail = document.getElementById('sa_email');
  const saPhone = document.getElementById('sa_phone');
  const saCountry = document.getElementById('sa_country');
  const saAddress1 = document.getElementById('sa_address1');
  const saAddress2 = document.getElementById('sa_address2');
  const saCity = document.getElementById('sa_city');
  const saState = document.getElementById('sa_state');
  const saPostal = document.getElementById('sa_postal');

  if (saAttention) saAttention.value = s.name || '';
  if (saEmail) saEmail.value = s.email || '';
  if (saPhone) saPhone.value = s.phone || '';
  setSelectOrInputValue(saCountry, s.shipping_country || '');
  if (saAddress1) saAddress1.value = s.shipping_address_line_1 || '';
  if (saAddress2) saAddress2.value = s.shipping_address_line_2 || '';
  setSelectOrInputValue(saCity, s.shipping_city || '');
  if (saPostal) saPostal.value = s.shipping_postal_code || '';

  // Set state value - need to wait for Select2 initialization
  if (saState && s.shipping_state) {
    // If Select2 is initialized
    if (window.jQuery && $(saState).hasClass('select2-hidden-accessible')) {
      setSelectOrInputValue(saState, s.shipping_state);
    } else {
      // Fallback for regular select
      setSelectOrInputValue(saState, s.shipping_state);
    }
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const shippingDisplay = document.getElementById('shipping-address');
  const saveBtn = document.getElementById('saveShippingBtn');
  const copyBtn = document.getElementById('copy-billing-btn');
  const modalEl = document.getElementById('shippingAddressModal');
  const bsModal = modalEl ? new bootstrap.Modal(modalEl) : null;

  function openModal() { if (bsModal) bsModal.show(); }

  // Shipping display is intentionally not clickable. Provide an Edit button to open modal.
  const editShippingBtn = document.getElementById('edit-shipping-btn');
  if (editShippingBtn) {
    editShippingBtn.addEventListener('click', function (e) {
      e.preventDefault();
      if (bsModal) {
        console.log("modal loaded");
        bsModal.show();
        // Initialize Select2 and populate with vendor data
        setTimeout(function () {
          initializeShippingStateDropdown();
          // Populate modal with vendor shipping data
          if (currentCustomerShippingData) {
            console.log("has current data");
            populateShippingModal(currentCustomerShippingData);
          } else {
            console.log("has no current data");
          }
        }, 100);
      }
    });
  }

  if (copyBtn) {
    copyBtn.addEventListener('click', function (e) {
      e.preventDefault();
      // copy billing fields into modal inputs
      const bname = document.getElementById('billing-name') ? document.getElementById('billing-name').innerText : '';
      const baddr = document.getElementById('billing-address') ? document.getElementById('billing-address').innerText : '';
      const bcontact = document.getElementById('billing-contact') ? document.getElementById('billing-contact').innerText : '';
      const bgst = document.getElementById('billing-gst') ? document.getElementById('billing-gst').innerText : '';

      // Parse contact field to extract email and phone
      // Format: "email | phone" or just "email" or just "phone"
      let email = '', phone = '';
      if (bcontact) {
        if (bcontact.includes('|')) {
          const parts = bcontact.split('|').map(p => p.trim());
          email = parts[0] || '';
          phone = parts[1] || '';
        } else if (bcontact.includes('@')) {
          // If no pipe but contains @, it's email
          email = bcontact;
        } else {
          // Otherwise assume it's phone
          phone = bcontact;
        }
      }

      // Fill modal inputs
      document.getElementById('sa_attention').value = bname || '';
      document.getElementById('sa_email').value = email || '';
      document.getElementById('sa_phone').value = phone || '';
      // try split address into lines roughly
      document.getElementById('sa_address1').value = baddr || '';
      document.getElementById('sa_address2').value = '';
      // attempt to extract city/postal from billing-address (best-effort)
      // leave city/state/postal blank for manual edit
      document.getElementById('sa_city').value = '';
      document.getElementById('sa_state').value = '';
      document.getElementById('sa_postal').value = '';
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', function (e) {
      // read modal fields
      const att = document.getElementById('sa_attention').value || '';
      const email = document.getElementById('sa_email').value || '';
      const phone = document.getElementById('sa_phone').value || '';
      const country = document.getElementById('sa_country').value || '';
      const a1 = document.getElementById('sa_address1').value || '';
      const a2 = document.getElementById('sa_address2').value || '';
      const city = document.getElementById('sa_city').value || '';
      const state = document.getElementById('sa_state').value || '';
      const postal = document.getElementById('sa_postal').value || '';

      let finalShipping = normalizeShippingData({
        name: att,
        email: email,
        phone: phone,
        shipping_country: country,
        shipping_address_line_1: a1,
        shipping_address_line_2: a2,
        shipping_city: city,
        shipping_state: state,
        shipping_postal_code: postal
      });
      if (!hasShippingDetails(finalShipping) && currentBillingData) {
        finalShipping = buildShippingFromBilling(currentBillingData);
      }

      // update display text
      const shipEl = document.getElementById('shipping-address');
      const shipContactEl = document.getElementById('shipping-contact');
      if (shipEl) {
        const nameEl = document.getElementById('shipping-name');
        let disp = finalShipping.name || '';
        nameEl.innerText = disp;
        let lines = [];
        if (finalShipping.shipping_address_line_1) lines.push(finalShipping.shipping_address_line_1);
        if (finalShipping.shipping_address_line_2) lines.push(finalShipping.shipping_address_line_2);
        let loc = '';
        if (finalShipping.shipping_city) loc += finalShipping.shipping_city;
        if (finalShipping.shipping_state) loc += (loc ? ', ' : '') + finalShipping.shipping_state;
        if (finalShipping.shipping_postal_code) loc += (loc ? ', ' : '') + finalShipping.shipping_postal_code;
        if (finalShipping.shipping_country) loc += (loc ? ', ' : '') + finalShipping.shipping_country;
        if (loc) lines.push(loc);
        shipEl.innerText = lines.join('\n');
      }
      if (shipContactEl) {
        shipContactEl.innerText = (finalShipping.email ? finalShipping.email + (finalShipping.phone ? ' | ' + finalShipping.phone : '') : (finalShipping.phone || ''));
      }

      // set hidden inputs
      try {
        document.getElementById('shipping_attention').value = finalShipping.name || '';
        document.getElementById('shipping_email').value = finalShipping.email || '';
        document.getElementById('shipping_phone').value = finalShipping.phone || '';
        document.getElementById('shipping_country').value = finalShipping.shipping_country || '';
        document.getElementById('shipping_address1').value = finalShipping.shipping_address_line_1 || '';
        document.getElementById('shipping_address2').value = finalShipping.shipping_address_line_2 || '';
        document.getElementById('shipping_city').value = finalShipping.shipping_city || '';
        document.getElementById('shipping_state').value = finalShipping.shipping_state || '';
        document.getElementById('shipping_postal_code').value = finalShipping.shipping_postal_code || '';
      } catch (err) { console.warn(err) }

      // If by adarshshipping state is provided, update Place of Supply to that state
      if (finalShipping.shipping_state) {
        const placeOfSupplyDiv = document.getElementById('place-of-supply');
        const hiddenPlaceField = document.getElementById('place_of_supply_hidden');
        if (placeOfSupplyDiv) {
          placeOfSupplyDiv.innerText = finalShipping.shipping_state;
        }
        if (hiddenPlaceField) {
          hiddenPlaceField.value = finalShipping.shipping_state;
        }
      }// If by adarsh

      currentCustomerShippingData = finalShipping;
      window.savedShippingData = {
        attention: finalShipping.name || '',
        email: finalShipping.email || '',
        phone: finalShipping.phone || '',
        country: finalShipping.shipping_country || '',
        address1: finalShipping.shipping_address_line_1 || '',
        address2: finalShipping.shipping_address_line_2 || '',
        city: finalShipping.shipping_city || '',
        state: finalShipping.shipping_state || '',
        postal: finalShipping.shipping_postal_code || ''
      };
      window.hasSavedShippingData = hasShippingDetails(currentCustomerShippingData);

      if (bsModal) bsModal.hide();
    });
  }
  // Initialize Select2 when modal is shown
  if (modalEl) {
    modalEl.addEventListener('shown.bs.modal', function () {
      initializeShippingStateDropdown();
      if (currentCustomerShippingData) {
        // Small delay to ensure Select2 is fully initialized
        setTimeout(function () {
          populateShippingModal(currentCustomerShippingData);
        }, 50);
      }
    });
  }
});

document.addEventListener('DOMContentLoaded', function () {
  console.log("domloaded!!!");
  function qs(selector) { return document.querySelector(selector); }
  const select = qs('#id_vendor') || qs('#vendor_select') || qs('select[name="vendor"]');
  const vendorInfo = qs('#vendor-info');
  const billingName = qs('#billing-name');
  const billingAddress = qs('#billing-address');
  const billingContact = qs('#billing-contact');
  const billingGst = qs('#billing-gst');
  // GST treatment element removed; do not set GST Treatment here
  const placeOfSupplyDiv = qs('#place-of-supply');

  function clearVendor() {
    if (!vendorInfo) return;
    vendorInfo.style.display = 'none';
    billingName.innerText = '';
    billingAddress.innerText = '';
    billingContact.innerText = '';
    billingGst.innerText = '';
    // clear any shipping info the user may have previously entered
    const shipNameEl = document.getElementById('shipping-name');
    const shipAddrEl = document.getElementById('shipping-address');
    if (shipNameEl) shipNameEl.innerText = '';
    if (shipAddrEl) shipAddrEl.innerText = 'New Address';
    // clear hidden shipping inputs so previous vendor's data doesn't persist
    ['shipping_attention', 'shipping_email', 'shipping_phone', 'shipping_country', 'shipping_address1', 'shipping_address2', 'shipping_city', 'shipping_state', 'shipping_postal_code'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    if (placeOfSupplyDiv) placeOfSupplyDiv.innerText = '';

    // Unlock currency if vendor is cleared
    if (typeof setDocumentCurrencyLocked === 'function') {
      setDocumentCurrencyLocked(false);
    }
    const docSel = document.getElementById('document_currency');
    if (docSel) {
      docSel.dataset.userSelected = '0';
      setDocumentCurrencyValue('', '', getBaseCurrencySymbol());
      refreshCurrencyUi();
    }
  }

  // Clear inputs inside the Shipping Address modal so previous vendor's values don't persist
  function clearShippingModal() {
    const ids = ['sa_attention', 'sa_email', 'sa_phone', 'sa_country', 'sa_address1', 'sa_address2', 'sa_city', 'sa_state', 'sa_postal'];
    ids.forEach(function (id) {
      const el = document.getElementById(id);
      if (el) {
        if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') el.value = '';
        else el.innerText = '';
      }
    });
  }



  // function fillVendor(data){ <!-- commented by sree on 24-02-26 -->
  window.fillVendor = function (data) {

    console.log('fillVendor 2 called with data:', data);
    if (!vendorInfo) return;
    if (!data || data.error) {
      clearVendor();
      currentCustomerShippingData = null;
      return;
    }
    vendorInfo.style.display = 'block';
    const hasSavedShipping = window.hasSavedShippingData;
    const savedShipping = normalizeShippingData(window.savedShippingData);
    const vendorShipping = normalizeShippingData(data.shipping);
    if (hasSavedShipping && hasShippingDetails(savedShipping)) {
      currentCustomerShippingData = savedShipping;
    } else if (hasShippingDetails(vendorShipping)) {
      currentCustomerShippingData = vendorShipping;
    } else {
      currentCustomerShippingData = buildShippingFromBilling(data.billing || {});
    }
    console.log('Stored shipping data:', currentCustomerShippingData);
    const b = data.billing || {};
    currentBillingData = b;
    billingName.innerText = b.name || '';
    let addr = '';
    if (b.address_line_1) addr += b.address_line_1 + ', ';
    if (b.address_line_2) addr += b.address_line_2 + ', ';
    if (b.city) addr += b.city + ', ';
    if (b.postal_code) addr += b.postal_code + ', ';
    if (b.country) addr += b.country;
    billingAddress.innerText = addr.replace(/, $/, '');
    billingContact.innerText = (b.email ? b.email + (b.phone ? ' | ' + b.phone : '') : (b.phone || ''));
    billingGst.innerText = (b.tax_number || b.gst_number) ? ('Tax Number: ' + (b.tax_number || b.gst_number)) : '';
    // Fill shipping info from vendor data
    const s = normalizeShippingData(currentCustomerShippingData);
    const shipNameEl = document.getElementById('shipping-name');
    const shipAddrEl = document.getElementById('shipping-address');
    const shipContactEl = document.getElementById('shipping-contact');

    if (shipNameEl) {
      shipNameEl.innerText = s.name || '';
    }

    if (shipAddrEl) {
      let shipLines = [];
      if (s.shipping_address_line_1) shipLines.push(s.shipping_address_line_1);
      if (s.shipping_address_line_2) shipLines.push(s.shipping_address_line_2);

      let loc = '';
      if (s.shipping_city) loc += s.shipping_city;
      if (s.shipping_state) loc += (loc ? ', ' : '') + s.shipping_state;
      if (s.shipping_postal_code) loc += (loc ? ', ' : '') + s.shipping_postal_code;
      if (s.shipping_country) loc += (loc ? ', ' : '') + s.shipping_country;
      if (loc) shipLines.push(loc);

      // If no shipping data, show "New Address"
      shipAddrEl.innerText = shipLines.length > 0 ? shipLines.join('\n') : 'New Address';
    }
    if (shipContactEl) {
      shipContactEl.innerText = (s.email ? s.email + (s.phone ? ' | ' + s.phone : '') : (s.phone || ''));
    }

    // Also populate hidden shipping inputs for form submission
    try {
      document.getElementById('shipping_attention').value = s.name || '';
      document.getElementById('shipping_email').value = s.email || '';
      document.getElementById('shipping_phone').value = s.phone || '';
      document.getElementById('shipping_country').value = s.shipping_country || '';
      document.getElementById('shipping_address1').value = s.shipping_address_line_1 || '';
      document.getElementById('shipping_address2').value = s.shipping_address_line_2 || '';
      document.getElementById('shipping_city').value = s.shipping_city || '';
      document.getElementById('shipping_state').value = s.shipping_state || '';
      document.getElementById('shipping_postal_code').value = s.shipping_postal_code || '';
    } catch (err) {
      console.warn('Error setting shipping hidden inputs:', err);
    }
    applyVendorPaymentTerms(data);

    // Update currency and exchange rate based on vendor's currency,
    // but preserve saved edit-page FX values on the initial load.
    const currentVendorId = (data && data.id !== undefined && data.id !== null) ? data.id.toString() : '';
    const shouldPreserveInitialFx =
      window.isExistingPurchaseOrderEdit &&
      window.initialPurchaseVendorId &&
      currentVendorId === window.initialPurchaseVendorId.toString();

    if (shouldPreserveInitialFx) {
      applyInitialPurchaseFxState();
      setTimeout(function () {
        try { refreshPricesFromBase(); } catch (e) { calculateTotals(); }
      }, 0);
    } else {
      const date = $('#id_date').val() || $('input[name="date"]').val();
      updateExchangeRate(data.id, null, date, { forceDocumentCurrency: true });
    }

    // GST treatment display removed; don't set gstTreatment here.
    if (placeOfSupplyDiv) {
      const savedPlaceField = document.querySelector('input[name="place_of_supply"]');
      const savedVal = savedPlaceField ? (savedPlaceField.value || '').trim() : '';
      const state = (savedVal || data.place_of_supply || '').toLowerCase();
      console.log('Place of Supply - saved:', savedVal, 'from data:', data.place_of_supply, 'final state:', state);

      // Find the properly cased state value from the states array
      const states = [
        'Andaman and Nicobar Islands', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar',
        'Chandigarh', 'Chhattisgarh', 'Dadra and Nagar Haveli', 'Daman and Diu', 'Delhi',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
        'Ladakh', 'Lakshadweep', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya',
        'Mizoram', 'Nagaland', 'Odisha', 'Puducherry', 'Punjab', 'Rajasthan', 'Sikkim',
        'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
      ];
      const properCasedState = states.find(s => s.toLowerCase() === state) || (savedVal || data.place_of_supply || '');
      placeOfSupplyDiv.innerText = properCasedState;

      // Also update hidden field
      const hiddenField = document.querySelector('input[name="place_of_supply"]');
      if (hiddenField && properCasedState) {
        hiddenField.value = properCasedState;
      }
    }
  }

  // Place of Supply is now auto-populated from vendor data

  // Place of Supply is now auto-populated from vendor data
  //added by neha on 4-2-26 
  window.loadVendorDetails = function (vendorId) {
    console.log("loading vendordetails");
    if (!vendorId) { clearVendor(); return; }
    const docSel = document.getElementById('document_currency');
    if (docSel) {
      docSel.dataset.userSelected = '0';
    }
    const companyPrefix = getCompanyPrefix();
    const detailUrl = companyPrefix
      ? `/${companyPrefix}/purchase/vendor/${vendorId}/detail/`
      : `/purchase/vendor/${vendorId}/detail/`;

    fetch(detailUrl, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(r => {
        if (!r.ok) {
          throw new Error(`Vendor detail request failed with status ${r.status}`);
        }
        return r.json();
      })
      .then(fillVendor)
      .catch(err => { console.error(err); clearVendor(); });
  }



  if (select) {
    select.addEventListener('change', function () {
      // Clear any shipping modal fields so they don't show previous vendor's data
      try { clearShippingModal(); } catch (err) { console.warn('clearShippingModal failed', err); }
      window.applyVendorDefaultPaymentTerms = true;
      loadVendorDetails(this.value);
    });

    // Also handle select2 selection event
    if (window.jQuery) {
      $(select).on('select2:select', function (e) {
        var id = $(this).val();
        window.applyVendorDefaultPaymentTerms = true;
        if (id) loadVendorDetails(id);
      });

      // When Select2 dropdown is closed without a selection, hide vendor info if no vendor selected
      $(select).on('select2:close', function (e) {
        try {
          if (!$(this).val() || $(this).val() === '') {
            clearVendor();
          }
        } catch (err) { console.warn('Error handling select2:close', err); }
      });
      // When an option is unselected (clear), hide vendor info immediately
      $(select).on('select2:unselect', function (e) {
        try { clearVendor(); } catch (err) { console.warn('Error handling select2:unselect', err); }

        //added by sree on 19-02-26 to clear preferred vendor items & validate form
        clearVendorPreferredItemRows();  // ← ADD THIS
        if (typeof validateForm === 'function') validateForm();

      });
    }
    // Load initial vendor if present
    const init = select.value;
    if (init) loadVendorDetails(init);

    // If a new vendor is created via the Add Customer modal, refresh details when modal closes
    try {
      const addCustomerModalEl = document.getElementById('addCustomerModal');
      if (addCustomerModalEl) {
        addCustomerModalEl.addEventListener('hidden.bs.modal', function () {
          try {
            // If a vendor is selected (newly created option might be selected by other code), reload details
            if (select && select.value) {
              // ensure shipping modal fields are cleared before reloading details
              try { clearShippingModal(); } catch (err) { }
              loadVendorDetails(select.value);
            }
            else { clearVendor(); }
          } catch (err) { console.warn('Error reloading vendor after modal close', err); }
        });
      }
    } catch (e) { /* ignore */ }
  }
});

// Show Add vendor Modal on +New click
document.addEventListener('DOMContentLoaded', function () {
  var addVendorBtn = document.getElementById('addVendorBtn');
  if (addVendorBtn) {
    addVendorBtn.addEventListener('click', function () {
      var modal = new bootstrap.Modal(document.getElementById('addVendorModal'));
      modal.show();
    });
  }
});

// vendor Contact Add/Remove (delegated for modal + page forms)
document.addEventListener('click', function (e) {
  // Add contact - modal variant id or page variant id
  if (e.target && (e.target.id === 'add-Vendor-contact' || e.target.id === 'add-contact')) {
    // prefer modal container if present
    let container = document.getElementById('vendor-contact-persons-container') || document.getElementById('contact-persons-container') || document.getElementById('vendor-contact-persons-container');
    if (!container) return;
    const row = document.createElement('div');
    row.className = 'row contact-row mb-2';
    row.innerHTML = `
      <div class="col-md-4">
        <input type="text" name="contact_name" class="form-control" placeholder="Name">
      </div>
      <div class="col-md-4">
        <input type="email" name="contact_email" class="form-control" placeholder="Email">
      </div>
      <div class="col-md-3">
        <input type="text" name="contact_phone" class="form-control" placeholder="Phone">
      </div>
      <div class="col-md-1">
        <button type="button" class="btn btn-danger remove-contact">Delete</button>
      </div>
    `;
    container.appendChild(row);
  }
  // Remove contact (works for modal and page)
  if (e.target && e.target.classList && e.target.classList.contains('remove-contact')) {
    const row = e.target.closest('.contact-row');
    if (row) row.remove();
  }
});



// Handle unit select "+New" option
$('#item_unit_select').on('select2:select', function (e) {
  var data = e.params.data;
  if (data.isNew) {
    // Open unit creation modal
    $('#addUnitForm')[0].reset();
    $('#addUnitModal .alert').remove();

    // IMPORTANT: Set higher z-index and ensure proper stacking
    var unitModal = new bootstrap.Modal(document.getElementById('addUnitModal'), {
      backdrop: 'static', // Prevent closing by clicking backdrop
      keyboard: true
    });

    // Adjust z-index before showing
    $('#addUnitModal').on('show.bs.modal', function () {
      // Get the item modal's z-index
      var itemModalZIndex = parseInt($('#addItemModal').css('z-index')) || 1050;

      // Set unit modal z-index higher
      $(this).css('z-index', itemModalZIndex + 10);

      // Also adjust the backdrop z-index
      setTimeout(function () {
        $('.modal-backdrop').not(':first').css('z-index', itemModalZIndex + 5);
      }, 0);
    });

    unitModal.show();

    // Focus on the name input after modal opens
    $('#addUnitModal').on('shown.bs.modal', function () {
      $('#unit_name').focus();
    });

    // Reset unit select
    $('#item_unit_select').val(null).trigger('change');
  }
});

// Save new unit
$('#saveUnitBtn').on('click', function () {
  var unitName = $('#unit_name').val().trim();
  // var unitSymbol = $('#unit_symbol').val().trim();

  if (!unitName) {
    // Show error in modal
    $('#addUnitModal .modal-body').prepend(
      '<div class="alert alert-danger">Please enter a unit name</div>'
    );
    $('#unit_name').focus();
    return;
  }

  // Disable save button to prevent double-click
  $(this).prop('disabled', true).text('Saving...');

  // Build company-prefixed URL for unit save
  var pathParts = window.location.pathname.split('/');
  var companyCode = pathParts[1] || '';
  var ajaxUrl = '/' + companyCode + '/sales/add_unit/';

  // Helper to read CSRF token from cookie
  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  // Save new unit via AJAX
  $.ajax({
    url: ajaxUrl,
    method: 'POST',
    data: {
      name: unitName,
      csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').first().val()
    },
    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') },
    success: function (response) {
      if (response.success) {
        // Close modal
        var modalEl = document.getElementById('addUnitModal');
        var modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();

        // Add the new unit to the select and select it
        var displayText = response.name;
        var newOption = new Option(displayText, response.id, true, true);
        $('#item_unit_select').append(newOption).trigger('change');

        // Show success message (optional)
        // alert('Unit created successfully!');
      } else {
        // Show error in modal
        $('#addUnitModal .alert').remove();
        $('#addUnitModal .modal-body').prepend(
          '<div class="alert alert-danger">' + (response.error || 'Failed to create unit') + '</div>'
        );
      }
    },
    error: function (xhr) {
      // Show error in modal
      $('#addUnitModal .alert').remove();
      var errorMsg = xhr.responseJSON?.error || 'Error creating unit. Please try again.';
      $('#addUnitModal .modal-body').prepend(
        '<div class="alert alert-danger">' + errorMsg + '</div>'
      );
    },
    complete: function () {
      // Re-enable save button
      $('#saveUnitBtn').prop('disabled', false).text('Save Unit');
    }
  });
});

// Clear errors when user starts typing
$('#unit_name').on('input', function () {
  $('#addUnitModal .alert').remove();
});

// Handle Enter key in form
$('#addUnitForm').on('submit', function (e) {
  e.preventDefault();
  $('#saveUnitBtn').click();
});


// Handle item select clear/unselect
$('#items-table').on('select2:clear select2:unselect', '.item_select', function (e) {
  let $row = $(this).closest('tr');

  // Clear all fields in the row
  $row.find('.desc').val('');
  $row.find('.qty').val(1);
  $row.find('.price').val(0);
  $row.find('.gstinclude').val('');
  $row.find('.o_price').val(0);
  $row.find('.item-discount').val(0);
  $row.find('.discount-type').val('flat');
  $row.find('.hsn-input').val('');
  $row.find('.hsn-display').text('');

  // Clear tax select
  let $taxSelect = $row.find('.tax-select');
  $taxSelect.val(null).trigger('change');

  // Clear row data
  $row.data('tax-pref', '');

  // Update calculations
  updateRowAmount($row);
  calculateTotals();
  validateForm();
});

// Handle tax select clear/unselect
$('#items-table').on('select2:clear select2:unselect', '.tax-select', function (e) {
  let $row = $(this).closest('tr');

  // Reset tax rate to 0
  $(this).data('rate', 0);

  // Update calculations
  updateRowAmount($row);
  calculateTotals();
});



// Clear validation errors when user types
$('#item_name, #item_selling_price').on('input', function () {
  $(this).removeClass('is-invalid');
  $(this).next('.invalid-feedback').remove();
});

// Clear validation errors when user selects from Select2
$('#item_unit_select, #item_intra_tax_select, #item_inter_tax_select').on('change', function () {
  $(this).next('.select2-container').removeClass('is-invalid');
  $(this).next('.select2-container').next('.invalid-feedback').remove();
});


$('#addItemModal').on('change', '#item_tax_pref', function () {
  if (this.value === 'taxable') {
    $('#item_tax_fields').show();
    // Make tax fields required
    $('#item_intra_tax_select').attr('required', true);
    $('#item_inter_tax_select').attr('required', true);
    // Show GST inclusive checkbox
    $('#item_gst_inclusive_row').show();
  } else {
    $('#item_tax_fields').hide();
    // Remove required attribute
    $('#item_intra_tax_select').attr('required', false);
    $('#item_inter_tax_select').attr('required', false);
    // Hide GST inclusive checkbox
    $('#item_gst_inclusive_row').hide();

    // Clear any validation errors
    $('#item_intra_tax_select, #item_inter_tax_select').each(function () {
      $(this).next('.select2-container').removeClass('is-invalid');
      $(this).next('.select2-container').next('.invalid-feedback').remove();
    });
  }
});

// Initialize proper state when modal opens
$('#addItemModal').on('show.bs.modal', function () {
  $('#item_tax_pref').val('taxable').trigger('change');
});



function loadVendorPreferredItems(vendorId) {
  if (!vendorId) return;

  $.getJSON('/purchase/vendor/' + vendorId + '/preferred-items/', function (items) {
    if (!items || items.length === 0) return;

    // Clear existing empty rows (rows with no item selected)
    $('#items-table tbody tr').each(function () {
      const $sel = $(this).find('.item_select');
      if (!$sel.val()) {
        $(this).remove();
      }
    });
    // ✅ FIX: Reset TOTAL_FORMS to match actual remaining rows before adding
    const $totalForms = $('#id_form-TOTAL_FORMS');
    if ($totalForms.length) {
      $totalForms.val($('#items-table tbody tr').length);
    }

    items.forEach(function (item, idx) {
      // Add a new row for each preferred item
      const currentCount = $('#items-table tbody tr').length;
      const rowIdx = currentCount;
      const symbol = getDocumentCurrencySymbol();
      const fx = parseFloat($('#fx_rate_to_base').val()) || 1;
      const basePrice = parseFloat(item.price) || 0;
      const baseOPrice = parseFloat(item.o_price) || basePrice;
      const documentPrice = (fx && fx !== 1) ? (basePrice / fx) : basePrice;

      const newRow = `
                <tr data-tax-pref="${item.tax_pref || ''}">
                    <td>
                        <select name="form-${rowIdx}-product" class="item_select"></select>
                        <input type="hidden" name="form-${rowIdx}-id" value="">

                        <div style="margin-top:6px;">
                            <a href="#" class="open-hsn-btn">HSN: <span class="hsn-display">${item.hsn_code || ''}</span> <small style="color:#3a7bd5;">Update</small></a>
                            <input type="hidden" name="form-${rowIdx}-hsn_code" class="hsn-input" value="${item.hsn_code || ''}">
                        </div>
                    </td>
<td><input type="text" class="desc" name="form-${rowIdx}-description" value="${item.description || ''}"></td>                    <td><input type="number" class="qty" name="form-${rowIdx}-quantity" value="1" min="0"></td>
                    <td><input type="number" class="price" name="form-${rowIdx}-price" min="0" step="0.0001" value="${documentPrice.toFixed(4)}"></td>
                    <td style="display:none;"><input type="hidden" name="form-${rowIdx}-gstinclude" class="gstinclude" value="${item.gstinclude}"></td>
                    <td style="display:none;"><input type="hidden" name="form-${rowIdx}-o_price" class="o_price" value="${baseOPrice.toFixed(4)}"></td>
                    <td><select class="tax-select" name="form-${rowIdx}-prd_tax"></select></td>
                    <td style="display:flex;gap:2px;" class="discount-item">
                        <input type="number" class="item-discount" name="form-${rowIdx}-prd_disvalue" value="0" min="0" step="0.01">
                        <select class="discount-type rupee-sign" name="form-${rowIdx}-prd_distype">
                            <option value="flat">${symbol}</option>
                            <option value="percent">%</option>
                        </select>
                    </td>
                    <td class="amount">${symbol}0.00</td>
                    <td><button type="button" class="remove-item-btn">X</button></td>
                </tr>`;

      const $row = $(newRow);
      $('#items-table tbody').append($row);

      // Initialize item select2 and pre-select the item
      const $itemSelect = $row.find('.item_select');
      initItemSelect($itemSelect);

      const option = new Option(
        item.name + ' ' + item.unit,
        item.id + '_',
        true, true
      );
      $itemSelect.append(option).trigger('change');
      $row.data('price_base', basePrice);
      $row.data('o_price_base', baseOPrice);
      try { setBasePriceDisplay($row, basePrice); } catch (e) { }
      $row.data('tax-pref', item.tax_pref || '');

      // Set up tax select
      const $taxSelect = $row.find('.tax-select');
      if (item.tax_pref === 'non_taxable') {
        const nonTaxOpt = new Option('Non-taxable', '', true, true);
        $taxSelect.append(nonTaxOpt);
        $taxSelect.prop('disabled', true).addClass('bg-light').data('rate', 0);
      } else {
        if (item.tax_id) {
          const taxOpt = new Option(item.tax_name, item.tax_id, true, true);
          $(taxOpt).data('rate', item.tax_rate).attr('data-rate', item.tax_rate);
          $taxSelect.append(taxOpt).data('rate', item.tax_rate);
        }
        initTaxSelect($taxSelect);
      }

      // ✅ FIX: Increment TOTAL_FORMS after each row is added
      if ($totalForms.length) {
        $totalForms.val(parseInt($totalForms.val(), 10) + 1);
      }
      updateRowAmount($row);
    });

    calculateTotals();

    //FIX: Re-run validation after items are loaded so save button enables
    setTimeout(function () {
      if (typeof validateForm === 'function') {
        validateForm();
      }
    }, 200);
  }).fail(function (err) {
    console.warn('Could not load preferred items for vendor:', err);
  });
}

function clearVendorPreferredItemRows() {
  // Remove all rows from the items table body
  $('#items-table tbody tr').each(function () {
    const $row = $(this);

    // Destroy select2 instances to avoid memory leaks
    $row.find('.item_select, .tax-select').each(function () {
      if ($(this).hasClass('select2-hidden-accessible')) {
        try { $(this).select2('destroy'); } catch (e) { }
      }
    });

    $row.remove();
  });

  // Reset TOTAL_FORMS to 0
  const $totalForms = $('#id_form-TOTAL_FORMS');
  if ($totalForms.length) {
    $totalForms.val(0);
  }

  // Add back one blank row so the table isn't empty
  $('#add-item-btn').trigger('click');

  // Recalculate totals
  calculateTotals();
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}


function autoGenerateVendorCode(name) {

  if (!name || name.trim().length === 0) return;
  const csrf = $('[name=csrfmiddlewaretoken]').first().val();
  console.log('CSRF token found:', csrf);         // ← is it undefined?
  console.log('Name being sent:', name.trim());   // ← is name correct?


  // Send AJAX request to save item (company-prefixed URL)
  var pathParts = window.location.pathname.split('/');
  var companyCode = pathParts[1] || '';
  var ajaxUrl = '/' + companyCode + '/purchase/generate-vendor-code/';


  // AJAX call
  fetch(ajaxUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    body: `name=${encodeURIComponent(name.trim())}`
  })
    .then(response => response.json())
    .then(data => {

      if (data.success && data.code) {
        $('#addVendorModal').find('input[name="vendor_code"]').val(data.code);
        console.log('Auto-generated vendor code:', data.code);
      }
      else {
        $('#addVendorModal').find('input[name="vendor_code"]').val('');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      $('#addVendorModal').find('input[name="vendor_code"]').val('');
    });
}
// Regenerate vendor code on button click (if you have a refresh/generate button next to the field)
$(document).on('click', '#addVendorModal .generate-vendor-code-btn', function (e) {
  e.preventDefault();
  autoGenerateVendorCode();
});


// Regenerate vendor code when company_name or first_name changes inside the vendor modal
$(document).on('input', '#addVendorModal input[name="company_name"]', function () {
  var name = $(this).val().trim();
  if (name.length >= 1) {
    autoGenerateVendorCode(name);
  }
});


$(document).on('input', '#addVendorModal input[name="first_name"]', function () {
  var name = $(this).val().trim();
  if (name.length >= 1) {
    autoGenerateVendorCode(name);
  }
});

$(document).on('input', '#addVendorModal input[name="first_name"]', function () {
  // Only use first_name if company_name is empty
  var companyName = $('#addVendorModal input[name="company_name"]').val().trim();
  if (!companyName) {
    var name = $(this).val().trim();
    if (name.length >= 1) {
      autoGenerateVendorCode(name);
    }
  }
});


// Initialize base price data and refresh prices on load
$(document).ready(function () {
  setTimeout(function () {
    seedBasePriceData();
    refreshPricesFromBase();
  }, 1000);
});

