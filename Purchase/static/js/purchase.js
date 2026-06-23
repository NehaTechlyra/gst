// purchase.js
// author sreevidya
console.log("purchase.js loaded ✅");
const form = document.getElementById('purchase-form');
let lastVendorSearchTerm = '';

function applyVendorPaymentTermsFromSelectData(data) {
  var $payTerms = $('#pay-terms, select[name="payment_term"]').first();
  if (!$payTerms.length || !data) {
    return;
  }

  if (data.payment_terms_id) {
    var label = data.payment_terms_name || data.payment_terms_id;
    if (data.payment_terms_days !== null && data.payment_terms_days !== undefined && data.payment_terms_name) {
      label = data.payment_terms_name + ' (' + data.payment_terms_days + ' days)';
    }
    $payTerms.find('option[value="' + data.payment_terms_id + '"]').remove();
    $payTerms.append(new Option(label, data.payment_terms_id, true, true)).trigger('change');
  } else {
    $payTerms.val(null).trigger('change');
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

    var paymentModalEl = document.getElementById('paymentTermsModal');
    if (paymentModalEl) {
      var paymentModal = bootstrap.Modal.getOrCreateInstance(paymentModalEl);
      paymentModal.show();
    }

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

// Use native Bootstrap 5 event listener to load payment terms when modal shows
var paymentTermsModalEl = document.getElementById('paymentTermsModal');
if (paymentTermsModalEl) {
  paymentTermsModalEl.addEventListener('show.bs.modal', loadPaymentTerms);
}

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



// Add new row on Add New button click
$('#addNew').on('click', function () {
  let newRow = `<tr data-id="">
      <td><input type="text" class="form-control term-name" placeholder="Term Name"></td>
      <td><input type="number" class="form-control term-days" placeholder="Number of days"></td>
      <td class="text-center">
        <button type="button" class="btn btn-danger btn-sm delete-row" style="display:none;">Delete</button>
      </td>
    </tr>`;
  $('#paymentTermsModal table tbody').append(newRow);
});


// Save button ajax save all changes
$('#paymentTermsModal .btn-primary[type="button"]').on('click', function (e) {
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
    url: '/PayTerms/save_payterms/',  // Your new backend save endpoint
    method: 'POST',
    contentType: 'application/json',
    data: JSON.stringify({ terms: terms, deleted: deletedTerms }),
    success: function (response) {
      alert("Payment terms saved successfully");
      deletedTerms = [];
    },
    error: function () {
      alert("Error saving payment terms");
    }
  });

});


$('#vendor_select').select2({
  placeholder: 'Search or select a vendor',
  allowClear: true,
  minimumInputLength: 0,
  ajax: {
    url: '/Items/vendor/',
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
      return { results: results };
    },
    cache: true
  }
});

// Add "+ New" button in Select2 dropdown footer
$('#vendor_select').on('select2:open', function () {
  const $dropdown = $('.select2-dropdown');
  if ($dropdown.find('.vendor-add-footer').length === 0) {
    $dropdown.append(`
          <div class="vendor-add-footer" style="padding:8px; border-top:1px solid #eee; background:#f9f9f9; text-align:center; cursor:pointer;">
            <button type="button" class="btn btn-primary btn-sm" style="width:100%;">+ Add Vendor</button>
          </div>
        `);
    $dropdown.find('.vendor-add-footer button').on('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      $('#vendor_select').select2('close');
      $.get('/Items/vendor_createform/', function (formHtml) {
        $('#vendorCreateModal .modal-body').html(formHtml);
        // Show using Bootstrap 5 Modal API
        var vendorModalEl = document.getElementById('vendorCreateModal');
        if (vendorModalEl) {
          var vendorModal = bootstrap.Modal.getOrCreateInstance(vendorModalEl);
          vendorModal.show();
        }
        // Initialize contact-person formset inside injected HTML: ensure one empty row by default
        try {
          var $modalBody = $('#vendorCreateModal .modal-body');
          var $totalForms = $modalBody.find('#id_contactperson-TOTAL_FORMS');
          var $container = $modalBody.find('#contact-persons-container');
          var tpl = $modalBody.find('#empty-form-template').html();
          if ($totalForms.length && tpl) {
            var total = parseInt($totalForms.val() || '0');
            var existing = $container.find('.contact-row').length;
            if (total === 0 && existing === 0) {
              var newHtml = tpl.replace(/__prefix__/g, 0);
              $container.append(newHtml);
              $totalForms.val(1);
            }
          }
        } catch (err) {
          console.warn('Could not init contact-person formset:', err);
        }
      }).fail(function () {
        alert('Failed to load vendor form');
      });
    });
  }
});






