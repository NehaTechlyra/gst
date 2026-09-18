document.addEventListener('DOMContentLoaded', function () {
  function updateDateFields(form) {
    const period = form.querySelector('[name="period"]');
    const dateFields = form.querySelectorAll('[name="start_date"], [name="end_date"]');
    if (!period) {
      return;
    }

    const isCustom = period.value === 'custom';
    dateFields.forEach(function (field) {
      field.disabled = !isCustom;
      field.setAttribute('aria-disabled', String(!isCustom));
    });
  }

  document.querySelectorAll('[data-mis-date-filter]').forEach(function (form) {
    const period = form.querySelector('[name="period"]');
    if (!period) {
      return;
    }

    period.addEventListener('change', function () {
      updateDateFields(form);
    });
    form.addEventListener('reset', function () {
      window.setTimeout(function () {
        updateDateFields(form);
      }, 0);
    });
    updateDateFields(form);
  });
});
