// sales_quotaion.js
// author sreevidya
console.log("purchase.js loaded ✅");



const form = document.getElementById('purchase-form');
let lastCustomerSearchTerm = '';
let lastsalepersonSearchTerm = '';


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
  return (
    (docSel.dataset && docSel.dataset.baseSymbol) ||
    docSel.getAttribute('data-base-symbol') ||
    DEFAULT_CURRENCY_SYMBOL
  );
}

// Returns the company/base currency symbol (from document_currency data-base-symbol)
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
  const fxInput = document.getElementById('fx_rate_to_base');
  const fxRate = fxInput ? parseFloat(fxInput.value) : NaN;
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

function formatBaseCurrencyAmount(value) {
  const numeric = Number(value || 0);
  return getBaseCurrencySymbol() + ' ' + numeric.toFixed(2);
}

function setBasePriceDisplay($row, value) {
  if (!($row && $row.length)) return;
  const formatted = formatBaseCurrencyAmount(value);
  const $input = $row.find('.o_price_display');
  if ($input.length) {
    $input.val(formatted);
    return;
  }
  const $cell = $row.find('.base-price');
  if ($cell.length) {
    $cell.text(formatted);
  }
}

function parseBasePriceFromRow($row) {
  if (!($row && $row.length)) return 0;
  const $input = $row.find('.o_price_display');
  let text = $input.length ? $input.val() : $row.find('.base-price').text();
  if (!text) return 0;
  text = text.replace(/[^\d\-.]/g, '');
  return parseFloat(text) || 0;
}

function updateFlatDiscountSymbols() {
  const symbol = getDocumentCurrencySymbol();
  // Update any per-item discount selects
  document.querySelectorAll('.discount-type option[value="flat"]').forEach(function (opt) {
    opt.textContent = symbol;
  });
  // Also update any global or other discount selectors that use the rupee-sign class (eg. grand discount)
  document.querySelectorAll('select.rupee-sign').forEach(function (sel) {
    try {
      var opt = sel.querySelector('option[value="flat"]');
      if (opt) opt.textContent = symbol;
    } catch (e) { /* ignore */ }
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
    '}'
  ].join('\n');
  document.head.appendChild(style);
}

function getDocumentCurrencyHiddenInput() {
  const docSel = document.getElementById('document_currency');
  if (!docSel) return null;
  let hidden = document.getElementById('document_currency_hidden');
  if (!hidden) {
    hidden = document.createElement('input');
    hidden.type = 'hidden';
    hidden.id = 'document_currency_hidden';
    hidden.disabled = true;
    docSel.insertAdjacentElement('afterend', hidden);
  }
  return hidden;
}

function syncDocumentCurrencyMirror() {
  const docSel = document.getElementById('document_currency');
  const hidden = getDocumentCurrencyHiddenInput();
  if (!docSel || !hidden) return;
  const originalName = docSel.dataset.originalName || docSel.name || 'document_currency';
  hidden.value = docSel.value || '';
  hidden.name = originalName;
  hidden.disabled = !docSel.disabled;
}

function setDocumentCurrencyLocked(locked) {
  const docSel = document.getElementById('document_currency');
  if (!docSel) return;
  if (window.forceDocumentCurrencyLocked && !locked) {
    locked = true;
  }
  ensureDocumentCurrencyLockStyles();
  if (!docSel.dataset.originalName) {
    docSel.dataset.originalName = docSel.name || 'document_currency';
  }

  docSel.disabled = !!locked;
  docSel.dataset.lockedByCustomer = locked ? '1' : '0';
  docSel.setAttribute('aria-disabled', locked ? 'true' : 'false');
  docSel.classList.toggle('document-currency-locked', !!locked);
  syncDocumentCurrencyMirror();

  try {
    if (window.jQuery) {
      window.jQuery(docSel).prop('disabled', !!locked).trigger('change.select2');
    }
  } catch (e) {
    console.warn('document currency lock sync failed', e);
  }
}

function bindDocumentCurrencyChange() {
  const docSel = document.getElementById('document_currency');
  if (!docSel) return;
  // Use event delegation to guarantee it catches dynamically re-initialized select2 events
  $(document).off('change select2:select', '#document_currency').on('change select2:select', '#document_currency', function (event) {
    syncDocumentCurrencyMirror();
    if (window.isApplyingInitialInvoiceFx) return;
    if (window.isAutoFillingCurrency) return; // Prevent loop/false flags when auto-filling from customer change
    if (this.dataset.lockedByCustomer === '1') return;

    this.dataset.userSelected = '1';
    rebuildCurrencySymbolMap();
    updateFlatDiscountSymbols();
    updateBaseCurrencyVisibility();
    calculateTotals();

    // Dynamically fetch and update the exchange rate for the newly selected currency
    var cid = $(this).val();
    if (cid) {
      var pathParts = window.location.pathname.split('/');
      var companyCode = pathParts[1] || '';
      if (companyCode) {
        var apiUrl = '/' + companyCode + '/currencies/api/customer_rate/?currency_id=' + encodeURIComponent(cid);
        fetch(apiUrl, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
          .then(function (r) { return r.json(); })
          .then(function (resp) {
            if (!resp || !resp.ok) return;
            var fxIn = document.getElementById('fx_rate_to_base');
            var fxDate = document.getElementById('fx_rate_date');

            // Note: Since this is a manual override of the currency, 
            // auto-updating the exchange rate here makes the most sense.
            if (fxIn && resp.rate) {
              try {
                if (fxIn.value != resp.rate) fxIn.value = resp.rate;
                try { fxIn.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) { $(fxIn).trigger('input'); }
              } catch (e) { }
            }
            if (fxDate && (resp.rate_effective_from || resp.date)) {
              try { fxDate.value = resp.rate_effective_from || resp.date; } catch (e) { }
            }
          })
          .catch(function (err) { console.warn('currency rate fetch error', err); });
      }
    }
  });
}
let lastItemSearchTerm = '';

function applyInitialInvoiceFxState() {
  const docSel = document.getElementById('document_currency');
  const fxIn = document.getElementById('fx_rate_to_base');
  const fxDate = document.getElementById('fx_rate_date');

  window.isApplyingInitialInvoiceFx = true;
  try {
    if (docSel && window.initialInvoiceCurrencyId) {
      try {
        docSel.value = window.initialInvoiceCurrencyId;
        docSel.dataset.userSelected = '1';
        if (window.jQuery) {
          $(docSel).val(window.initialInvoiceCurrencyId).trigger('change.select2');
        }
        syncDocumentCurrencyMirror();
      } catch (e) {
        console.warn('failed to apply initial invoice currency', e);
      }
    }
    if (fxIn && window.initialInvoiceFxRate) {
      fxIn.value = window.initialInvoiceFxRate;
    }
    if (fxDate && window.initialInvoiceFxDate) {
      fxDate.value = window.initialInvoiceFxDate;
    }
  } finally {
    window.isApplyingInitialInvoiceFx = false;
  }

  if (fxIn && window.initialInvoiceFxRate) {
    try {
      fxIn.dispatchEvent(new Event('input', { bubbles: true }));
    } catch (e) {
      try { $(fxIn).trigger('input'); } catch (ignore) { }
    }
  }
}


// ============================================
// GLOBAL SCOPE - accessible everywhere
// ============================================
let _customerSelect = null;
let _itemsTable = null;
let _saveButton = null;

function validateForm() {
  console.log("=== validateForm called ===");
  console.log("_customerSelect:", _customerSelect);
  console.log("_itemsTable:", _itemsTable);
  console.log("_saveButton:", _saveButton);

  if (!_customerSelect || !_itemsTable || !_saveButton) {
    console.warn("EARLY RETURN - one of the refs is null!");
    return;
  }

  console.log("customer value:", _customerSelect.value);

  const allRows = _itemsTable.querySelectorAll('tbody tr');
  console.log("total rows in DOM:", allRows.length);

  const rowData = [];
    Array.from(allRows).forEach(row => {
    const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
    const isDeleted = deleteCheckbox && deleteCheckbox.checked;
    const isHidden = row.style.display === 'none';
    if (isDeleted || isHidden) {
      console.log("Skipping row (deleted/hidden) -> deleted:", isDeleted, "hidden:", isHidden);
      return;
    }

    // Prefer explicit select with class 'item_select', but fall back to any product input
    let itemSelect = row.querySelector('select.item_select');
    if (!itemSelect) {
      itemSelect = row.querySelector('select[name$="-product"], input[name$="-product"]');
    }

    const qtyInput = row.querySelector('input.qty');
    const priceInput = row.querySelector('input.price');

    if (!itemSelect || !qtyInput || !priceInput) {
      console.log("Skipping row because required inputs are missing:", { hasProduct: !!itemSelect, hasQty: !!qtyInput, hasPrice: !!priceInput });
      return;
    }

    rowData.push({ row, itemSelect, qtyInput, priceInput });
  });

  console.log("visible rows with required inputs:", rowData.length);

  let isValid = true;
  if (!_customerSelect.value) { isValid = false; console.log("FAIL: no customer"); }
  if (rowData.length === 0) {
    isValid = false;
    console.log("FAIL: no visible rows with item/qty/price");
  } else {
    for (const { itemSelect, qtyInput, priceInput } of rowData) {
      console.log("checking row - itemSelect value:", itemSelect.value, "qty:", qtyInput.value, "price:", priceInput.value);
      if (!itemSelect.value || itemSelect.value === "") {
        isValid = false;
        console.log("FAIL: no item selected");
        break;
      }
      const qty = parseFloat(String(qtyInput.value || '').replace(/[^0-9.\-]/g, ''));
      const price = parseFloat(String(priceInput.value || '').replace(/[^0-9.\-]/g, ''));
      if (isNaN(qty) || isNaN(price)) {
        isValid = false;
        console.log("FAIL: NaN qty/price");
        break;
      }
      // Allow decimal quantities less than 1, but reject zero or negative quantities
      if (qty <= 0 || price < 0) {
        isValid = false;
        console.log("FAIL: qty<=0 or price<0");
        break;
      }
    }
  }

  console.log("isValid:", isValid, "-> button disabled:", !isValid);
  _saveButton.disabled = !isValid;
  _saveButton.parentElement.title = !isValid ? "Fill the required fields" : "";
}


// Initialize shipping state dropdown with all Indian states
function initializeShippingStateDropdown() {
  const stateSelect = document.getElementById('sa_state');
  if (!stateSelect) {
    console.warn('sa_state element not found');
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
      console.warn('Error initializing Select2:', e);
    }
  }

  console.log('State dropdown initialized with', states.length, 'states');
}
$('#pay-terms').select2({
  placeholder: '',
  allowClear: true,
  minimumInputLength: 0,
  ajax: {
    url: (function() {
      var parts = window.location.pathname.split('/');
      var first = parts[1] || '';
      var modules = ['sales', 'purchase', 'inventory', 'PayTerms', 'Items', 'customer', 'vendor', 'user', 'crm', 'hr', 'masters'];
      var cp = modules.includes(first.toLowerCase()) ? '' : first;
      return (cp ? '/' + cp : '') + '/PayTerms/payterm_list/';
    })(),
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
$(document).on('click', '#paymentTermsModal .btn-primary', function (e) {//by adarsh
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

  $.ajax({
    // Construct company-prefixed URL for PayTerms save endpoint
    url: (function () {
      var parts = window.location.pathname.split('/');
      var company = parts[1] || '';
      return '/' + company + '/PayTerms/save_payterms/';
    })(),
    method: 'POST',
    contentType: 'application/json',
    data: JSON.stringify({ terms: terms, deleted: deletedTerms }),
    // include CSRF token for JSON POST
    headers: (function () {
      function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
          var cookies = document.cookie.split(';');
          for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
            }
          }
        }
        return cookieValue;
      }
      var headersObj = { 'X-Requested-With': 'XMLHttpRequest' };
      var csrftoken = getCookie('csrftoken');
      if (csrftoken) headersObj['X-CSRFToken'] = csrftoken;
      return headersObj;
    })(),
    success: function (response) {
      showToast("Payment terms saved successfully", "success");
      deletedTerms = [];

      // by adarshGet the newly created payment term ID and name from response
      let newTermId = response.last_created_id;
      let newTermName = response.last_created_name;

      // Close the modal
      var paymentModal = bootstrap.Modal.getInstance(document.getElementById('paymentTermsModal'));
      if (paymentModal) {
        paymentModal.hide();
      }

      // Select the newly created payment term in any active payment term select2 fields
      if (newTermId && newTermName) {
        setTimeout(function () {
          // Find all select fields for payment terms (by ID or name)
          var $pts = $('#pay-terms, [name="payment_terms"]');
          $pts.each(function() {
            var $el = $(this);
            var newOption = new Option(newTermName, newTermId, true, true);
            // Remove any existing option with same value to avoid duplicates
            $el.find('option[value="' + newTermId + '"]').remove();
            $el.append(newOption).trigger('change');
          });
        }, 100);
      }//byadarsh
    },
    error: function () {
      alert("Error saving payment terms");
    }
  });

});


