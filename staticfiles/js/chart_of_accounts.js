// console.log("chart")

$(document).ready(function() {
    const $parent = $('#id_parent');
    const $type = $('#id_type');
    const $searchCode = $('#id_search_code');

    function initParentSelect() {
        if (!$parent.length) return;

        $parent.select2({
            placeholder: 'Search or select parent',
            allowClear: true,
            width: '100%'
        });

        if ($parent.val()) {
            $parent.trigger('change');
        }
    }

    function bindParentChange() {
        if (!$parent.length) return;

        $parent.off('change.account-parent').on('change.account-parent', function() {
            const parentId = $(this).val();

            if (!parentId) {
                $searchCode.val('');
                return;
            }

            $.ajax({
                url: '/chart_of_accounts/generate_code/',
                data: { parent: parentId },
                dataType: 'json',
                success: function(data) {
                    $searchCode.val(data.code || '');
                    $searchCode.css('color', 'grey');
                    $searchCode.one('input', function() {
                        $searchCode.css('color', '');
                    });
                },
                error: function(xhr, status, error) {
                    console.error('Error fetching generated code:', error);
                    $searchCode.val('');
                }
            });
        });
    }

    function applyParentOptions(data, preserveSelection) {
        if (!$parent.length) return;

        const previousValue = preserveSelection ? $parent.val() : '';
        const options = ['<option value="">---------</option>'];

        $.each(data.parents || [], function(index, parent) {
            const selected = String(parent.id) === String(previousValue) ? ' selected' : '';
            options.push(`<option value="${parent.id}"${selected}>${parent.name}</option>`);
        });

        $parent.html(options.join(''));

        if (previousValue && $parent.find(`option[value="${previousValue}"]`).length) {
            $parent.val(previousValue);
        } else {
            $parent.val('');
        }

        $parent.trigger('change');
        initParentSelect();
    }

    if ($type.length) {
        $type.on('change', function() {
            const typeCode = $(this).val();

            if (!typeCode) {
                $parent.html('<option value="">---------</option>');
                $parent.val('');
                $searchCode.val('');
                initParentSelect();
                return;
            }

            $.ajax({
                url: window.get_parents_url,
                data: { type_code: typeCode },
                dataType: 'json',
                success: function(data) {
                    applyParentOptions(data, true);
                    $searchCode.val('');
                },
                error: function(xhr, status, error) {
                    console.error('Error fetching parents:', error);
                }
            });
        });
    }

    initParentSelect();
    bindParentChange();

    $(document).on('select2:open', function() {
        const searchField = document.querySelector('.select2-container--open .select2-search__field');
        if (searchField) {
            searchField.focus();
        }
    });
});

