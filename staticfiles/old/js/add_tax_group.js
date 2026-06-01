 function loadTaxForm() {
  fetch("{% url 'tax_add_modal' %}")
    .then(response => response.text())
    .then(html => {
      document.getElementById('taxModalContent').innerHTML = html;
      const taxModal = new bootstrap.Modal(document.getElementById('taxModal'));
      taxModal.show();
      bindTaxFormSubmit();
    })
    .catch(error => console.error('Error loading form:', error));
}

function bindTaxFormSubmit() {
  const form = document.getElementById('taxForm');
  if (!form) return;

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(form);

    fetch("{% url 'tax_add_modal' %}", {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        const taxModalEl = document.getElementById('taxModal');
        const taxModal = bootstrap.Modal.getInstance(taxModalEl);
        taxModal.hide();

        showToast('Tax added successfully.', 'success');
        // Optionally, refresh part of your page or update UI here
        // Add the code here to reload and update tax choices in the main form
    fetch("{% url 'tax_choices_partial' %}")
      .then(response => response.text())
      .then(html => {
        // Update the tax choices container with new HTML
        document.getElementById('taxes_container').innerHTML = html;
      });
      } else {
        document.getElementById('taxModalContent').innerHTML = data.html_form;
        bindTaxFormSubmit(); // re-bind event listeners for new form content
      }
    })
    .catch(error => console.error('Error submitting form:', error));
  });
}

document.getElementById('openTaxModalButton').addEventListener('click', loadTaxForm);


function showToast(message, type='success') {
  let toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toastContainer';
    toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '1080';
    document.body.appendChild(toastContainer);
  }
  const toastEl = document.createElement('div');
  toastEl.className = `toast align-items-center text-bg-${type} border-0`;
  toastEl.setAttribute('role', 'alert');
  toastEl.setAttribute('aria-live', 'assertive');
  toastEl.setAttribute('aria-atomic', 'true');
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  toastContainer.appendChild(toastEl);

  const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
  toast.show();
}