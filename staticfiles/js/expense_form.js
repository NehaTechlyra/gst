function initializeSelect2($element) {
    const $select = $($element);
    const $container = $select.closest('td');
    
    if ($select.hasClass('select2-hidden-accessible')) {
        $select.select2('destroy');
    }
    
    $select.select2({
        width: '100%',
        dropdownParent: $container,
        minimumResultsForSearch: 0,
        placeholder: "Select...",
        allowClear: true
    });
}

function createEmptyRow(index) {
    // Create a fresh row structure
    const $row = $(`
        <tr class="expense-line">
            <td>
                <select name="lines-${index}-account" id="lines-${index}-account" class="form-select line-account">
                    <option value="">Select an expense account</option>
                    ${$('#id_account').html()}
                </select>
            </td>
            <td>
                <input type="text" name="lines-${index}-notes" id="lines-${index}-notes" class="form-control line-notes" value="">
            </td>
            <td>
                <div style="display:flex; gap:8px; align-items:center;">
                    <select name="lines-${index}-tax" id="lines-${index}-tax" class="form-select line-tax">
                        <option value="">---------</option>
                        ${$('#id_tax').html()}
                    </select>
                    <button type="button" class="btn btn-outline-secondary btn-add-tax" title="Add Tax">+</button>
                </div>
            </td>
            <td class="text-end">
                <input type="number" name="lines-${index}-amount" id="lines-${index}-amount" class="form-control line-amount" value="0" step="0.01">
            </td>
            <td class="text-center">
                <input type="checkbox" name="lines-${index}-DELETE" id="lines-${index}-DELETE" style="display:none;">
                <i class="bx bx-x remove-line"></i>
            </td>
        </tr>
    `);

    return $row;
}

function addExpenseRow() {
    const index = $('#expense-lines tbody tr').length;
    const $newRow = createEmptyRow(index);
    
    // Append the new row
    $('#expense-lines tbody').append($newRow);
    
    // Initialize Select2 after the row is added to the DOM
    setTimeout(() => {
        $newRow.find('.line-account, .line-tax').each(function() {
            initializeSelect2(this);
        });
    }, 100);
    
    // Update formset management form
    $('#id_lines-TOTAL_FORMS').val(index + 1);
    
    recalcExpenseTotal();
}

$(document).ready(function() {
    // Initialize existing Select2 dropdowns
    $('.line-account, .line-tax').each(function() {
        initializeSelect2(this);
    });

    // Event handlers
    $('#add-expense-line').on('click', addExpenseRow);
    
    $(document).on('click', '.remove-line', function() {
        const $row = $(this).closest('tr');
        if ($('#expense-lines tbody tr:visible').length > 1) {
            // Remove the row
            $row.remove();
            // Re-index remaining rows
            $('#expense-lines tbody tr').each(function(index) {
                $(this).find(':input').each(function() {
                    const name = $(this).attr('name');
                    if (name) {
                        const newName = name.replace(/-\d+-/, `-${index}-`);
                        $(this).attr('name', newName).attr('id', newName);
                    }
                });
            });
            // Update form count
            $('#id_lines-TOTAL_FORMS').val($('#expense-lines tbody tr').length);
            recalcExpenseTotal();
        } else {
            showToast('Cannot remove the last expense line', 'warning');
        }
    });
});