$('#item_select').select2({
  placeholder: '',
  allowClear: true,
  minimumInputLength: 1,
  ajax: {
    url: '/purchase/get_item/',
    dataType: 'json',
    delay: 250,
    data: function (params) {
      return { q: params.term };
    },
    processResults: function (data) {
      let results = data.map(function (item) {
        return {
          id: item.id, text: item.name, description: item.sell_desc,
          price: item.sl_price, uom: item.unit
        };
      });
      results.push({
        id: 'new',
        text: '+ New',
        isNew: true // custom flag to mark special option
      });
      console.log("this working");
      return { results: results };
    },
    cache: true
  }
});

$('#item_select').on('select2:select', function (e) {
  var data = e.params.data;
  if (data.isNew) {
    saveFormData();

    var currentUrl = window.location.href; // remember current page
    // redirect to vendor create page, pass current page as 'next'
    window.location.href = '/Items/add_item/?next=' + encodeURIComponent(currentUrl);
  }

  // Save data periodically or on input changes (optional)
  form.addEventListener('input', saveFormData);

  // Clear saved data on successful submission
  form.addEventListener('submit', () => {
    sessionStorage.removeItem('savedPurchaseForm');
  });
});


$('#items-table').on('select2:select', '.item-select', function (e) {
  let data = e.params.data;
  let $row = $(this).closest('tr');

  if (data.isNew) {
    alert("Open item creation modal here!");
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
    $oPriceInput.val(parseFloat(data.o_price) || 0);
    console.log("Set o_price to:", $oPriceInput.val());
  } else {
    console.warn("No .o_price input found in this row", $row.html());
  }




  $row.find('.price').val(data.price || 0);//seting price of item in the price field

  $row.find('.qty').val(1);

  // set tax if available
  let $taxSelect = $row.find('.tax-select');
  $taxSelect.empty();
  if (data.tax_id) {
    // let newOption = new Option(data.tax_name, data.tax_id, true, true);
    // $taxSelect.append(newOption).trigger('change');
    // $taxSelect.data('rate', data.tax_rate || 0);
    let $taxSelect = $row.find('.tax-select');
    // Create option with tax rate
    let newOption = new Option(data.tax_name, data.tax_id, true, true);
    $(newOption).data('rate', data.tax_rate || 0);   // ✅ attach tax rate
    $taxSelect.append(newOption).trigger('change');
  } else {
    $taxSelect.data('rate', 0);
  }

  updateRowAmount($row);
  calculateTotals();
});


function initItemSelect($el) {
  $el.select2({
    placeholder: 'Select Item',
    allowClear: true,
    minimumInputLength: 1,
    // multiple: false,              // ✅ ensure single select
    // closeOnSelect: true,          // ✅ close dropdown when selected
    ajax: {
      url: '/purchase/get_item/',
      dataType: 'json',
      delay: 250,
      data: params => ({ q: params.term }),
      processResults: data => ({
        results: data.map(item => ({
          id: item.id + '_' + (item.barcode || ''),
          text: item.name + ' ' + item.unit,
          description: item.sell_desc,
          price: item.sl_price,
          gstinclude: item.gstinclude,
          o_price: item.o_price,

          uom: item.unit,
          tax_id: item.tax_id,
          tax_name: item.tax_name,
          tax_rate: item.tax_rate
        })).concat([{ id: 'new', text: '+ New', isNew: true }])
      })
    }
  });

}


initItemSelect($('.item-select'));


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

  let gstval = $row.find('.gstinclude').val();
  let opriceval = parseFloat($row.find('.o_price').val()) || 0;

  console.log("gst included:" + gstval);


  let baseAmount = qty * price;

  let taxRate = parseFloat($row.find('.tax-select').data('rate')) || 0;

  let discount = parseFloat($row.find('.item-discount').val()) || 0;
  let discountType = $row.find('.discount-type').val(); // 'flat' or 'percent'

  // Apply discount based on type
  let discountedAmount;
  if (discountType === 'percent') {
    discountedAmount = baseAmount - (baseAmount * discount / 100);
  } else {
    discountedAmount = baseAmount - discount;
  }
  if (discountedAmount < 0) discountedAmount = 0;

  // let taxAmount = baseAmount * (taxRate / 100);
  let taxAmount = discountedAmount * (taxRate / 100);
  console.log("taxAmount" + taxAmount);
  let finalAmount;
  if (gstval == 'true') {
    finalAmount = baseAmount;

  }
  else {
    finalAmount = baseAmount + taxAmount;

  }

  // let finalAmount = baseAmount + taxAmount;
  console.log("finalAmount" + finalAmount);


  $row.find('.amount').text('₹' + finalAmount.toFixed(2));

  // Save values for totals
  $row.data({
    // baseAmount: baseAmount,
    baseAmount: discountedAmount,

    taxAmount: taxAmount,
    finalAmount: finalAmount
  });
}



