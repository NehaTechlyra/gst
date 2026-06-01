// Initialize Select2 for an element
function initSelect2ForElement(element) {
    const $select = $(element);
    const $container = $select.closest('td, .col-md-3, .col-md-4');
    
    // Make sure Select2 is destroyed if it was already initialized
    if ($select.data('select2')) {
        $select.select2('destroy');
    }
    
    $select.select2({
        dropdownParent: $container,
        width: '100%',
        minimumResultsForSearch: 0,
        placeholder: "Select...",
        allowClear: true
    });
}

// Initialize all Select2 elements in a container
function initializeAllSelect2($container) {
    $container.find('select').each(function() {
        initSelect2ForElement(this);
    });
}

// Create and initialize a new expense row
function createExpenseRow(index) {
    const rowHtml = `
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
    `;
    
    return $(rowHtml);
}

$(document).ready(function() {
    // Handle adding new expense row
    $('#add-expense-line').on('click', function() {
        const index = $('#expense-lines tbody tr').length;
        const $newRow = createExpenseRow(index);
        
        // Append the row first
        $('#expense-lines tbody').append($newRow);
        
        // Initialize Select2 after the row is in the DOM
        $newRow.find('.line-account, .line-tax').each(function() {
            initSelect2ForElement(this);
        });
        
        // Update form count
        $('#id_lines-TOTAL_FORMS').val(index + 1);
        
        // Update total
        if (typeof recalcExpenseTotal === 'function') {
            recalcExpenseTotal();
        }
    });
    
    // Handle removing expense row
    $(document).on('click', '.remove-line', function() {
        const $row = $(this).closest('tr');
        
        if ($('#expense-lines tbody tr:visible').length > 1) {
            // Destroy Select2 instances before removing
            $row.find('.select2-hidden-accessible').each(function() {
                $(this).select2('destroy');
            });
            
            // Remove the row
            $row.remove();
            
            // Renumber remaining rows
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
            
            // Update total
            if (typeof recalcExpenseTotal === 'function') {
                recalcExpenseTotal();
            }
        } else {
            if (typeof showToast === 'function') {
                showToast('Cannot remove the last expense line', 'warning');
            } else {
                alert('Cannot remove the last expense line');
            }
        }
    });
    
    // Initialize Select2 for existing rows
    initializeAllSelect2($('#expense-lines'));
});