// ✅ SIMPLIFIED: Let django-select2 handle initialization, just add event handlers
$(document).ready(function () {
  console.log("[SELECT2-SIMPLE] Script loaded, waiting for Select2 elements");

  // Give django-select2 a moment to initialize
  setTimeout(function () {
    console.log("Initializing customer_select and binding events...");
    
    // Helper to get company prefix robustly
    var getCompanyPrefix = function() {
      const pathParts = window.location.pathname.split('/');
      const firstPart = pathParts[1] || '';
      const modules = ['sales', 'purchase', 'inventory', 'PayTerms', 'Items', 'customer', 'vendor', 'user', 'crm', 'hr', 'masters'];
      if (modules.includes(firstPart.toLowerCase())) {
        return '';
      }
      return firstPart;
    };

    // Initialize Customer Select2 with AJAX and +New support
    $('#customer_select').select2({
      placeholder: 'Choose customer',
      allowClear: true,
      minimumInputLength: 1,
      ajax: {
        url: (function() {
          var cp = getCompanyPrefix();
          return (cp ? '/' + cp : '') + '/sales/customer/';
        })(),
        dataType: 'json',
        delay: 250,
        data: function(params) {
          window.lastCustomerSearchTerm = params.term || '';
          return { q: params.term };
        },
        processResults: function(data) {
          let results = data.map(function(item) {
            return { id: item.id, text: item.name };
          });
          results.push({ id: 'new', text: '+ New Customer', isNew: true });
          return { results: results };
        },
        cache: true
      }
    });

    $('#customer_select').on('select2:select', function (e) {
      console.log("Customer selection event fired. Data:", (e.params ? e.params.data : 'no params'));
      var data = (e && e.params && e.params.data) ? e.params.data : null;
      // Fallback: if no event data, try to derive from target value
      if (!data) {
        var v = (e && e.target && e.target.value) ? e.target.value : null;
        data = v ? { id: v } : null;
      }
      if (data && (data.id === 'new' || data.isNew)) {
        console.log("'+ New Customer' selected. Opening modal...");
        // Use lastCustomerSearchTerm captured in ajax.data while typing
        var typedName = (window.lastCustomerSearchTerm || '').trim();
        var companyPrefix = getCompanyPrefix();
        var customerFormUrl = (companyPrefix ? '/' + companyPrefix : '') + '/sales/customer_createform/';
        
        console.log("Fetching customer create form from:", customerFormUrl);
        $.get(customerFormUrl, { name: typedName }, function (formHtml) {
          console.log("Form HTML received successfully.");
          $('#addCustomerModal .modal-body').html(formHtml);

          // Initialize Select2 for form fields immediately after form is injected
          try {
            var $mb = $('#addCustomerModal .modal-body');
            if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
              $mb.find('.select2').each(function () {
                var $el = $(this);
                try { $el.select2('destroy'); } catch (e) { }
                
                // Special handling for payment_terms inside the modal
                if ($el.attr('name') === 'payment_terms') {
                  var companyPrefix = (function() {
                    var parts = window.location.pathname.split('/');
                    return parts[1] || '';
                  })();
                  $el.select2({
                    placeholder: 'Select Payment Terms',
                    allowClear: true,
                    width: '100%',
                    dropdownParent: $('#addCustomerModal'),
                    ajax: {
                      url: '/' + companyPrefix + '/PayTerms/payterm_list/',
                      dataType: 'json',
                      processResults: function (data) {
                        let results = data.map(function (item) {
                          return { id: item.id, text: item.name };
                        });
                        results.push({ id: 'new', text: '+ New', isNew: true });
                        return { results: results };
                      },
                      cache: true
                    }
                  });

                  $el.on('select2:select', function (e) {
                    var data = e.params.data;
                    if (data.id === 'new' || data.isNew) {
                      $('#paymentTermsModal').modal('show');
                      $el.val(null).trigger('change');
                    }
                  });
                } else {
                  $el.select2({ 
                    placeholder: $el.data('placeholder') || 'Select', 
                    allowClear: true, 
                    width: 'resolve', 
                    dropdownParent: $('#addCustomerModal') 
                  });
                }
              });
            }
          } catch (err) { console.warn('Select2 init on form load failed:', err); }

          // Prefill after modal is fully shown. Use .one() so handler runs once.
          $('#addCustomerModal').one('shown.bs.modal', function () {
            // Use setTimeout to run AFTER any other shown handlers complete
            setTimeout(function () {
              try {
                if (typedName) {
                  var $company = $('#addCustomerModal').find('input[name="company_name"]');
                  var $first = $('#addCustomerModal').find('input[name="first_name"]');

                  console.log('PRE-FILL: typedName=', typedName);
                  console.log('PRE-FILL: company field found=', $company.length);
                  console.log('PRE-FILL: first field found=', $first.length);

                  if ($company.length) {
                    $company.val(typedName).trigger('input');
                    console.log('PRE-FILL: company_name set to', $company.val());
                  } else if ($first.length) {
                    $first.val(typedName).trigger('input');
                    console.log('PRE-FILL: first_name set to', $first.val());
                  } else {
                    console.warn('PRE-FILL: Neither company_name nor first_name found in modal DOM');
                    console.log('Modal inputs:', $('#addCustomerModal input').map(function(){ return this.name; }).get());
                  }
                }
              } catch (e) {
                console.error('PRE-FILL error:', e);
              }
            }, 100);
          });

          $('#addCustomerModal').modal('show');
        });
        $(this).val(null).trigger('change');
      } else if (data && data.id) {
        window.applyCustomerDefaultPaymentTerms = true;
        try {
          if (typeof loadVendorDetails === 'function') {
            loadVendorDetails(data.id);
          }
        } catch (err) { console.warn('customer payment term detail load failed', err); }
      }
    });

    $('#sales_person_select').on('select2:select', function (e) {
      var data = e.params.data;
      if (data.id === 'new' || data.isNew) {
        $.get('/sales/saleperson_createform/', function (formHtml) {
          $('#salepersonCreateModal .modal-body').html(formHtml);
          $('#salepersonCreateModal').modal('show');
        });
        $(this).val(null).trigger('change');
      }
    });
  }, 500);
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


// Handle form submission after modals
$(document).on('submit', '#addCustomerModal form', function (ev) {
  ev.preventDefault();
  var $form = $(this);

  var method = ($form.attr('method') || 'POST').toUpperCase();

  // ALWAYS construct the correct URL with company code - don't rely on form action attribute
  var pathParts = window.location.pathname.split('/');
  var companyCode = pathParts[1]; // Extract company code from current URL
  var action = '/' + companyCode + '/sales/add_customer/';

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
        var modalEl = document.getElementById('addCustomerModal');
        try {
          var inst = bootstrap.Modal.getInstance(modalEl);
          if (inst) {
            inst.hide();
          } else {
            // create temporary instance to hide
            new bootstrap.Modal(modalEl).hide();
          }
        } catch (e) {
          try { $('#addCustomerModal').modal('hide'); } catch (ee) { /* ignore */ }
        }

        // Remove any previous errors and clear modal body
        $('#addCustomerModal .modal-body .alert.alert-danger').remove();
        $('#addCustomerModal .modal-body .text-danger.small').remove();

        var displayName = data.name || (data.first_name ? (data.first_name + (data.last_name ? ' ' + data.last_name : '')) : 'New');
        var newOption = new Option(displayName, data.id, true, true);
        var $sel = $('#customer_select');
        // Remove any existing option with same value to avoid duplicates
        $sel.find('option[value="' + data.id + '"]').remove();
        // Append once and set value — trigger a single change event
        $sel.append(newOption);
        $sel.val(data.id).trigger('change');
        // Explicit validation
        validateForm();
        // Refresh customer and currency details via the shared helper
        try {
          if (typeof loadVendorDetails === 'function') {
            window.applyCustomerDefaultPaymentTerms = true;
            loadVendorDetails(data.id);
          }
        } catch (err) { console.warn('force vendor details failed', err); }
        // Clear modal content after short delay to avoid race if Bootstrap animates
        setTimeout(function () { $('#addCustomerModal .modal-body').empty(); }, 300);
        validateForm(); // in case there were validation errors before that are now resolved
        return;
      }

      // Otherwise assume HTML returned (form with errors or full form) - replace modal body
      $('#addCustomerModal .modal-body').html(response);
      // Initialize //byadarshselect2 for any select elements injected into the modal (validation case)
      try {
        var $mb2 = $('#addCustomerModal .modal-body');
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
          $mb2.find('.select2').each(function () {
            var $el = $(this);
            // destroy existing select2 instance before re-initializing to avoid duplicates
            try { $el.select2('destroy'); } catch (e) { }
            $el.select2({ placeholder: $el.data('placeholder') || 'Select', allowClear: true, width: 'resolve', dropdownParent: $('#addCustomerModal') });
          });
        }
      } catch (initErr2) { console.warn('Select2 init failed after submit response:', initErr2); }//byadarsh
      // Reveal errors because this was a submit attempt
      try {
        $('#addCustomerModal').data('customerFormSubmitted', true);
        var $mb = $('#addCustomerModal .modal-body');
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
          $('#addCustomerModal .text-danger.small').remove();
          $('#addCustomerModal .alert.alert-danger').remove();

          // Render non-field errors
          if (json.errors.__all__ || json.errors.non_field_errors) {
            var nf = json.errors.__all__ || json.errors.non_field_errors;
            $('#addCustomerModal .modal-body').prepend('<div class="alert alert-danger">' + nf.join('<br>') + '</div>');
          }

          // Render field-specific errors next to inputs
          Object.keys(json.errors).forEach(function (field) {
            if (field === '__all__' || field === 'non_field_errors') return;
            var msgs = json.errors[field];
            // Try to find input/select/textarea with that name
            var $field = $('#addCustomerModal').find('[name="' + field + '"]');
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
              $('#addCustomerModal .modal-body').prepend('<div class="alert alert-danger"><strong>' + field + ':</strong> ' + msgs.join(', ') + '</div>');
            }
          });

          // Mark that the user attempted to submit so we reveal errors
          $('#addCustomerModal').data('customerFormSubmitted', true);
          // Reveal any errors we just added (CSS hides them by default inside the modal)
          try {
            var $mb_errors = $('#addCustomerModal .modal-body');
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
          $('#addCustomerModal .modal-body').html(xhr.responseText);
          // Reveal errors since this is response after failed submit
          try {
            $('#addCustomerModal').data('customerFormSubmitted', true);
            var $mb2 = $('#addCustomerModal .modal-body');
            $mb2.find('.text-danger.small, .text-danger, .invalid-feedback, .alert.alert-danger').show();
            $mb2.find('*').filter(function () { return $(this).text().trim() === 'This field is required.'; }).show();
          } catch (ee) { }
        } else {
          alert('Error saving customer. See console for details.');
          console.error('Customer save error', xhr);
        }
      }
    }
  });
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
//         // redirect to customer create page, pass current page as 'next'
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
      url: (function() {
        var parts = window.location.pathname.split('/');
        var first = parts[1] || '';
        var modules = ['sales', 'purchase', 'inventory', 'PayTerms', 'Items', 'customer', 'vendor', 'user', 'crm', 'hr', 'masters'];
        var cp = modules.includes(first.toLowerCase()) ? '' : first;
        return (cp ? '/' + cp : '') + '/sales/get_item_sales/';
      })(),
      dataType: 'json',
      delay: 250,
      data: params => {
        lastItemSearchTerm = params.term || '';
        return { q: params.term };
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
          tax_id: item.tax_id,
          tax_name: item.tax_name,
          tax_rate: item.tax_rate,
          tax_pref: item.tax_pref  // ✅ Add tax_pref to the data
          // })).concat([{ id: 'new', text: '+ New', isNew: true }])}))
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


  // Handle selection of "+ New" option
  $el.on('select2:select', function (e) {
    const data = e.params.data;
    let $sel = $(this);
    let $row = $sel.closest('tr');
    console.log("Selected ID:", data.id);
    console.log("Full Item Object:", data);

    // If user chose the special "+ New" option, open add-item modal
    if (data.isNew) {
      const searchTerm = lastItemSearchTerm || '';
      $('#item_name').val(searchTerm);
      const $thisRow = $(this).closest('tr');
      const rowIndex = $thisRow.index();
      if (window.setCurrentRowIndex) window.setCurrentRowIndex(rowIndex);
      window.activeItemSelectForNewItem = this;
      console.log('Captured search term for new item:', searchTerm);
      // Reset the select and modal form
      $(this).val(null).trigger('change');
      try { document.getElementById('addItemForm').reset(); } catch (e) { }
      if (searchTerm) $('#item_name').val(searchTerm);
      $('#item_tax_fields').show();
      $('#item_tax_pref').val('taxable');
      $('#addItemModal select').each(function () { if ($(this).hasClass('select2-hidden-accessible')) { $(this).val(null).trigger('change'); } });
      // Ensure selects inside modal are initialized before showing
      try {
        initializeItemModalSelects();
      } catch (e) { console.warn('initializeItemModalSelects failed:', e); }
      $('#addItemModal').modal('show');
      $('#addItemModal').on('shown.bs.modal', function handler() {
        setTimeout(function () { $('#item_name').focus().select(); }, 150);
        $('#addItemModal').off('shown.bs.modal', handler);
      });
      return;
    }

    // prices from the item API are in company base currency; convert to document currency
    let priceBase = parseFloat(data.price) || 0;
    let oPriceBase = parseFloat(data.o_price) || priceBase;

    // fx_rate_to_base means: amount_in_document_currency * fx = amount_in_base
    // So to convert base -> document currency: converted = base / fx
    let fx = parseFloat($('#fx_rate_to_base').val()) || 1;
    let convertedPrice = (fx && fx !== 1) ? (priceBase / fx) : priceBase;

    $row.find('.price').val(convertedPrice.toFixed(2));
    $row.find('.o_price').val(oPriceBase.toFixed(2));
    // show company/base currency price in a visible column
    setBasePriceDisplay($row, priceBase);
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
    allowClear: true,

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

function getRowTaxRate($row) {
  const taxPref = $row.data('tax-pref') || '';
  if (taxPref === 'non_taxable') return 0;
  const $selected = $row.find('.tax-select').find(':selected');
  return $selected.length ? (parseFloat($selected.data('rate')) || 0) : 0;
}

function updateMrpPreview($row) {
  const mrp = parseFloat($row.find('.mrp-input').val());
  const $popover = $row.find('.mrp-popover');
  if (!mrp || mrp <= 0) {
    $popover.find('.mrp-preview-price').text('₹0.00');
    $popover.find('.mrp-preview-gst').text('₹0.00');
    return;
  }
  const taxRate = getRowTaxRate($row);
  const price = mrp / (1 + taxRate / 100);
  const gst = mrp - price;
  $popover.find('.mrp-preview-price').text('₹' + price.toFixed(2));
  $popover.find('.mrp-preview-gst').text('₹' + gst.toFixed(2) + ' (' + taxRate + '%)');
}

function applyMrp($row) {
  const mrp = parseFloat($row.find('.mrp-input').val());
  if (!mrp || mrp <= 0) return;

  const taxRate = getRowTaxRate($row);
  const price = mrp / (1 + taxRate / 100);

  $row.find('.price').val(price.toFixed(2)).trigger('change');
  $row.data('custom-mrp', mrp);

  $row.find('.mrp-badge-text').text('MRP ₹' + mrp.toFixed(2));
  $row.find('.mrp-badge').show();
  $row.find('.mrp-toggle-btn').hide();
  $row.find('.mrp-popover').hide();
}

function clearMrp($row) {
  const masterPrice = $row.data('master_price');
  if (masterPrice !== undefined && masterPrice !== null) {
    $row.find('.price').val(parseFloat(masterPrice).toFixed(2)).trigger('change');
  }
  $row.removeData('custom-mrp');
  $row.find('.mrp-input').val('');
  $row.find('.mrp-badge').hide();
  $row.find('.mrp-toggle-btn').show();
}

// Open popover
$('#items-table').on('click', '.mrp-toggle-btn', function (e) {
  e.preventDefault();
  e.stopPropagation();
  $('.mrp-popover').not($(this).siblings('.mrp-popover')).hide();
  const $row = $(this).closest('tr');
  $row.find('.mrp-popover').show();
  $row.find('.mrp-input').trigger('focus');
});

// Live preview as user types
$('#items-table').on('input', '.mrp-input', function () {
  updateMrpPreview($(this).closest('tr'));
});

// Apply / Cancel / Clear
$('#items-table').on('click', '.mrp-apply-btn', function (e) {
  e.preventDefault();
  applyMrp($(this).closest('tr'));
});
$('#items-table').on('click', '.mrp-cancel-btn', function (e) {
  e.preventDefault();
  $(this).closest('.mrp-popover').hide();
});
$('#items-table').on('click', '.mrp-clear-btn', function (e) {
  e.preventDefault();
  clearMrp($(this).closest('tr'));
});

// Close popover on outside click
$(document).on('click', function (e) {
  if (!$(e.target).closest('.mrp-panel').length) {
    $('.mrp-popover').hide();
  }
});

// Recompute if tax changes while popover is open/applied
$('#items-table').on('select2:select change', '.tax-select', function () {
  const $row = $(this).closest('tr');
  updateMrpPreview($row);
  if ($row.data('custom-mrp')) {
    $row.find('.mrp-input').val($row.data('custom-mrp'));
    applyMrp($row);
  }
});


function hideSalesItemModal() {
  var modalEl = document.getElementById('addItemModal');
  if (!modalEl) return;

  function forceHideIfNeeded() {
    if (!modalEl.classList.contains('show')) return;
    modalEl.classList.remove('show');
    modalEl.style.display = 'none';
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.removeAttribute('aria-modal');
    modalEl.removeAttribute('role');
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('overflow');
    document.body.style.removeProperty('padding-right');
    if (window.jQuery) $('.modal-backdrop').remove();
  }

  if (window.bootstrap && bootstrap.Modal) {
    var modal = bootstrap.Modal.getInstance(modalEl) || bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.hide();
    setTimeout(forceHideIfNeeded, 250);
    return;
  }

  if (window.jQuery && typeof $('#addItemModal').modal === 'function') {
    $('#addItemModal').modal('hide');
    setTimeout(forceHideIfNeeded, 250);
    return;
  }

  forceHideIfNeeded();
}

window.hideSalesItemModal = hideSalesItemModal;



initTaxSelect($('.tax-select'));

$(function () {
  $('#items-table tbody tr').each(function () {
    const $row = $(this);
    if (parseBasePriceFromRow($row) === 0) {
      setBasePriceDisplay($row, 0);
    }
  });
});


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
  let baseAmount = getRowBaseAmount($row, qty, price);


  // let baseAmount = qty * price;
  // Get tax rate - for non-taxable items, this will be 0
  let taxRate = 0;
  if (taxPref !== 'non_taxable' && taxPref !== 'non_taxable') {
    taxRate = parseFloat($row.find('.tax-select').data('rate')) || 0;
  }

  // let taxRate = parseFloat($row.find('.tax-select').data('rate')) || 0;

  let discount = parseFloat($row.find('.item-discount').val()) || 0;
  let discountType = $row.find('.discount-type').val(); // 'flat' or 'percent'

  // Calculate base amount first = qty × price

  // Apply discount based on type
  let discountedAmount;
  if (discountType === 'percent') {
    // Percent discount on total amount
    discountedAmount = baseAmount - (baseAmount * discount / 100);
  } else {
    // Flat discount on total amount (not per unit)
    discountedAmount = baseAmount - discount;
  }
  if (discountedAmount < 0) discountedAmount = 0;

  // let taxAmount = baseAmount * (taxRate / 100);
  let taxAmount = discountedAmount * (taxRate / 100);
  console.log("taxAmount" + taxAmount);

  let grossAmount = getRowGrossAmount($row, qty, price, baseAmount, taxRate);
  let displayAmount = isGstIncludedValue($row.find('.gstinclude').val())
    ? (discountType === 'percent' ? grossAmount - (grossAmount * discount / 100) : Math.max(grossAmount - discount, 0))
    : discountedAmount;

  console.log("displayAmount: " + displayAmount);


  $row.find('.amount').text('₹' + displayAmount.toFixed(2));

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

  // Save values for totals
  $row.data({
    // baseAmount: baseAmount,
    baseAmount: discountedAmount,

    taxAmount: taxAmount,
    // finalAmount: finalAmount,
    isNonTaxable: (taxPref === 'non_taxable' || taxPref === 'non_taxable')
  });
}

function isGstIncludedValue(rawValue) {
  if (typeof rawValue === 'boolean') return rawValue;
  const normalized = String(rawValue || '').trim().toLowerCase();
  return normalized === 'true' || normalized === '1' || normalized === 'yes';
}

function getRowBaseAmount($row, qty, price) {
  const gstval = $row.find('.gstinclude').val();
  const gstIncluded = isGstIncludedValue(gstval);
  const fxInput = document.getElementById('fx_rate_to_base');
  const fxRate = fxInput ? (parseFloat(fxInput.value) || 1) : 1;
  const priceBase = parseFloat($row.data('price_base'));
  const oPriceBase = parseFloat($row.data('o_price_base'));

  console.log("gst included:" + gstval);
  console.log("priceBase", priceBase, "oPriceBase", oPriceBase, "fxRate", fxRate);

  const visibleAmount = qty * price;
  let baseAmountFromData = null;

  if (gstIncluded && Number.isFinite(oPriceBase) && oPriceBase > 0 && fxRate > 0) {
    baseAmountFromData = qty * (oPriceBase / fxRate);
  } else if (Number.isFinite(priceBase) && priceBase > 0 && fxRate > 0) {
    baseAmountFromData = qty * (priceBase / fxRate);
  }

  if (baseAmountFromData !== null && baseAmountFromData > 0) {
    const diff = Math.abs(baseAmountFromData - visibleAmount);
    if (diff > 0.0001 && visibleAmount > 0) {
      return visibleAmount;
    }
    return baseAmountFromData;
  }

  return visibleAmount;
}

function getRowGrossAmount($row, qty, price, baseAmount, taxRate) {
  const gstIncluded = isGstIncludedValue($row.find('.gstinclude').val());
  if (gstIncluded) {
    const fxInput = document.getElementById('fx_rate_to_base');
    const fxRate = fxInput ? (parseFloat(fxInput.value) || 1) : 1;
    const priceBase = parseFloat($row.data('price_base'));
    if (Number.isFinite(priceBase) && priceBase > 0 && fxRate > 0) {
      return qty * (priceBase / fxRate);
    }
    return qty * price;
  }
  return baseAmount + (baseAmount * (taxRate || 0) / 100);
}



function calculateTotals() {
  let subtotal = 0;
  // let allitmtotal = 0;
  let totalTax = 0;
  let totalDiscount = 0; // Track item-level discount separately from subtotal


  document.querySelectorAll("#items-table tbody tr").forEach(function (row) {
    // Skip rows hidden or marked deleted by neha on 23-12-25
    const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
    if ((deleteCheckbox && deleteCheckbox.checked) || row.style.display === 'none') {
      return; // Skip this row from calculations
    }
    let $row = $(row);
    let qty = parseFloat(row.querySelector(".qty").value) || 0;
    let price = parseFloat(row.querySelector(".price").value) || 0;
    let taxPref = $row.data('tax-pref') || '';
    let baseAmount = getRowBaseAmount($row, qty, price);
    console.log("baseAmount1" + baseAmount);

    // allitmtotal+=baseAmount;
    // console.log("allitmtotal1"+allitmtotal);


    // Item-level discount
    let discount = parseFloat($(row).find(".item-discount").val()) || 0;
    let discountType = $(row).find(".discount-type").val();

    // Apply discount based on type
    let discountedAmount;
    if (discountType === 'percent') {
      // Percent discount on total amount
      discountedAmount = baseAmount - (baseAmount * discount / 100);
    } else {
      // Flat discount on total amount (not per unit)
      discountedAmount = baseAmount - discount;
    }
    if (discountedAmount < 0) discountedAmount = 0;


    totalDiscount += baseAmount - discountedAmount;

    // Subtotal should remain the full pre-discount line total.
    subtotal += baseAmount;

    // tax-select handling
    // let $taxSelect = $(row).find(".tax-select");

    // Calculate tax
    let taxRate = 0;
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

    // update row amount cell- show only discounted amount (no tax)
    var curCode = getDocumentCurrencySymbol();
    const grossAmount = getRowGrossAmount($row, qty, price, baseAmount, taxRate);
    const displayAmount = isGstIncludedValue($row.find('.gstinclude').val())
      ? (discountType === 'percent' ? grossAmount - (grossAmount * discount / 100) : Math.max(grossAmount - discount, 0))
      : discountedAmount;
    row.querySelector(".amount").innerText = curCode + ' ' + displayAmount.toFixed(2);

    // subtotal += discountedAmount;
    // totalTax += taxAmount;
  });

  // Subtotal displays the pre-discount total of all rows.
  if (document.getElementById("subtotal")) document.getElementById("subtotal").innerText = getDocumentCurrencySymbol() + ' ' + subtotal.toFixed(2);

  // let total = subtotal + totalTax;
  // console.log("allitmtotal"+allitmtotal);
  // document.getElementById("subtotal").innerText = "₹" + allitmtotal.toFixed(2);

  // document.getElementById("subtotal").innerText = "₹" + subtotal.toFixed(2);



  // if (document.getElementById("tax-total")) {
  //   document.getElementById("tax-total").innerText = "₹" + totalTax.toFixed(2);
  // }

  // ✅ NEW: Display tax based on company country
  // If India company, split into CGST and SGST; otherwise show VAT
  if (typeof COMPANY_IS_INDIA !== 'undefined' && COMPANY_IS_INDIA === true) {
    // India: Split total tax into CGST and SGST (even split for intra-state)
    var cgst = (totalTax / 2) || 0;
    var sgst = (totalTax / 2) || 0;
    if (document.getElementById("tax-total-cgst")) {
      document.getElementById("tax-total-cgst").innerText = getDocumentCurrencySymbol() + ' ' + cgst.toFixed(2);
    }
    if (document.getElementById("tax-total-sgst")) {
      document.getElementById("tax-total-sgst").innerText = getDocumentCurrencySymbol() + ' ' + sgst.toFixed(2);
      
    }
  } else {
    // Non-India: Show VAT as single total tax
    if (document.getElementById("tax-total-vat")) {
      document.getElementById("tax-total-vat").innerText = getDocumentCurrencySymbol() + ' ' + totalTax.toFixed(2);

    }

  }
  // $('#discount-amount').text(totalDiscount.toFixed(2));

  // Total before grand discount = subtotal + tax.
  let totalBeforeDiscount = subtotal + totalTax;


  // Apply Grand Discount
  let grandDiscount = parseFloat($('#grand-discount').val()) || 0;
  let grandDiscountType = $('#grand-discount-type').val();
  let grandDiscountValue = 0;

  if (grandDiscountType === 'percent') {
    // grandDiscountValue = total * (grandDiscount / 100);
    grandDiscountValue = totalBeforeDiscount * (grandDiscount / 100);

  } else {
    grandDiscountValue = grandDiscount;
  }
  // if (grandDiscountValue > total) grandDiscountValue = total; // prevent negative

  if (grandDiscountValue > totalBeforeDiscount) grandDiscountValue = totalBeforeDiscount; // prevent negative

  // ✅ Display the grand discount value in the grandDiscountValue element
  $('#grandDiscountValue').text(getDocumentCurrencySymbol() + ' ' + grandDiscountValue.toFixed(2));

  // $('#discount-amount').text(discountValue.toFixed(2));
  // let grandTotal = total - grandDiscountValue;
  let grandTotal = totalBeforeDiscount - grandDiscountValue;

  let TotalDiscount = grandDiscountValue + totalDiscount;
  $('#discount-amount').text(TotalDiscount.toFixed(2));
  grandTotal = totalBeforeDiscount - TotalDiscount;
  if (grandTotal < 0) grandTotal = 0;

  syncTdsTcsDefinitionState();
  const tdsTcsType = document.querySelector('input[name="tds_tcs_type"]:checked')?.value || 'tds';
  const tdsTcsRate = parseFloat(document.getElementById('tds_tcs_rate')?.value) || 0;
  let tdsTcsAmount = 0;
  if (tdsTcsRate > 0) {
    tdsTcsAmount = grandTotal * tdsTcsRate / 100;
  }
  const tdsTcsLabel = tdsTcsType === 'tcs' ? 'TCS Amount' : 'TDS Amount';
  if (document.getElementById('tds-tcs-label')) {
    document.getElementById('tds-tcs-label').innerText = tdsTcsLabel;
  }
  if (document.getElementById('tds-tcs-amount')) {
    const sign = tdsTcsType === 'tds' ? '-' : '+';
    document.getElementById('tds-tcs-amount').innerText = getDocumentCurrencySymbol() + ' ' + sign + tdsTcsAmount.toFixed(2);
  }
  if (document.getElementById('tds_tcs_amount')) {
    document.getElementById('tds_tcs_amount').value = tdsTcsAmount.toFixed(2);
  }

  const fxInput = document.getElementById('fx_rate_to_base');
  const fxRateValue = fxInput ? (parseFloat(fxInput.value) || 1) : 1;
  const baseTdsTcsAmountValue = tdsTcsAmount * fxRateValue;

  const turnoverSelect = document.getElementById('turnover_tax_select');
  const isTurnoverCompany = String(window.COMPANY_TAX_TYPE || '').trim().toUpperCase() === 'TURNOVER';
  let turnoverTaxAmount = 0;
  if (isTurnoverCompany && turnoverSelect && turnoverSelect.value) {
    const selectedOption = turnoverSelect.options[turnoverSelect.selectedIndex];
    const selectedId = String(turnoverSelect.value || '');
    const cachedRates = window.turnoverTaxRates || {};
    let turnoverRate = parseFloat(
      (selectedOption && selectedOption.dataset && selectedOption.dataset.rate) ||
      $(turnoverSelect).find(':selected').data('rate') ||
      cachedRates[selectedId]
    ) || 0;
    turnoverTaxAmount = grandTotal * turnoverRate / 100;
  }

  const finalGrandTotal = grandTotal + turnoverTaxAmount;
  if (document.getElementById("turnover-tax-amount")) {
    document.getElementById("turnover-tax-amount").innerText = getDocumentCurrencySymbol() + ' ' + turnoverTaxAmount.toFixed(2);
  }

  const tdsTcsSignedAmount = tdsTcsType === 'tds' ? -tdsTcsAmount : tdsTcsAmount;
  let finalGrandTotalWithTdsTcs = finalGrandTotal + tdsTcsSignedAmount;
  if (finalGrandTotalWithTdsTcs < 0) finalGrandTotalWithTdsTcs = 0;

  const roundingMethod = String(window.SALES_ROUNDING_METHOD || 'none').toLowerCase();
  const roundingIncrement = Number(window.SALES_ROUNDING_INCREMENT || 0);
  const unroundedTotal = finalGrandTotalWithTdsTcs;
  if (roundingMethod === 'whole') {
    finalGrandTotalWithTdsTcs = Math.round(unroundedTotal);
  } else if (roundingMethod === 'increment' && roundingIncrement > 0) {
    finalGrandTotalWithTdsTcs = Math.round(unroundedTotal / roundingIncrement) * roundingIncrement;
  }
  const roundOffAmount = finalGrandTotalWithTdsTcs - unroundedTotal;
  const unroundedTotalElement = document.getElementById('unroundedGrandTotal');
  if (unroundedTotalElement) unroundedTotalElement.value = unroundedTotal.toFixed(2);
  const roundOffElement = document.getElementById('round-off-amount');
  if (roundOffElement) roundOffElement.innerText = getDocumentCurrencySymbol() + ' ' + roundOffAmount.toFixed(2);

  if (document.getElementById("grand-total")) document.getElementById("grand-total").innerText = getDocumentCurrencySymbol() + ' ' + finalGrandTotalWithTdsTcs.toFixed(2);
  document.getElementById('grandTotal').value = finalGrandTotalWithTdsTcs.toFixed(2);
  const baseSubtotalValue = subtotal * fxRateValue;
  const baseTotalTaxValue = totalTax * fxRateValue;
  const baseTotalDiscountValue = TotalDiscount * fxRateValue;
  const baseGrandTotalValue = finalGrandTotalWithTdsTcs * fxRateValue;

  const baseSummaryCard = document.getElementById('base-transaction-summary');
  if (baseSummaryCard) {
    const docCurrencySelect = document.getElementById('document_currency');
    const docBaseSymbol =
      (docCurrencySelect && docCurrencySelect.dataset && docCurrencySelect.dataset.baseSymbol) ||
      (docCurrencySelect && docCurrencySelect.getAttribute('data-base-symbol'));
    const baseSymbol =
      baseSummaryCard.dataset.baseSymbol || docBaseSymbol || DEFAULT_CURRENCY_SYMBOL;
    const formatAmount = (val) => baseSymbol + ' ' + (Number.isFinite(val) ? val : 0).toFixed(2);

    const baseSubtotalEl = document.getElementById('base-subtotal');
    if (baseSubtotalEl) baseSubtotalEl.innerText = formatAmount(baseSubtotalValue);
    const baseCgstEl = document.getElementById('base-tax-cgst');
    if (baseCgstEl) baseCgstEl.innerText = formatAmount(baseTotalTaxValue / 2);
    const baseSgstEl = document.getElementById('base-tax-sgst');
    if (baseSgstEl) baseSgstEl.innerText = formatAmount(baseTotalTaxValue / 2);
    const baseVatEl = document.getElementById('base-tax-vat');
    if (baseVatEl) baseVatEl.innerText = formatAmount(baseTotalTaxValue);
    const baseDiscountEl = document.getElementById('base-total-discount');
    if (baseDiscountEl) baseDiscountEl.innerText = formatAmount(baseTotalDiscountValue);
    const baseTdsTcsLabelEl = document.getElementById('base-tds-tcs-label');
    if (baseTdsTcsLabelEl) baseTdsTcsLabelEl.innerText = tdsTcsType === 'tcs' ? 'TCS Amount' : 'TDS Amount';
    const baseTdsTcsAmountEl = document.getElementById('base-tds-tcs-amount');
    if (baseTdsTcsAmountEl) baseTdsTcsAmountEl.innerText = formatAmount(baseTdsTcsAmountValue);
    const baseGrandTotalEl = document.getElementById('base-grand-total');
    if (baseGrandTotalEl) baseGrandTotalEl.innerText = formatAmount(baseGrandTotalValue);
  }

  if (typeof window.refreshCustomerCreditSummary === 'function') {
    window.refreshCustomerCreditSummary();
  }
}


// --- On qty or price change ---
$('#items-table').on('input change', '.qty, .price, .item-discount, .discount-type', function () {
  let $row = $(this).closest('tr');

  // If user edited the visible document-currency price, update stored base prices
  if ($(this).hasClass('price')) {
    const docPrice = parseFloat($row.find('.price').val()) || 0;
    const fx = parseFloat($('#fx_rate_to_base').val()) || 1;
    const priceBase = docPrice * fx;
    $row.data('price_base', priceBase);
    $row.data('o_price_base', priceBase);
    // keep server-hidden field in sync
    $row.find('.o_price').val(priceBase.toFixed(2));
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
  if (selectedType === 'tds' && tdsSelect) {
    selectedOption = tdsSelect.options[tdsSelect.selectedIndex];
  } else if (selectedType === 'tcs' && tcsSelect) {
    selectedOption = tcsSelect.options[tcsSelect.selectedIndex];
  }

  const rate = selectedOption ? parseFloat(selectedOption.dataset.rate || selectedOption.value || 0) : 0;
  const taxId = selectedOption ? selectedOption.value || '' : '';

  if (hiddenRate) {
    hiddenRate.value = Number.isFinite(rate) ? rate : 0;
  }
  if (hiddenId) {
    hiddenId.value = taxId;
  }
}

$(document).on('change', 'input[name="tds_tcs_type"], #tds_definition_select, #tcs_definition_select', function () {
  syncTdsTcsDefinitionState();
  calculateTotals();
});
$(document).on('select2:select', '#turnover_tax_select', function (event) {
  const selected = event.params && event.params.data;
  if (!selected) return;
  window.turnoverTaxRates = window.turnoverTaxRates || {};
  if (selected.id !== undefined && selected.rate !== undefined) {
    window.turnoverTaxRates[String(selected.id)] = selected.rate;
  }
  const option = this.options[this.selectedIndex];
  if (option && selected.rate !== undefined) {
    option.dataset.rate = selected.rate;
    $(option).data('rate', selected.rate);
  }
});
$(document).on('change select2:select select2:clear', '#turnover_tax_select', calculateTotals);

document.querySelectorAll('input[type="number"]').forEach(input => {
  input.addEventListener('focus', function () {
    this.select();
  });
});





document.addEventListener("DOMContentLoaded", function () {

  // Ensure qty inputs accept decimal quantities (e.g., 0.5)
  function allowDecimalQtys(scope) {
    (scope || document).querySelectorAll('input.qty').forEach(function (el) {
      try {
        el.setAttribute('min', '0.01');
        el.setAttribute('step', '0.01');
      } catch (e) { /* ignore */ }
    });
  }

  // Apply initially and watch for dynamically added rows
  allowDecimalQtys(document);
  // MutationObserver to patch future rows added to items table
  try {
    const itemsTableBody = document.querySelector('#items-table tbody');
    if (itemsTableBody) {
      const mo = new MutationObserver(function (mutations) {
        mutations.forEach(function (m) {
          m.addedNodes.forEach(function (n) {
            if (n.nodeType === 1) allowDecimalQtys(n);
          });
        });
      });
      mo.observe(itemsTableBody, { childList: true, subtree: true });
    }
  } catch (e) { console.warn('allowDecimalQtys observer failed', e); }


  rebuildCurrencySymbolMap();
  updateFlatDiscountSymbols();
  bindDocumentCurrencyChange();
  syncDocumentCurrencyMirror();
  updateBaseCurrencyVisibility();

  // Recalculate document-currency prices from stored company/base prices when FX changes
  function refreshPricesFromBase() {
    window.isRefreshingPricesFromFx = true;
    let fx = parseFloat($('#fx_rate_to_base').val()) || 1;
    $('#items-table tbody tr').each(function () {
      const $row = $(this);
      // Robust: if we already have stored base prices (price_base / o_price_base) use them.
      // Otherwise try to infer base prices from current document-currency values using existing FX.
      let priceBaseRaw = $row.data('price_base');
      let oPriceBaseRaw = $row.data('o_price_base');
      let priceBase = (priceBaseRaw !== undefined && priceBaseRaw !== null) ? parseFloat(priceBaseRaw) : NaN;
      let oPriceBase = (oPriceBaseRaw !== undefined && oPriceBaseRaw !== null) ? parseFloat(oPriceBaseRaw) : NaN;

      if (!Number.isFinite(oPriceBase) || oPriceBase === 0) {
        const hiddenBasePrice = parseFloat($row.find('.o_price').val()) || 0;
        if (hiddenBasePrice > 0) {
          oPriceBase = hiddenBasePrice;
        }
      }

      if (!Number.isFinite(priceBase) || priceBase === 0) {
        const displayBasePrice = parseBasePriceFromRow($row);
        if (displayBasePrice > 0) {
          priceBase = displayBasePrice;
          if (!Number.isFinite(oPriceBase) || oPriceBase === 0) {
            oPriceBase = displayBasePrice;
          }
        }
      }

      if (!Number.isFinite(priceBase) || priceBase === 0) {
        // Attempt to deduce base price from the currently shown document-currency price
        const docPrice = parseFloat($row.find('.price').val()) || 0;
        const docOPrice = parseFloat($row.find('.o_price').val()) || docPrice;
        if (docPrice > 0) {
          // fx means: document_amount * fx = base_amount
          priceBase = docPrice * fx;
          oPriceBase = docOPrice * fx;
          // Store for future conversions
          $row.data('price_base', priceBase);
          $row.data('o_price_base', oPriceBase);
          $row.find('.o_price').val(oPriceBase.toFixed(2));
        }
      }

      if (Number.isFinite(priceBase) && priceBase > 0) {
        let converted = (fx && fx !== 1) ? (priceBase / fx) : priceBase;
        $row.find('.price').val(converted.toFixed(2));
        if (Number.isFinite(oPriceBase) && oPriceBase > 0) {
          $row.find('.o_price').val(oPriceBase.toFixed(2));
        }
        setBasePriceDisplay($row, priceBase);
        try { updateRowAmount($row); } catch (e) { }
      }
    });
    calculateTotals();
    window.isRefreshingPricesFromFx = false;
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
        let oPriceValue = parseFloat(oPriceInput.val()) || 0;
        if (oPriceValue <= 0) {
          oPriceValue = basePriceValue || 0;
          if (oPriceValue > 0) {
            oPriceInput.val(oPriceValue.toFixed(2));
          }
        }
        if (oPriceValue > 0) {
          $row.data('o_price_base', oPriceValue);
        }
      }
    });
  }

  // Bind FX input changes (if present in the DOM)
  $('#fx_rate_to_base').on('input change', function () {
    updateBaseCurrencyVisibility();
    refreshPricesFromBase();
  });

  seedBasePriceData();
  refreshPricesFromBase();

  // Ensure base-price/amount refresh when document currency changes (updates symbol mapping)
  var _docSel2 = document.getElementById('document_currency');
  if (_docSel2) {
    _docSel2.addEventListener('change', function () { try { refreshPricesFromBase(); } catch (e) { } });
    try {
      // Watch for attribute changes on the currency select (defensive). Some libraries update attributes instead
      var _mo = new MutationObserver(function (muts) {
        try { refreshPricesFromBase(); } catch (e) { }
      });
      _mo.observe(_docSel2, { attributes: true, childList: false, subtree: false });
    } catch (e) { /* ignore mutation observer errors */ }
  }

  // // restoreFormData();


  // const customerSelect = document.getElementById('customer_select');
  // // const payTermsSelect = document.getElementById('pay-terms');
  // const itemsTable = document.getElementById('items-table');
  // // Scope the main save button to the purchase form so modal submit buttons are not affected
  // const saveButton = (form && form.querySelector) ? form.querySelector('button[type="submit"].btn.btn-primary') : document.querySelector('button[type="submit"].btn.btn-primary');



  // function validateForm() {
  //     let isValid = true;

  //     // 1. customer selected (not empty/null)
  //     if (!customerSelect.value) {
  //       console.log("no customer is selected");

  //       isValid = false;
  //     }

  //     // 2. Payment term selected
  //     // if (!payTermsSelect.value) {
  //     //         console.log("no pay term is selected");

  //     //   isValid = false;
  //     // }

  //     // 3. At least one item row with valid item selected

  //     const allRows = itemsTable.querySelectorAll('tbody tr');

  //     // Only consider visible, non-deleted rows
  //     const rows = Array.from(allRows).filter(row => {
  //       const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
  //       const isDeleted = deleteCheckbox && deleteCheckbox.checked;
  //       const isHidden = row.style.display === 'none';
  //       return !isDeleted && !isHidden;
  //     });

  //     // const rows = itemsTable.querySelectorAll('tbody tr');
  //     if (rows.length === 0) {
  //       console.log("row length 0");
  //       isValid = false;
  //     } else {
  //       console.log("row length 1");

  //       // Check that each row has item selected
  //       for (const row of rows) {
  //         const itemSelect = row.querySelector('select.item_select');
  //         const qtyInput = row.querySelector('input.qty');
  //         const priceInput = row.querySelector('input.price');
  //         if (!qtyInput || !priceInput) {
  //         console.error('Quantity or Price input missing in row:', row);
  //         isValid = false;
  //         break;
  //       }

  //         if (!itemSelect || !itemSelect.value || itemSelect.value === "") {
  //             console.log("no item is selected");

  //           isValid = false;
  //           break;
  //         }
  //               console.log("item is selected");

  //         // 4. Quantity and price minimum 1
  //         const qty = parseFloat(qtyInput.value);
  //         const price = parseFloat(priceInput.value);
  //         console.log("value of qty:",qty);
  //         console.log("value of price:",price);
  //         if (isNaN(qty) || isNaN(price)) {
  //           console.log('Quantity or Price value is not numeric:', qtyInput.value, priceInput.value);
  //           isValid = false;
  //           break;
  //         }

  //         if (isNaN(qty) || qty < 1 || isNaN(price) || price < 0) {
  //                 console.log("value error in qty & price");

  //           isValid = false;
  //           break;
  //         }
  //       }
  //     }
  //     console.log("called validate form");

  //     console.log("value of isValid :"+isValid);
  //     saveButton.disabled = !isValid;
  //     if (!isValid) {
  //       saveButton.parentElement.title = "Fill the required fields"; // Title on wrapper div
  //     } else {
  //       saveButton.parentElement.title = "";
  //     }

  //   }

  //   // Attach event listeners to validate on changes
  //   // customerSelect.addEventListener('change', validateForm);
  //   $('#customer_select').on('select2:select select2:unselect', function() {
  //     validateForm();
  //     $('#customer_select').on('change', validateForm);
  //   });

  //   // payTermsSelect.addEventListener('change', validateForm);
  // //   $('#pay-terms').on('select2:select select2:unselect', function() {
  // //   validateForm();
  // // });


  //   // Delegate event listener for item select, qty, and price changes inside items table
  //   // itemsTable.addEventListener('change', function(e) {
  //   //   if (e.target.classList.contains('item_select') || e.target.classList.contains('qty') || e.target.classList.contains('price')) {
  //   //     validateForm();
  //   //   }
  //   // });
  //   $('#items-table').on('select2:select select2:unselect', '.item_select', function () {
  //     validateForm();
  //   });

  //   // itemsTable.addEventListener('input', function(e) {
  //   //   if (e.target.classList.contains('qty') || e.target.classList.contains('price')) {
  //   //     validateForm();
  //   //   }
  //   // });
  //   $('#items-table').on('input', '.qty, .price', function () {
  //     validateForm();
  //   });

  //   // Also check validation on page load in case of prefilled form
  //   validateForm();
  _customerSelect = document.getElementById('customer_select');
  _itemsTable = document.getElementById('items-table');
  // _saveButton = (form && form.querySelector)
  //   ? form.querySelector('button[type="submit"].btn.btn-primary')
  //   : document.querySelector('button[type="submit"].btn.btn-primary');

  const salesForm = document.getElementById('salesinvoice-form');
  _saveButton = salesForm
    ? salesForm.querySelector('button[type="submit"].btn.btn-primary')
    : document.querySelector('button[type="submit"].btn.btn-primary');

  $('#customer_select').on('select2:select select2:unselect', function () {
    validateForm();
  });

  $('#items-table').on('select2:select select2:unselect', '.item_select', function () {
    validateForm();
  });

  $('#items-table').on('input', '.qty, .price', function () {
    validateForm();
  });

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
      let newRow = `
    <tr data-tax-pref="">
      <td>
        <select name="form-${idx}-product" class="item_select"></select>
        <div style="margin-top:6px;">
          <a href="#" class="open-hsn-btn">HSN: <span class="hsn-display"></span> <small style="color:#3a7bd5;">Update</small></a>
          <input type="hidden" name="form-${idx}-hsn_code" class="hsn-input">
        </div>
      </td>
      <td><input type="text" class="desc" name="items[${idx}][description]"></td>
      <td><input type="number" class="qty" name="form-${idx}-quantity" value="1" min="0.01" step="0.01"></td>
      <td class="price-cell">
        <input type="number" class="price" name="form-${idx}-price" min="0.01" step="0.01" value="0">

        <div class="mrp-panel">
          <button type="button" class="mrp-toggle-btn"><i class="bi bi-calculator"></i> MRP</button>

          <div class="mrp-badge" style="display:none;">
            <span class="mrp-badge-text"></span>
            <button type="button" class="mrp-clear-btn" title="Remove custom price"><i class="bi bi-x-circle"></i></button>
          </div>

          <div class="mrp-popover" style="display:none;">
            <label class="mrp-popover-label">MRP (incl. GST)</label>
            <input type="number" class="mrp-input form-control form-control-sm" placeholder="e.g. 300" min="0" step="0.01">
            <div class="mrp-breakdown">
              <div><span>Pre-GST Price</span><strong class="mrp-preview-price">₹0.00</strong></div>
              <div><span>GST Amount</span><strong class="mrp-preview-gst">₹0.00</strong></div>
            </div>
            <div class="mrp-popover-actions">
              <button type="button" class="btn btn-sm btn-link mrp-cancel-btn">Cancel</button>
              <button type="button" class="btn btn-sm btn-primary mrp-apply-btn">Apply</button>
            </div>
          </div>
        </div>
      </td>
      <td class="base-price">
        <input type="text" class="form-control form-control-sm o_price_display" name="form-${idx}-o_price_display" value="" readonly>
      </td>
      <td style="display:flex;gap:2px;" class="discount-item">
              <input type="number" class="item-discount" name="form-${idx}-prd_disvalue" value="0" min="0" step="0.01">
        <select class="discount-type rupee-sign" name="form-${idx}-prd_distype">
          <option value="flat" class="rupee-sign">&#8377;</option>
          <option value="percent">%</option>
        </select>
      </td>
      <td><select class="tax-select" name="form-${idx}-prd_tax"></select></td>

      <td style="display:none;"><input type="hidden" name="form-${idx}-gstinclude" class="gstinclude"></td>
      <td style="display:none;"><input type="hidden" name="form-${idx}-o_price" class="o_price"></td>
      <td class="amount">₹0.00</td>
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


$(document).on('submit', '#customerCreateForm', function (e) {
  e.preventDefault();
  var $form = $(this);
  // Construct company-prefixed URL to avoid posting to root /sales/ endpoint
  var companyPrefix = (function() {
    var parts = window.location.pathname.split('/');
    var first = parts[1] || '';
    var modules = ['sales', 'purchase', 'inventory', 'PayTerms', 'Items', 'customer', 'vendor', 'user', 'crm', 'hr', 'masters'];
    return modules.includes(first.toLowerCase()) ? '' : first;
  })();
  var customerUrl = (companyPrefix ? '/' + companyPrefix : '') + '/sales/add_customer/';

  $.ajax({
    method: 'POST',
    url: customerUrl,
    data: $form.serialize(),
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    success: function (response) {
      if (response.success) {
        // close modal
        var modalEl = document.getElementById('customerCreateModal');
        var modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();

        // add customer to select2 and select it
        var newOption = new Option(response.name, response.id, true, true);
        $('#customer_select').append(newOption).trigger('change');
      }
    },
    error: function (xhr) {
      var errors = xhr.responseJSON?.errors || {};
      var errorMsg = errors.name ? errors.name.join(', ') : 'Error creating customer';
      $('#customerCreateModal .modal-body').prepend(
        `<div class="alert alert-danger">${errorMsg}</div>`
      );
    }
  });
});

$(document).on('submit', '#salepersonCreateForm', function (e) {
  e.preventDefault();
  var $form = $(this);
  // Construct company-prefixed URL for sales person create
  var pathParts = window.location.pathname.split('/');
  var companyCode = pathParts[1] || '';
  var salepersonUrl = '/' + companyCode + '/sales/add_salesperson/';

  $.ajax({
    method: 'POST',
    url: salepersonUrl,
    data: $form.serialize(),
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    success: function (response) {
      if (response.success) {
        // close modal
        var modalEl = document.getElementById('salepersonCreateModal');
        var modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();

        // add customer to select2 and select it
        var newOption = new Option(response.name, response.id, true, true);
        $('#sales_person_select').append(newOption).trigger('change');
      }
    },
    error: function (xhr) {
      var errors = xhr.responseJSON?.errors || {};
      var errorMsg = errors.name ? errors.name.join(', ') : 'Error creating customer';
      $('#salepersonCreateModal .modal-body').prepend(
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




  document.querySelector("#items-table").addEventListener("change", function (e) {
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
    let newRow = `
    <tr data-tax-pref="">
      <td>
        <select name="form-${idx}-product" class="item_select"></select>
        <div style="margin-top:6px;">
          <a href="#" class="open-hsn-btn">HSN: <span class="hsn-display"></span> <small style="color:#3a7bd5;">Update</small></a>
          <input type="hidden" name="form-${idx}-hsn_code" class="hsn-input">
        </div>
      </td>
      <td><input type="text" class="desc" name="items[${idx}][description]"></td>
      <td><input type="number" class="qty" name="form-${idx}-quantity" value="1" min="0.01" step="0.01"></td>
      <td class="price-cell">
        <input type="number" class="price" name="form-${idx}-price" min="0.01" step="0.01" value="0">

        <div class="mrp-panel">
          <button type="button" class="mrp-toggle-btn"><i class="bi bi-calculator"></i> MRP</button>

          <div class="mrp-badge" style="display:none;">
            <span class="mrp-badge-text"></span>
            <button type="button" class="mrp-clear-btn" title="Remove custom price"><i class="bi bi-x-circle"></i></button>
          </div>

          <div class="mrp-popover" style="display:none;">
            <label class="mrp-popover-label">MRP (incl. GST)</label>
            <input type="number" class="mrp-input form-control form-control-sm" placeholder="e.g. 300" min="0" step="0.01">
            <div class="mrp-breakdown">
              <div><span>Pre-GST Price</span><strong class="mrp-preview-price">₹0.00</strong></div>
              <div><span>GST Amount</span><strong class="mrp-preview-gst">₹0.00</strong></div>
            </div>
            <div class="mrp-popover-actions">
              <button type="button" class="btn btn-sm btn-link mrp-cancel-btn">Cancel</button>
              <button type="button" class="btn btn-sm btn-primary mrp-apply-btn">Apply</button>
            </div>
          </div>
        </div>
      </td>
      <td class="base-price">
        <input type="text" class="form-control form-control-sm o_price_display" name="form-${idx}-o_price_display" value="" readonly>
      </td>
      <td style="display:flex;gap:2px;" class="discount-item">
              <input type="number" class="item-discount" name="form-${idx}-prd_disvalue" value="0" min="0" step="0.01">
        <select class="discount-type rupee-sign" name="form-${idx}-prd_distype">
          <option value="flat" class="rupee-sign">&#8377;</option>
          <option value="percent">%</option>
        </select>
      </td>
      <td><select class="tax-select" name="form-${idx}-prd_tax"></select></td>

      <td style="display:none;"><input type="hidden" name="form-${idx}-gstinclude" class="gstinclude"></td>
      <td style="display:none;"><input type="hidden" name="form-${idx}-o_price" class="o_price"></td>
      <td class="amount">₹0.00</td>
      <td><button type="button" class="remove-item-btn">X</button></td>
</tr>`;
    $('#items-table tbody').append(newRow);
    const $newRow = $('#items-table tbody tr:last');
    setBasePriceDisplay($newRow, 0);
    initItemSelect($newRow.find('.item_select'));
    initTaxSelect($newRow.find('.tax-select'));
    calculateTotals();
    updateFlatDiscountSymbols();
    // Also update management form's TOTAL_FORMS value after adding a new row
    let totalForms = $('#id_form-TOTAL_FORMS');
    if (totalForms.length) {
      let currentCount = parseInt(totalForms.val(), 10);
      totalForms.val(currentCount + 1);
    }
  });

  // 3. Remove Item Row
  //added by neha for remove item btn on 23-12-25
  document.querySelector("#items-table").addEventListener("click", function (e) {
    if (e.target.classList.contains("remove-item-btn")) {
      console.log("remove-item-btn cliked");
      const formRow = e.target.closest("tr");
      const deleteCheckbox = formRow.querySelector('input[type="checkbox"][name$="-DELETE"]');

      if (deleteCheckbox) {
        // Existing DB-backed row: mark for deletion and disable its inputs so
        // validation ignores it and it won't be submitted as an active row.
        deleteCheckbox.checked = true;
        formRow.querySelectorAll('input, select, textarea, button').forEach(function(el) {
          try {
            // keep the DELETE checkbox enabled so Django processes it
            if (el === deleteCheckbox) return;
            el.disabled = true;
          } catch (err) { /* ignore */ }
        });
        formRow.style.display = 'none';
      } else {
        // Newly added row (no DELETE checkbox) — remove from DOM and update
        // the management form TOTAL_FORMS value if present.
        formRow.remove();
        let totalForms = document.querySelector('#id_form-TOTAL_FORMS');
        if (totalForms) {
          let currentCount = parseInt(totalForms.value || '0', 10);
          totalForms.value = String(Math.max(0, currentCount - 1));
        }
      }

      calculateTotals();
      console.log("Row deleted - calling validateForm now");
      validateForm();
    }
  });

  // 4. Calculate Totals
  document.querySelector("#items-table").addEventListener("input", calculateTotals);


  calculateTotals();

});

// Re-price existing rows when FX rate changes
$(document).on('input change', '#fx_rate_to_base', function () {
  try {
    updateBaseCurrencyVisibility();
    let fx = parseFloat($(this).val()) || 1;
    $('#items-table tbody tr').each(function () {
      let $row = $(this);
      let priceBase = parseFloat($row.data('price_base')) || 0;
      let oPriceBase = parseFloat($row.data('o_price_base')) || 0;
      if (priceBase > 0) {
        let converted = (fx && fx !== 1) ? (priceBase / fx) : priceBase;
        $row.find('.price').val(converted.toFixed(2));
      }
      if (oPriceBase > 0) {
        $row.find('.o_price').val(oPriceBase.toFixed(2));
      }
      updateRowAmount($row);
    });
    calculateTotals();
  } catch (e) { console.warn('reprice on fx change failed', e); }
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
    let $selectedOption = $(this).find(':selected');
    let selectedOptionData = $selectedOption.data() || {};
    data = Object.assign({}, selectedOptionData, data);
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
    // if ($oPriceInput.length) {
    //   $oPriceInput.val(parseFloat(data.o_price) || 0);
    //   console.log("Set o_price to:", $oPriceInput.val());
    // } else {
    //   console.warn("No .o_price input found in this row");
    // }


    if ($oPriceInput.length) {
      let priceBase2 = parseFloat(data.price) || 0;
      let oPriceBase2 = parseFloat(data.o_price) || priceBase2;
      let fx2 = parseFloat($('#fx_rate_to_base').val()) || 1;
      let convertedP = (fx2 && fx2 !== 1) ? (priceBase2 / fx2) : priceBase2;
      $oPriceInput.val(oPriceBase2.toFixed(2));
      console.log("Set o_price to:", $oPriceInput.val());
      $row.find('.price').val(convertedP.toFixed(2));
      $row.data('price_base', priceBase2);
      $row.data('o_price_base', oPriceBase2);
    } else {
      console.warn("No .o_price input found in this row", $row.html());
      $row.find('.price').val(data.price || 0);//seting price of item in the price field
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

    // Prefill HSN information for the selected item without auto-opening the modal.
    // The modal should open only when the user clicks the "Update" link.
    const $currentRow = $row;
    // Keep a reference for manual updates
    $('#hsnModal').data('targetRow', $currentRow);
    let itemVal = $(this).val() || '';
    let itemId = (itemVal.indexOf('_') !== -1) ? itemVal.split('_')[0] : itemVal;
    // Clear modal select2 input (but do not open modal here)
    $('#hsn_select').empty().trigger('change');
    if (itemId) {
      $.get('/Items/get-item-hsn/', { item_id: itemId })
        .done(function (resp) {
          if (resp.hsn_id) {
            // If the product has a defined HSN, apply it to the row (no modal)
            $currentRow.find('.hsn-input').val(resp.hsn_code);
            $currentRow.find('.hsn-display').text(resp.hsn_code);
          } else {
            // No HSN from server. If this row already stores an HSN, display it; otherwise leave blank
            const existing = $currentRow.find('.hsn-input').val() || '';
            if (existing) {
              $currentRow.find('.hsn-display').text(existing);
              const opt = new Option(existing, existing, true, true);
              $('#hsn_select').append(opt).trigger('change');
            } else {
              $currentRow.find('.hsn-display').text('');
            }
          }
        })
        .fail(function () {
          // On failure, prefer any existing HSN on the row; otherwise leave blank
          const existing = $currentRow.find('.hsn-input').val() || '';
          if (existing) { $currentRow.find('.hsn-display').text(existing); }
        });
    } else {
      // no item selected; clear the display
      $currentRow.find('.hsn-display').text('');
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
    if (typeof validateForm === 'function') {
      validateForm();
    }
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

function showBarcodeToast(message, type) {
  var toastContainer = document.getElementById('barcode-toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'barcode-toast-container';
    toastContainer.style.position = 'fixed';
    toastContainer.style.top = '20px';
    toastContainer.style.right = '20px';
    toastContainer.style.zIndex = '1080';
    toastContainer.style.display = 'flex';
    toastContainer.style.flexDirection = 'column';
    toastContainer.style.gap = '10px';
    toastContainer.style.pointerEvents = 'none';
    document.body.appendChild(toastContainer);
  }

  var toastEl = document.createElement('div');
  toastEl.setAttribute('role', 'alert');
  toastEl.setAttribute('aria-live', 'assertive');
  toastEl.setAttribute('aria-atomic', 'true');
  toastEl.style.minWidth = '220px';
  toastEl.style.maxWidth = '320px';
  toastEl.style.padding = '10px 14px';
  toastEl.style.borderRadius = '8px';
  toastEl.style.color = '#fff';
  toastEl.style.background = type === 'error' ? '#dc3545' : '#198754';
  toastEl.style.boxShadow = '0 8px 25px rgba(0,0,0,0.18)';
  toastEl.style.fontSize = '0.95rem';
  toastEl.style.lineHeight = '1.4';
  toastEl.style.opacity = '0';
  toastEl.style.transform = 'translateY(-8px)';
  toastEl.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
  toastEl.textContent = message || '';

  toastContainer.appendChild(toastEl);

  requestAnimationFrame(function () {
    toastEl.style.opacity = '1';
    toastEl.style.transform = 'translateY(0)';
  });

  setTimeout(function () {
    toastEl.style.opacity = '0';
    toastEl.style.transform = 'translateY(-8px)';
    setTimeout(function () {
      if (toastEl.parentNode) toastEl.parentNode.removeChild(toastEl);
    }, 220);
  }, 2800);
}

function setBarcodeStatus(message, type) {
  var status = document.getElementById('invoice-barcode-status');
  if (message && message !== 'Searching...') {
    showBarcodeToast(message, type);
  }

  if (!status) return;
  status.textContent = message || '';
  status.style.color = type === 'error' ? '#b42318' : '#198754';
  status.style.display = message ? 'block' : 'none';
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

  if (document.getElementById('invoice-barcode-status')) {
    document.getElementById('invoice-barcode-status').textContent = 'Searching...';
    document.getElementById('invoice-barcode-status').style.display = 'block';
    document.getElementById('invoice-barcode-status').style.color = '#198754';
  }
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
  // Allow modal show briefly and then reset the guard
  try { window.__allowHsnModalShow = true; } catch (e) { }
  var hsnModal = new bootstrap.Modal(document.getElementById('hsnModal'), { backdrop: true });
  hsnModal.show();
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

// Defensive guard: block any accidental auto-show of the HSN modal
(function () {
  if (window.bootstrap && bootstrap.Modal && bootstrap.Modal.prototype) {
    const _origShow = bootstrap.Modal.prototype.show;
    window.__allowHsnModalShow = false;
    bootstrap.Modal.prototype.show = function () {
      try {
        const el = this._element || this._config?.target || null;
        if (el && el.id === 'hsnModal' && !window.__allowHsnModalShow) {
          console.log('Blocked automatic show of hsnModal');
          return; // prevent showing
        }
      } catch (e) { /* ignore */ }
      return _origShow.apply(this, arguments);
    };
  }
})();

// Ensure modal does not show leftover errors when opened; reveal only after a submit attempt
$('#addCustomerModal').on('show.bs.modal', function () {
  try {
    var $modal = $(this);
    var $mb = $modal.find('.modal-body');
    if (!$modal.data('customerFormSubmitted')) {
      $mb.find('.text-danger.small, .text-danger, .invalid-feedback, .alert.alert-danger').hide();
      $mb.find('*').filter(function () { return $(this).text().trim() === 'This field is required.'; }).hide();
    }
  } catch (e) { /* ignore */ }
});

document.addEventListener('DOMContentLoaded', function () {
  console.log("on document load");
  const duplicateBtn = document.querySelector('[data-bs-target="#confirmDuplicateModal"]');
  const modal = document.getElementById('confirmDuplicateModal');
  const orderNumberEl = document.getElementById('orderNumber');
  const hiddenOrderId = document.getElementById('hiddenOrderId');

  if (!duplicateBtn) return;

  duplicateBtn.addEventListener('click', function () {
    console.log("duplicate button vlivked");
    const orderId = this.getAttribute('data-order-id');
    const orderno = this.getAttribute('data-order-number');

    console.log("orderId:", orderId);
    hiddenOrderId.value = orderId;
    console.log("hiddenOrderId value:", hiddenOrderId);
    orderNumberEl.textContent = orderno;  // Format as needed
  });
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

  // Populate modal fields with customer shipping data
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
  if (saCountry) saCountry.value = s.shipping_country || '';
  if (saAddress1) saAddress1.value = s.shipping_address_line_1 || '';
  if (saAddress2) saAddress2.value = s.shipping_address_line_2 || '';
  if (saCity) saCity.value = s.shipping_city || '';
  if (saPostal) saPostal.value = s.shipping_postal_code || '';

  // Set state value - need to wait for Select2 initialization
  if (saState && s.shipping_state) {
    // If Select2 is initialized
    if (window.jQuery && $(saState).hasClass('select2-hidden-accessible')) {
      $(saState).val(s.shipping_state).trigger('change');
    } else {
      // Fallback for regular select
      saState.value = s.shipping_state;
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
        // Initialize Select2 and populate with customer data
        setTimeout(function () {
          initializeShippingStateDropdown();
          // Populate modal with customer shipping data
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
  applyInitialInvoiceFxState();
  if (window.forceDocumentCurrencyLocked) {
    setDocumentCurrencyLocked(true);
  }
  // Ensure exchange-rate UI visibility matches current currency selection on load
  try { updateBaseCurrencyVisibility(); } catch (e) { /* ignore if function missing */ }
  function qs(selector) { return document.querySelector(selector); }
  const select = qs('#id_customer') || qs('#customer_select') || qs('select[name="customer"]');
  const customerInfo = qs('#vendor-info');
  const billingName = qs('#billing-name');
  const billingAddress = qs('#billing-address');
  const billingContact = qs('#billing-contact');
  const billingGst = qs('#billing-gst');
  // GST treatment element removed; do not set GST Treatment here
  const placeOfSupplyDiv = qs('#place-of-supply');
  let lastLoadedCustomerId = null;

  function clearVendor() {
    if (!customerInfo) return;
    customerInfo.style.display = 'none';
    billingName.innerText = '';
    billingAddress.innerText = '';
    billingContact.innerText = '';
    billingGst.innerText = '';
    // clear any shipping info the user may have previously entered
    const shipNameEl = document.getElementById('shipping-name');
    const shipAddrEl = document.getElementById('shipping-address');
    const shipContactEl = document.getElementById('shipping-contact');
    if (shipNameEl) shipNameEl.innerText = '';
    if (shipAddrEl) shipAddrEl.innerText = 'New Address';
    if (shipContactEl) shipContactEl.innerText = '';
    // clear hidden shipping inputs so previous customer's data doesn't persist
    ['shipping_attention', 'shipping_email', 'shipping_phone', 'shipping_country', 'shipping_address1', 'shipping_address2', 'shipping_city', 'shipping_state', 'shipping_postal_code'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    if (placeOfSupplyDiv) placeOfSupplyDiv.innerText = '';
    if (typeof window.renderCustomerCreditSummary === 'function') {
      window.renderCustomerCreditSummary(null);
    }
    lastLoadedCustomerId = null;
    const docSel = document.getElementById('document_currency');
    const fxIn = document.getElementById('fx_rate_to_base');
    const fxDate = document.getElementById('fx_rate_date');

    if (docSel) {
      docSel.dataset.userSelected = '0';
      setDocumentCurrencyLocked(false);
      $(docSel).val('').trigger('change');
    }
    if (fxIn) fxIn.value = '';
    if (fxDate) fxDate.value = '';
  }

  // Clear inputs inside the Shipping Address modal so previous customer's values don't persist
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
  function loadVendorDetails(customerId) {
    console.log("loading customerdetails");
    // Avoid attempting to fetch details for the "+ New" pseudo-option which uses the
    // value 'new' — this would generate a 404 because there's no customer with id 'new'.
    if (!customerId || customerId === 'new') { clearVendor(); return; }
    var docSel = document.getElementById('document_currency');
    if (docSel && customerId !== lastLoadedCustomerId) {
      docSel.dataset.userSelected = '0';
    }
    lastLoadedCustomerId = customerId;
    const excludeInvoiceId = select ? (select.dataset.excludeInvoice || '') : '';
    const queryString = excludeInvoiceId ? `?exclude_invoice=${encodeURIComponent(excludeInvoiceId)}` : '';
    const url = `/sales/customer/${customerId}/detail/${queryString}`;
    console.log('Fetching vendor details from:', url);
    fetch(url)
      .then(r => {
        console.log('Fetch response status:', r.status);
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

  function applyCustomerPaymentTerms(data) {
    var terms = data && data.payment_terms ? data.payment_terms : null;
    var $payTerms = $('#pay-terms, select[name="payment_term"]').first();

    if (!$payTerms.length) {
      window.applyCustomerDefaultPaymentTerms = false;
      return;
    }

    var shouldApply = !!window.applyCustomerDefaultPaymentTerms || !$payTerms.val();
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

    window.applyCustomerDefaultPaymentTerms = false;
  }


  function fillVendor(data) {
    console.log('fillVendor 2 called with data:', data);
    if (!customerInfo) return;
    if (!data || data.error) {
      clearVendor();
      currentCustomerShippingData = null;
      return;
    }
    if (data.is_cash_customer) {
      // Hide detailed customer info but allow currency autofill to proceed
      if (customerInfo) customerInfo.style.display = 'none';
      currentCustomerShippingData = null;
    } else {
      customerInfo.style.display = 'block';
      //  FIX: Check if we have saved shipping data from the quotation first
      const hasSavedShipping = window.hasSavedShippingData;
      console.log('Has saved shipping from quotation:', hasSavedShipping);

      // Use saved shipping data if available, otherwise use customer's default.
      // If customer shipping is empty, default shipping to billing details.
      const savedShipping = normalizeShippingData(window.savedShippingData);
      const customerShipping = normalizeShippingData(data.shipping);
      if (hasSavedShipping && hasShippingDetails(savedShipping)) {
        currentCustomerShippingData = savedShipping;
        console.log('Using saved shipping from quotation:', currentCustomerShippingData);
      } else if (hasShippingDetails(customerShipping)) {
        currentCustomerShippingData = customerShipping;
        console.log('Using customer default shipping:', currentCustomerShippingData);
      } else {
        currentCustomerShippingData = buildShippingFromBilling(data.billing || {});
        console.log('Customer has no shipping, using billing as shipping:', currentCustomerShippingData);
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
      billingGst.innerText = b.gst_number ? ('Tax Number: ' + b.gst_number) : '';
      // Fill shipping info from customer data
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
      applyCustomerPaymentTerms(data);
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
      if (typeof window.renderCustomerCreditSummary === 'function') {
        window.renderCustomerCreditSummary(data.credit || null);
      }
    }
    // Auto-fill document currency and FX rate/date using currencies API
    try {
      var parts = window.location.pathname.split('/');
      var companyCode = parts[1] || '';
      // Try to derive customer id from API data, otherwise use the select value
      var customerIdForApi = (data && data.id) ? data.id : (select ? select.value : '');
      console.log('currency autofill: companyCode=', companyCode, 'customerIdForApi=', customerIdForApi);
      if (companyCode && customerIdForApi) {
        var apiUrl = '/' + companyCode + '/currencies/api/customer_rate/?customer_id=' + encodeURIComponent(customerIdForApi);
        fetch(apiUrl, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
          .then(function (r) { return r.json(); })
          .then(function (resp) {
            console.log('customer currency api response', apiUrl, resp);
            if (!resp || !resp.ok) {
              setDocumentCurrencyLocked(false);
              return;
            }
            try {
              var docSel = document.getElementById('document_currency');
              if (docSel) {
                var userOverrode = docSel.dataset.userSelected === '1';
                var preserveInitialFx = !!window.preserveInitialInvoiceFx;
                var editingExistingInvoice = !!window.isExistingInvoiceEdit;
                var shouldAutoFill = !userOverrode && !preserveInitialFx && !editingExistingInvoice && resp.currency_id;
                if (shouldAutoFill) {
                  var cid = resp.currency_id.toString();
                  var symbolFromResp = resp.currency_symbol || resp.currency_code || (docSel.dataset && docSel.dataset.baseSymbol) || DEFAULT_CURRENCY_SYMBOL;
                  var existingOption = docSel.querySelector('option[value="' + cid + '"]');
                  if (!existingOption) {
                    var opt = document.createElement('option');
                    opt.value = cid;
                    opt.text = resp.currency_code || resp.currency_symbol || cid;
                    opt.dataset.symbol = symbolFromResp;
                    docSel.appendChild(opt);
                    registerCurrencyOption(opt);
                  } else {
                    existingOption.dataset.symbol = symbolFromResp;
                    registerCurrencyOption(existingOption);
                  }

                  window.isAutoFillingCurrency = true;
                  function setDocCurrencyOnce() {
                    try { docSel.value = cid; } catch (e) { console.warn('could not set docSel.value', e); }
                    try { var ev = new Event('change'); docSel.dispatchEvent(ev); } catch (e) { console.warn('could not dispatch native change', e); }
                    try {
                      if (window.jQuery) {
                        var $sel = window.jQuery(docSel);
                        if ($sel && typeof $sel.val === 'function') {
                          $sel.val(cid).trigger('change');
                        }
                      }
                    } catch (e) { console.warn('could not trigger jQuery change', e); }
                  }
                  setDocCurrencyOnce();
                  setTimeout(function () {
                    try {
                      if (window.jQuery) {
                        var $sel = window.jQuery(docSel);
                        try { if ($sel.data('select2')) $sel.select2('destroy'); } catch (e) { }
                        try { $sel.select2({ placeholder: 'Select', allowClear: true, width: 'resolve' }); } catch (e) { }
                        try { $sel.val(cid).trigger('change'); } catch (e) { }
                      } else {
                        setDocCurrencyOnce();
                      }
                    } catch (e) { console.warn('reinit doc currency failed', e); }
                    finally {
                      window.isAutoFillingCurrency = false;
                      setDocumentCurrencyLocked(true);
                      // Update discount symbols and rebuild currency map after auto-fill completes
                      // BUT do NOT recalculate totals - discount values should stay the same
                      setTimeout(function () {
                        rebuildCurrencySymbolMap();
                        updateFlatDiscountSymbols();
                      }, 50);
                    }
                  }, 300);

                  var fxIn = document.getElementById('fx_rate_to_base');
                  var fxDate = document.getElementById('fx_rate_date');
                  // Overwrite FX rate when API provides one so conversion can run on customer change
                  if (fxIn && resp.rate) {
                    try {
                      if (fxIn.value != resp.rate) fxIn.value = resp.rate;
                      // Dispatch input event so listeners reprice rows
                      try { fxIn.dispatchEvent(new Event('input')); } catch (e) { $(fxIn).trigger('input'); }
                    } catch (e) { /* ignore */ }
                  }
                  if (fxDate && (resp.rate_effective_from || resp.date)) {
                    try { fxDate.value = resp.rate_effective_from || resp.date; } catch (e) { }
                  }
                  try {
                    var symInput = document.getElementById('document_currency_symbol');
                    if (!symInput) {
                      symInput = document.createElement('input');
                      symInput.type = 'hidden';
                      symInput.id = 'document_currency_symbol';
                      var formEl = document.querySelector('form');
                      if (formEl) formEl.appendChild(symInput);
                    }
                    if (resp.currency_symbol) symInput.value = resp.currency_symbol;
                    else if (resp.currency_code) symInput.value = resp.currency_code;
                  } catch (e) { console.warn('set doc currency symbol failed', e); }
                  // Ensure prices are refreshed after autofill completes
                  setTimeout(function () {
                    try {
                      if (typeof refreshPricesFromBase === 'function') refreshPricesFromBase();
                    } catch (e) { /* ignore */ }
                  }, 500);
                }
                else {
                  if (preserveInitialFx) {
                    applyInitialInvoiceFxState();
                    window.preserveInitialInvoiceFx = false;
                  }
                  if (editingExistingInvoice) {
                    applyInitialInvoiceFxState();
                  }
                  setDocumentCurrencyLocked(false);
                }
              }
            } catch (e) { console.warn('currency auto-fill error', e); }
          })
          .catch(function (err) {
            setDocumentCurrencyLocked(false);
            console.warn('currency api error', err);
          });
      }
    } catch (e) { /* ignore */ }
  }

  // Place of Supply is now auto-populated from customer data





  //uncommented on 10-2-26 by neha for loading customer details on select change and on page load if customer is already selected
  if (select) {
    select.addEventListener('change', function () {
      // Clear any shipping modal fields so they don't show previous customer's data
      try { clearShippingModal(); } catch (err) { console.warn('clearShippingModal failed', err); }
      window.applyCustomerDefaultPaymentTerms = true;
      loadVendorDetails(this.value);
    });

    // Also handle select2 selection event
    if (window.jQuery) {
      $(select).on('select2:select', function (e) {
        var id = $(this).val();
        window.applyCustomerDefaultPaymentTerms = true;
        if (id) loadVendorDetails(id);
      });

      // When Select2 dropdown is closed without a selection, hide customer info if no customer selected
      $(select).on('select2:close', function (e) {
        try {
          if (!$(this).val() || $(this).val() === '') {
            clearVendor();
          }
        } catch (err) { console.warn('Error handling select2:close', err); }
      });
      // When an option is unselected (clear), hide customer info immediately
      $(select).on('select2:unselect', function (e) {
        try { clearVendor(); } catch (err) { console.warn('Error handling select2:unselect', err); }
      });
    }
    // Load initial customer if present
    const init = select.value;
    if (init) loadVendorDetails(init);

    // If a new customer is created via the Add Customer modal, refresh details when modal closes
    try {
      const addCustomerModalEl = document.getElementById('addCustomerModal');
      if (addCustomerModalEl) {
        addCustomerModalEl.addEventListener('hidden.bs.modal', function () {
          try {
            // If a customer is selected (newly created option might be selected by other code), reload details
            if (select && select.value) {
              // ensure shipping modal fields are cleared before reloading details
              try { clearShippingModal(); } catch (err) { }
              loadVendorDetails(select.value);
            }
            else { clearVendor(); }
          } catch (err) { console.warn('Error reloading customer after modal close', err); }
        });
      }
    } catch (e) { /* ignore */ }
  }
});

// Show Add customer Modal on +New click
// document.addEventListener('DOMContentLoaded', function() {
//   var addVendorBtn = document.getElementById('addVendorBtn');
//   if (addVendorBtn) {
//     addVendorBtn.addEventListener('click', function() {
//       var modal = new bootstrap.Modal(document.getElementById('addVendorModal'));
//       modal.show();
//     });
//   }
// });

// customer Contact Add/Remove (delegated for modal + page forms)
// document.addEventListener('click', function(e) {
//   // Add contact - modal variant id or page variant id
//   if (e.target && (e.target.id === 'add-Vendor-contact' || e.target.id === 'add-contact')) {
//     // prefer modal container if present
//     let container = document.getElementById('customer-contact-persons-container') || document.getElementById('contact-persons-container') || document.getElementById('customer-contact-persons-container');
//     if (!container) return;
//     const row = document.createElement('div');
//     row.className = 'row contact-row mb-2';
//     row.innerHTML = `
//       <div class="col-md-4">
//         <input type="text" name="contact_name" class="form-control" placeholder="Name">
//       </div>
//       <div class="col-md-4">
//         <input type="email" name="contact_email" class="form-control" placeholder="Email">
//       </div>
//       <div class="col-md-3">
//         <input type="text" name="contact_phone" class="form-control" placeholder="Phone">
//       </div>
//       <div class="col-md-1">
//         <button type="button" class="btn btn-danger remove-contact">Delete</button>
//       </div>
//     `;
//     container.appendChild(row);
//   }
//   // Remove contact (works for modal and page)
//   if (e.target && e.target.classList && e.target.classList.contains('remove-contact')) {
//     const row = e.target.closest('.contact-row');
//     if (row) row.remove();
//   }
// });





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

  // Save new unit via AJAX
  // Save new unit via AJAX (company-prefixed URL + CSRF header)
  var pathParts = window.location.pathname.split('/');
  var companyCode = pathParts[1] || '';
  var ajaxUrl = '/' + companyCode + '/sales/add_unit/';

  // helper to read csrftoken from cookie
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
  $row.data('price_base', 0);
  $row.data('o_price_base', 0);
  setBasePriceDisplay($row, 0);

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
  
  // Initialize the default tax select for non-Indian companies
  if (!COMPANY_IS_INDIA) {
    // Initialize default tax select with Select2
    if (!$('#item_default_tax_select').hasClass('select2-hidden-accessible')) {
      $('#item_default_tax_select').select2({
        placeholder: 'Choose tax rate',
        allowClear: true,
        minimumInputLength: 0,
        dropdownParent: $('#addItemModal'),
        ajax: {
          url: '/Items/tax/',
          dataType: 'json',
          delay: 250,
          data: function(params) {
            return { q: params.term };
          },
          processResults: function(data) {
            let results = data.map(function(item) {
              return {
                id: item.id,
                text: item.taxname || item.name
              };
            });
            return { results: results };
          }
        }
      });
    }
  }
  
  // Call the visibility update function
  if (typeof updateTaxFieldsVisibility === 'function') {
    updateTaxFieldsVisibility();
  }
});



function autoGenerateCustomerCode(name) {

  if (!name || name.trim().length === 0) return;
  const csrf = $('[name=csrfmiddlewaretoken]').first().val();
  console.log('CSRF token found:', csrf);         // ← is it undefined?
  console.log('Name being sent:', name.trim());   // ← is name correct?


  // Send AJAX request to save item (company-prefixed URL)
  var pathParts = window.location.pathname.split('/');
  var companyCode = pathParts[1] || '';
  var ajaxUrl = '/' + companyCode + '/customer/generate-customer-code/';


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
        $('#addCustomerModal').find('input[name="customer_code"]').val(data.code);
        console.log('Auto-generated customer code:', data.code);
      }
      else {
        $('#addCustomerModal').find('input[name="customer_code"]').val('');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      $('#addCustomerModal').find('input[name="customer_code"]').val('');
    });
}
// Regenerate customer code on button click (if you have a refresh/generate button next to the field)
$(document).on('click', '#addCustomerModal .generate-customer-code-btn', function (e) {
  e.preventDefault();
  autoGenerateCustomerCode();
});


// Regenerate customer code when company_name or first_name changes inside the customer modal
$(document).on('input', '#addCustomerModal input[name="company_name"]', function () {
  var name = $(this).val().trim();
  if (name.length >= 1) {
    autoGenerateCustomerCode(name);
  }
});


$(document).on('input', '#addCustomerModal input[name="first_name"]', function () {
  var name = $(this).val().trim();
  if (name.length >= 1) {
    autoGenerateCustomerCode(name);
  }
});

$(document).on('input', '#addCustomerModal input[name="first_name"]', function () {
  // Only use first_name if company_name is empty
  var companyName = $('#addCustomerModal input[name="company_name"]').val().trim();
  if (!companyName) {
    var name = $(this).val().trim();
    if (name.length >= 1) {
      autoGenerateCustomerCode(name);
    }
  }
});