function calculateTotals() {
  let subtotal = 0;
  let allitmtotal = 0;
  let totalTax = 0;
  let totalDiscount = 0; // Track total item-level discount


  document.querySelectorAll("#items-table tbody tr").forEach(function (row) {
    let qty = parseFloat(row.querySelector(".qty").value) || 0;
    let price = parseFloat(row.querySelector(".price").value) || 0;
    let gstInput = row.querySelector(".gstinclude");
    let gstval = gstInput ? gstInput.value : '';
    console.log("gstval:" + gstval);
    // let gstval = row.querySelector(".gstinclude").value;
    // let oPriceInput = row.querySelector(".o_price");
    // let opriceval = oPriceInput ? parseFloat(oPriceInput.value) : 0;
    let oPriceInput = row.querySelector(".o_price");
    let opriceval = oPriceInput && oPriceInput.value ? parseFloat(oPriceInput.value) || 0 : 0;

    let baseAmount = qty * price;
    console.log("baseAmount1" + baseAmount);

    allitmtotal += baseAmount;
    console.log("allitmtotal1" + allitmtotal);


    // Item-level discount
    let discount = parseFloat($(row).find(".item-discount").val()) || 0;
    let discountType = $(row).find(".discount-type").val();
    let discountedAmount;
    if (discountType === 'percent') {
      discountedAmount = baseAmount - (baseAmount * discount / 100);
    } else {
      discountedAmount = baseAmount - discount;
    }
    if (discountedAmount < 0) discountedAmount = 0;

    totalDiscount += baseAmount - discountedAmount;

    // tax-select handling
    let $taxSelect = $(row).find(".tax-select");
    let taxRate = 0;

    if ($taxSelect.length) {
      let selected = $taxSelect.find(":selected");
      if (selected.length) {
        taxRate = parseFloat($(selected).data("rate")) || 0;
      }
    }
    console.log("discountedAmount1" + discountedAmount);
    let taxAmount = (discountedAmount * taxRate) / 100;

    console.log("taxAmount1" + taxAmount);

    let rowTotal;
    if (gstval == 'true') {
      rowTotal = discountedAmount;

    }
    else {
      rowTotal = discountedAmount + taxAmount;

    }
    console.log("discountedAmount1" + discountedAmount);
    // let rowTotal = discountedAmount  + taxAmount;
    console.log("rowTotal" + rowTotal);

    // update row amount cell
    row.querySelector(".amount").innerText = "₹" + rowTotal.toFixed(2);

    subtotal += discountedAmount;
    totalTax += taxAmount;
  });

  let total = subtotal + totalTax;
  console.log("allitmtotal" + allitmtotal);
  document.getElementById("subtotal").innerText = "₹" + allitmtotal.toFixed(2);

  // document.getElementById("subtotal").innerText = "₹" + subtotal.toFixed(2);
  document.getElementById("tax-total").innerText = "₹" + totalTax.toFixed(2);
  $('#discount-amount').text(totalDiscount.toFixed(2));


  // Apply Grand Discount
  let grandDiscount = parseFloat($('#grand-discount').val()) || 0;
  let grandDiscountType = $('#grand-discount-type').val();
  let grandDiscountValue = 0;

  if (grandDiscountType === 'percent') {
    grandDiscountValue = total * (grandDiscount / 100);
  } else {
    grandDiscountValue = grandDiscount;
  }
  if (grandDiscountValue > total) grandDiscountValue = total; // prevent negative
  // $('#discount-amount').text(discountValue.toFixed(2));
  let grandTotal = total - grandDiscountValue;
  let TotalDiscount = grandDiscountValue + totalDiscount;
  $('#discount-amount').text(TotalDiscount.toFixed(2));

  document.getElementById("grand-total").innerText = "₹" + grandTotal.toFixed(2);
  document.getElementById('grandTotal').value = grandTotal.toFixed(2);

}


