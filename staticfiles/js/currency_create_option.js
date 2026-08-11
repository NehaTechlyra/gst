(function (window, document, $) {
  'use strict';

  if (!$ || !window.bootstrap) {
    return;
  }

  const NEW_CURRENCY_VALUE = '__new_currency__';
  const NEW_CURRENCY_LABEL = '+ New Currency';
  const MODAL_ID = 'currency-create-modal';
  let activeCurrencySelect = null;

  function getCsrfToken() {
    const cookieMatch = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (cookieMatch && cookieMatch[1]) {
      return decodeURIComponent(cookieMatch[1]);
    }

    const tokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return tokenInput ? tokenInput.value : '';
  }

  function getCompanyCode() {
    const parts = window.location.pathname.split('/').filter(Boolean);
    return parts.length > 0 ? parts[0] : '';
  }

  function getCurrencyAddUrl() {
    const companyCode = getCompanyCode();
    return companyCode ? '/' + companyCode + '/currencies/add/' : '/currencies/add/';
  }

  function buildModalHtml() {
    return [
      '<div class="modal fade" id="' + MODAL_ID + '" tabindex="-1" aria-hidden="true">',
      '  <div class="modal-dialog modal-dialog-centered modal-lg">',
      '    <div class="modal-content">',
      '      <form id="currency-create-form" novalidate>',
      '        <div class="modal-header">',
      '          <h5 class="modal-title">Add New Currency</h5>',
      '          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>',
      '        </div>',
      '        <div class="modal-body">',
      '          <div class="alert alert-danger d-none" id="currency-create-error"></div>',
      '          <div class="row g-3">',
      '            <div class="col-md-4">',
      '              <label class="form-label">Code <span class="text-danger">*</span></label>',
      '              <input type="text" class="form-control" name="code" maxlength="3" placeholder="USD" required>',
      '            </div>',
      '            <div class="col-md-4">',
      '              <label class="form-label">Symbol</label>',
      '              <input type="text" class="form-control" name="symbol" maxlength="8" placeholder="$">',
      '            </div>',
      '            <div class="col-md-4">',
      '              <label class="form-label">Decimal places</label>',
      '              <input type="number" class="form-control" name="decimal_places" min="0" max="6" value="2">',
      '            </div>',
      '            <div class="col-md-12">',
      '              <label class="form-label">Name</label>',
      '              <input type="text" class="form-control" name="name" maxlength="80" placeholder="US Dollar">',
      '            </div>',
      '            <div class="col-md-12">',
      '              <label class="form-label">Format</label>',
      '              <select class="form-select" name="display_format">',
      '                <option value="1,234.56" selected>1,234.56</option>',
      '                <option value="1.234,56">1.234,56</option>',
      '                <option value="1 234,56">1 234,56</option>',
      '              </select>',
      '            </div>',
      '            <div class="col-md-12">',
      '              <div class="form-check mt-1">',
      '                <input class="form-check-input" type="checkbox" name="is_base" id="currency-create-is-base">',
      '                <label class="form-check-label" for="currency-create-is-base">Make this the base currency</label>',
      '              </div>',
      '            </div>',
      '          </div>',
      '        </div>',
      '        <div class="modal-footer">',
      '          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>',
      '          <button type="submit" class="btn btn-primary" id="currency-create-save">Save Currency</button>',
      '        </div>',
      '      </form>',
      '    </div>',
      '  </div>',
      '</div>',
    ].join('');
  }

  function getOrCreateModal() {
    let modalEl = document.getElementById(MODAL_ID);
    if (modalEl) {
      return modalEl;
    }

    document.body.insertAdjacentHTML('beforeend', buildModalHtml());
    modalEl = document.getElementById(MODAL_ID);

    const form = modalEl.querySelector('#currency-create-form');
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      saveCurrency();
    });

    modalEl.addEventListener('hidden.bs.modal', function () {
      const errorBox = modalEl.querySelector('#currency-create-error');
      if (errorBox) {
        errorBox.classList.add('d-none');
        errorBox.textContent = '';
      }
      const formEl = modalEl.querySelector('#currency-create-form');
      if (formEl) {
        formEl.reset();
      }
    });

    return modalEl;
  }

  function showModalError(message) {
    const modalEl = getOrCreateModal();
    const errorBox = modalEl.querySelector('#currency-create-error');
    if (!errorBox) {
      alert(message);
      return;
    }
    errorBox.textContent = message;
    errorBox.classList.remove('d-none');
  }

  function resetCurrencySelect($select) {
    const previousValue = $select.data('currency-last-valid');
    $select.data('currency-resetting', true);
    $select.val(previousValue || '');
    $select.trigger('change');
    window.setTimeout(function () {
      $select.data('currency-resetting', false);
    }, 0);
  }

  function setActiveSelectFromModal(currencyData) {
    const newValue = String(currencyData.code || currencyData.display || currencyData.id || '');
    const newLabel = currencyData.display || currencyData.code || newValue;

    $('select[name="currency"]').each(function () {
      const $select = $(this);
      if (!$select.length) {
        return;
      }

      const hasOption = $select.find('option').filter(function () {
        return String(this.value) === newValue;
      }).length > 0;
      if (!hasOption) {
        $select.append(new Option(newLabel, newValue, false, false));
      }

      if (activeCurrencySelect && this === activeCurrencySelect) {
        $select.data('currency-last-valid', newValue);
        $select.val(newValue);
        $select.trigger('change');
      }
    });
  }

  function saveCurrency() {
    const modalEl = getOrCreateModal();
    const formEl = modalEl.querySelector('#currency-create-form');
    const saveBtn = modalEl.querySelector('#currency-create-save');
    if (!formEl || !saveBtn) {
      return;
    }

    const errorBox = modalEl.querySelector('#currency-create-error');
    const data = $(formEl).serialize();

    if (errorBox) {
      errorBox.classList.add('d-none');
      errorBox.textContent = '';
    }

    saveBtn.disabled = true;
    const originalText = saveBtn.textContent;
    saveBtn.textContent = 'Saving...';

    $.ajax({
      url: getCurrencyAddUrl(),
      method: 'POST',
      data: data,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCsrfToken(),
      },
    })
      .done(function (response) {
        if (response && response.success) {
          setActiveSelectFromModal(response);
          bootstrap.Modal.getOrCreateInstance(modalEl).hide();
          if (typeof window.showToast === 'function') {
            window.showToast('Currency saved', 'success');
          }
          return;
        }

        showModalError((response && response.error) || 'Unable to save currency.');
      })
      .fail(function (xhr) {
        const message = (xhr.responseJSON && (xhr.responseJSON.error || xhr.responseJSON.message)) ||
          'Unable to save currency.';
        showModalError(message);
      })
      .always(function () {
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
      });
  }

  function openCurrencyModal(selectEl) {
    activeCurrencySelect = selectEl;
    const modalEl = getOrCreateModal();
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

    const formEl = modalEl.querySelector('#currency-create-form');
    if (formEl) {
      formEl.reset();
      const codeInput = formEl.querySelector('input[name="code"]');
      if (codeInput) {
        window.setTimeout(function () {
          codeInput.focus();
        }, 150);
      }
    }

    modal.show();
  }

  function bindCurrencySelects() {
    $('select[name="currency"]').each(function () {
      const $select = $(this);
      const currentValue = $select.val();
      if (currentValue && currentValue !== NEW_CURRENCY_VALUE) {
        $select.data('currency-last-valid', currentValue);
      }
    });

    $(document).on('focus mousedown select2:open', 'select[name="currency"]', function () {
      const $select = $(this);
      const currentValue = $select.val();
      if (currentValue && currentValue !== NEW_CURRENCY_VALUE) {
        $select.data('currency-last-valid', currentValue);
      }
    });

    $(document).on('change', 'select[name="currency"]', function () {
      const $select = $(this);
      if ($select.data('currency-resetting')) {
        return;
      }

      const value = $select.val();
      if (value === NEW_CURRENCY_VALUE) {
        const previousValue = $select.data('currency-last-valid') || '';
        openCurrencyModal(this);
        resetCurrencySelect($select);
        $select.data('currency-last-valid', previousValue);
        return;
      }

      if (value) {
        $select.data('currency-last-valid', value);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindCurrencySelects);
  } else {
    bindCurrencySelects();
  }
})(window, document, window.jQuery);
