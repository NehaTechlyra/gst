document.addEventListener('DOMContentLoaded', function() {
    const modeSelect = document.getElementById('id_mode');

    function toggleFields() {
        const mode = modeSelect.value;

        const gsm = document.querySelectorAll('.gsm-fields');
        const mobile = document.querySelectorAll('.mobile-fields');
        const api = document.querySelectorAll('.api-fields');

        // Hide all
        [gsm, mobile, api].forEach(group =>
            group.forEach(el => el.style.display = 'none')
        );

        // Show selected
        if (mode === 'gsm') gsm.forEach(el => el.style.display = '');
        if (mode === 'mobile') mobile.forEach(el => el.style.display = '');
        if (mode === 'api') api.forEach(el => el.style.display = '');
    }

    if (modeSelect) {
        toggleFields(); // Initial
        modeSelect.addEventListener('change', toggleFields);
    }
});