// --- On qty or price change ---
$('#items-table').on('input change', '.qty, .price, .item-discount, .discount-type', function () {
  let $row = $(this).closest('tr');
  updateRowAmount($row);
  calculateTotals();
});

$('#grand-discount, #grand-discount-type').on('input change', calculateTotals);

document.querySelectorAll('input[type="number"]').forEach(input => {
  input.addEventListener('focus', function () {
    this.select();
  });
});

document.addEventListener("DOMContentLoaded", function () {
  // restoreFormData();


  const vendorSelect = document.getElementById('vendor_select');
  const payTermsSelect = document.getElementById('pay-terms');
  const itemsTable = document.getElementById('items-table');
  const saveButton = document.querySelector('button[type="submit"].btn.btn-primary');



  function validateForm() {
    let isValid = true;

    // 1. Vendor selected (not empty/null)
    if (!vendorSelect.value) {
      console.log("no vendor is selected");

      isValid = false;
    }

    // 2. Payment term selected
    if (!payTermsSelect.value) {
      console.log("no pay term is selected");

      isValid = false;
    }

    // 3. At least one item row with valid item selected
    const rows = itemsTable.querySelectorAll('tbody tr');
    if (rows.length === 0) {
      console.log("row length 0");
      isValid = false;
    } else {
      console.log("row length 1");

      // Check that each row has item selected
      for (const row of rows) {
        const itemSelect = row.querySelector('select.item-select');
        const qtyInput = row.querySelector('input.qty');
        const priceInput = row.querySelector('input.price');

        if (!itemSelect || !itemSelect.value || itemSelect.value === "") {
          console.log("no item is selected");

          isValid = false;
          break;
        }
        console.log("item is selected");

        // 4. Quantity and price minimum 1
        const qty = parseFloat(qtyInput.value);
        const price = parseFloat(priceInput.value);

        if (isNaN(qty) || qty < 1 || isNaN(price) || price < 1) {
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
  });

  // payTermsSelect.addEventListener('change', validateForm);
  $('#pay-terms').on('select2:select select2:unselect', function () {
    validateForm();
  });


  // Delegate event listener for item select, qty, and price changes inside items table
  // itemsTable.addEventListener('change', function(e) {
  //   if (e.target.classList.contains('item-select') || e.target.classList.contains('qty') || e.target.classList.contains('price')) {
  //     validateForm();
  //   }
  // });
  $('#items-table').on('select2:select select2:unselect', '.item-select', function () {
    validateForm();
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
form.addEventListener('submit', function () {
  sessionStorage.removeItem('savedPurchaseForm');
});



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

  sessionStorage.setItem('savedPurchaseForm', JSON.stringify(data));
}
function restoreFormData() {
  let saved = sessionStorage.getItem('savedPurchaseForm');
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
                <tr>
                    <td><select name="items[${idx}][id]" class="item-select"></select></td>
                    <td><input type="text" name="items[${idx}][description]" class="desc"></td>
                    <td><input type="number" name="items[${idx}][qty]" min="0" class="qty"></td>
                    <td><input type="number" name="items[${idx}][price]" min="0" step="0.01" class="price"></td>
                    <td style="display:none;"><input type="hidden" name="items[${idx}][gstinclude]" class="gstinclude"></td>

                    <td style="display:none;"><input type="hidden" name="items[${idx}][o_price]" min="0" step="0.01" class="o_price"></td>
                    <td><select name="items[${idx}][tax]" class="tax-select"></select></td>
                    <td style="display:flex;gap:2px;">
                        <input type="number" class="item-discount" name="items[${idx}][discount]" min="0" step="0.01">
                        <select class="discount-type rupee-sign" name="items[${idx}][discount_type]">
                            <option value="flat" class="amount">&#8377;</option>
                            <option value="percent">%</option>
                        </select>
                    </td>
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
      initItemSelect($row.find('select.item-select'));
      initTaxSelect($row.find('select.tax-select'));
    });
  }

  calculateTotals();
}


$(document).on('submit', '#vendorCreateForm', function (e) {
  e.preventDefault();
  var $form = $(this);

  $.ajax({
    method: 'POST',
    url: $(this).attr('action') || '/Items/add_vendor/',
    data: $form.serialize(),
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    success: function (response) {
      if (response.success) {
        // close modal using Bootstrap 5 API
        var modalEl = document.getElementById('vendorCreateModal');
        if (modalEl) {
          var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.hide();
        }

        // add vendor to select2 and select it
        var newOption = new Option(response.name, response.id, true, true);
        $('#vendor_select').append(newOption).trigger('change');
      }
    },
    error: function (xhr) {
      // If server returned rendered partial (HTML), replace modal body so per-field errors appear
      if (xhr.responseText && xhr.getResponseHeader('Content-Type') && xhr.getResponseHeader('Content-Type').indexOf('text/html') !== -1) {
        $('#vendorCreateModal .modal-body').html(xhr.responseText);
        return;
      }
      var errors = xhr.responseJSON?.errors || {};
      var errorMsg = 'Error creating vendor';
      for (var field in errors) {
        if (errors[field] && errors[field].length > 0) {
          // errors[field] might be a list or nested for formset; pick first string
          var val = errors[field];
          if (Array.isArray(val)) {
            errorMsg = val[0];
          } else if (typeof val === 'object') {
            // nested errors like {'contactperson': [ {...} ]}
            errorMsg = 'Please correct the highlighted fields';
          } else {
            errorMsg = String(val);
          }
          break;
        }
      }
      $('#vendorCreateModal .modal-body').prepend(
        `<div class="alert alert-danger">${errorMsg}</div>`
      );
    }
  });
});
// Click handler for Save Vendor button (prevents full-page submit if form submit isn't intercepted)
$(document).on('click', '#vendorCreateModal .btn-save-vendor', function (e) {
  e.preventDefault();
  var $modal = $('#vendorCreateModal');
  var $form = $modal.find('#vendorCreateForm');
  if (!$form || $form.length === 0) return;

  $.ajax({
    method: 'POST',
    url: $form.attr('action') || '/Items/add_vendor/',
    data: $form.serialize(),
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    success: function (response) {
      if (response.success) {
        var modalEl = document.getElementById('vendorCreateModal');
        if (modalEl) {
          var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.hide();
        }
        var newOption = new Option(response.name, response.id, true, true);
        $('#vendor_select').append(newOption).trigger('change');
      }
    },
    error: function (xhr) {
      // If server returned rendered HTML (partial), replace modal body
      if (xhr.responseText && xhr.getResponseHeader('Content-Type') && xhr.getResponseHeader('Content-Type').indexOf('text/html') !== -1) {
        $('#vendorCreateModal .modal-body').html(xhr.responseText);
        return;
      }
      var errors = xhr.responseJSON?.errors || {};
      var errorMsg = 'Error creating vendor';
      for (var field in errors) {
        if (errors[field] && errors[field].length > 0) {
          errorMsg = errors[field][0];
          break;
        }
      }
      $('#vendorCreateModal .modal-body').prepend('<div class="alert alert-danger">' + errorMsg + '</div>');
    }
  });
});
// Delegated handlers to support ContactPerson formset inside injected modal HTML
$(document).on('click', '#vendorCreateModal #add-contact-person-btn', function (e) {
  e.preventDefault();
  var $modal = $('#vendorCreateModal');
  var $body = $modal.find('.modal-body');
  var totalInput = $body.find('#id_contactperson-TOTAL_FORMS');
  if (!totalInput || totalInput.length === 0) return;
  var total = parseInt(totalInput.val() || '0');
  var tpl = $body.find('#empty-form-template').html();
  if (!tpl) return;
  var newHtml = tpl.replace(/__prefix__/g, total);
  $body.find('#contact-persons-container').append(newHtml);
  totalInput.val(total + 1);
});

$(document).on('click', '#vendorCreateModal .remove-contact', function (e) {
  e.preventDefault();
  var $btn = $(this);
  var $row = $btn.closest('.contact-row');
  if (!$row || $row.length === 0) return;
  var $deleteInput = $row.find('input[type="hidden"][name$="-DELETE"]');
  var $modal = $('#vendorCreateModal');
  var $body = $modal.find('.modal-body');
  var totalInput = $body.find('#id_contactperson-TOTAL_FORMS');
  if ($deleteInput && $deleteInput.length) {
    $deleteInput.val('on');
    $row.hide();
  } else {
    $row.remove();
    if (totalInput && totalInput.length) {
      var total = parseInt(totalInput.val() || '0');
      totalInput.val(Math.max(0, total - 1));
    }
  }
});
$(document).on('select2:open', () => {
  const searchField = $('.select2-container--open .select2-search__field');
  if (searchField.length) {
    searchField[0].focus();
  }
});

$('#vendor_select').on('select2:select', function (e) {
  var data = e.params.data;
  if (data && !data.isNew) {
    applyVendorPaymentTermsFromSelectData(data);
  }
});
