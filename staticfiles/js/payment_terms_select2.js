(function ($) {
  if (!$ || !$.fn || !$.fn.select2) {
    return;
  }

  const paymentTermsSelector = 'select[name="payment_terms"]';
  const modalSelector = '#paymentTermsModal';
  let deletedTerms = [];

  function withCompanyPrefix(path) {
    const segments = window.location.pathname.split('/').filter(Boolean);
    const firstSegment = segments[0] || '';

    if (firstSegment && firstSegment !== 'PayTerms') {
      return `/${firstSegment}${path}`;
    }

    return path;
  }

  function getTermText(term) {
    const days = term.days || 0;
    return `${term.name} (${days} days)`;
  }

  function escapeAttribute(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function openPaymentTermsModal($select) {
    const modalEl = document.querySelector(modalSelector);
    if (!modalEl || !window.bootstrap) {
      return;
    }

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
    $select.val(null).trigger('change');
  }

  function loadPaymentTerms() {
    $.ajax({
      url: withCompanyPrefix('/PayTerms/payterm_list/'),
      type: 'GET',
      dataType: 'json',
      success: function (data) {
        const $tbody = $(`${modalSelector} table tbody`);
        $tbody.empty();
        deletedTerms = [];

        data.forEach(function (term) {
          const row = `
            <tr data-id="${term.id}">
              <td><input type="text" class="form-control term-name" value="${escapeAttribute(term.name)}"></td>
              <td><input type="number" class="form-control term-days" value="${term.days || 0}"></td>
              <td class="text-center">
                <button type="button" class="btn btn-danger btn-sm delete-row" style="display:none;">Delete</button>
              </td>
            </tr>`;
          $tbody.append(row);
        });
      },
      error: function () {
        console.error('Failed to load payment terms');
      }
    });
  }

  function refreshPaymentTermsSelect(lastCreatedId, lastCreatedName) {
    const $select = $(paymentTermsSelector);

    if (lastCreatedId && lastCreatedName) {
      const text = lastCreatedName;
      const option = new Option(text, lastCreatedId, true, true);
      $select.append(option).trigger('change');
      return;
    }

    $select.val(null).trigger('change');
  }

  function initPaymentTermsSelect() {
    const $select = $(paymentTermsSelector);

    if (!$select.length) {
      return;
    }

    if ($select.hasClass('select2-hidden-accessible')) {
      $select.select2('destroy');
    }

    $select.select2({
      placeholder: 'Select payment terms',
      allowClear: true,
      width: 'resolve',
      minimumInputLength: 0,
      ajax: {
        url: withCompanyPrefix('/PayTerms/payterm_list/'),
        dataType: 'json',
        processResults: function (data) {
          const results = data.map(function (term) {
            return {
              id: term.id,
              text: getTermText(term)
            };
          });

          results.push({
            id: 'new',
            text: '+ New',
            isNew: true
          });

          return { results: results };
        },
        cache: true
      }
    });

    $select.off('select2:select.paymentTerms').on('select2:select.paymentTerms', function (e) {
      const data = e.params.data;

      if (data && data.isNew) {
        openPaymentTermsModal($(this));
      }
    });
  }

  $(function () {
    initPaymentTermsSelect();

    const modalEl = document.querySelector(modalSelector);
    if (modalEl) {
      modalEl.addEventListener('show.bs.modal', loadPaymentTerms);
    }

    $(document).off('click.paymentTermsDelete', `${modalSelector} .delete-row`);
    $(document).on('click.paymentTermsDelete', `${modalSelector} .delete-row`, function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();

      const id = $(this).closest('tr').data('id');
      if (id) {
        deletedTerms.push(id);
      }

      $(this).closest('tr').remove();
    });

    $(document).off('click.paymentTermsAdd', `${modalSelector} #addNew`);
    $(document).on('click.paymentTermsAdd', `${modalSelector} #addNew`, function (event) {
      event.preventDefault();

      const newRow = `
        <tr data-id="">
          <td><input type="text" class="form-control term-name" placeholder="Term Name"></td>
          <td><input type="number" class="form-control term-days" placeholder="Number of days"></td>
          <td class="text-center">
            <button type="button" class="btn btn-danger btn-sm delete-row" style="display:none;">Delete</button>
          </td>
        </tr>`;

      $(`${modalSelector} table tbody`).append(newRow);
    });

    $(document).off('click.paymentTermsSave', `${modalSelector} .save-payment-terms`);
    $(document).on('click.paymentTermsSave', `${modalSelector} .save-payment-terms`, function (event) {
      event.preventDefault();

      const terms = [];

      $(`${modalSelector} table tbody tr`).each(function () {
        const id = $(this).attr('data-id');
        const name = $(this).find('.term-name').val();
        const days = $(this).find('.term-days').val();

        if (name && days !== '') {
          terms.push({
            id: id,
            name: name,
            days: parseInt(days, 10)
          });
        }
      });

      $.ajax({
        url: withCompanyPrefix('/PayTerms/save_payterms/'),
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ terms: terms, deleted: deletedTerms }),
        success: function (response) {
          deletedTerms = [];
          refreshPaymentTermsSelect(response.last_created_id, response.last_created_name);

          const modalEl = document.querySelector(modalSelector);
          if (modalEl && window.bootstrap) {
            bootstrap.Modal.getOrCreateInstance(modalEl).hide();
          }

          showToast('Payment terms saved successfully', 'success');
        },
        error: function () {
          alert('Error saving payment terms');
        }
      });
    });
  });
})(window.jQuery);
