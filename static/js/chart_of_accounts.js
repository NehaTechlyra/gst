// console.log("chart")
  // Define the AJAX URL from Django in the template
  const generate_code_url = "{% url 'generate-code-ajax' %}";

$(document).ready(function() {
    // Initialize Select2 on parent select
    function initParentSelect() {
        $('#id_parent').select2({
            placeholder: 'Search or select parent',
            allowClear: true,
            width: '100%'
        });
    }

    // Bind event that fetches and sets generated code on parent change
   function bindParentChange() {
    $('#id_parent').off('change').on('change', function() {
        const parentId = $(this).val();
        console.log("Parent changed. Selected ID:", parentId);

        if (!parentId) {
            $('#id_search_code').val('');
            return;
        }

        // Use the global variable generated in the Django template for the URL
        console.log("AJAX URL:", generate_code_url + "?parent=" + parentId);

        $.ajax({
            url: '/chart_of_accounts/generate_code/',
            data: { parent: parentId },
            dataType: 'json',
            success: function(data) {
                console.log("Generated code from server:", data.code);
                // $('#id_search_code').val(data.code || '');
                // $('#id_search_code').css('color', 'grey');
                // // $('#id_search_code').css('background-color', 'grey');
                // // $('#id_description').focus().select();
                const $input = $('#id_search_code');
                $input.val(data.code || '');
                $input.css('color', 'grey');  // grey when first loaded

                // When user edits, restore to original color
                $input.one('input', function() {
                    $input.css('color', ''); // remove inline color to restore original style
                });
            },
            error: function(xhr, status, error) {
                console.error("Error fetching generated code:", error);
                $('#id_search_code').val('');
            }
        });
    });
}


    // On Account Type change, fetch new parents and reset code
    $('#id_type').change(function() {
        const typeCode = $(this).val();
        console.log("Account Type changed to:", typeCode);

        if (!typeCode) {
            // Clear parent and search_code if no type selected
            $('#id_parent').html('<option value="" selected>---------</option>');
            $('#id_search_code').val('');
            // Re-initialize Select2 on an empty parent dropdown
            initParentSelect();
            bindParentChange();
            return;
        }

        // Fetch new parents for selected type via AJAX
        $.ajax({
            url: "{% url 'get_parents_for_type' %}",
            data: { 'type_code': typeCode },
            dataType: 'json',
            success: function(data) {
                console.log("Parents data received:", data.parents);

                let options = '<option value="" selected>---------</option>';
                $.each(data.parents, function(index, parent) {
                    options += `<option value="${parent.id}">${parent.name}</option>`;
                });

                // Update parent select options
                $('#id_parent').html(options);

                // Initialize Select2 again on updated parent select
                initParentSelect();

                // Bind the parent change handler again on new element
                bindParentChange();

                // Clear search code field on type change
                $('#id_search_code').val('');
            },
            error: function(xhr, status, error) {
                console.error('Error fetching parents:', error);
            }
        });
    });

    // Initial mount: initialize Select2 and bind events
    initParentSelect();
    bindParentChange();
});

