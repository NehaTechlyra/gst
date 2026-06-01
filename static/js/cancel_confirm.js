 // Confirmation dialog for cancel button
document.addEventListener('DOMContentLoaded', function() {
    console.log("cancel confirm called");
    const cancelButton = document.getElementById('cancel-button');
    
    if (cancelButton) {
        cancelButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Create the confirmation modal
            const modalHtml = `
                <div class="modal fade" id="cancelConfirmationModal" tabindex="-1" role="dialog" aria-labelledby="cancelConfirmationLabel" aria-hidden="true">
                    <div class="modal-dialog" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="cancelConfirmationLabel">Confirm Navigation</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <p>Are you sure you want to go back? All unsaved data will be lost.</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-primary" id="confirm-cancel">OK</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Add modal to body
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('cancelConfirmationModal'));
            modal.show();
            
            // Handle the confirmation
            document.getElementById('confirm-cancel').addEventListener('click', function() {
                window.history.back();
            });
            
            // Clean up modal when it's hidden
            document.getElementById('cancelConfirmationModal').addEventListener('hidden.bs.modal', function () {
                document.getElementById('cancelConfirmationModal').remove();
            });
        });
    }

    // Track form changes - Global variable
    let formChanged = false;
    const form = document.querySelector('form');
    
    if (form) {
        // Track all form input changes
        form.addEventListener('change', function(e) {
            formChanged = true;
            console.log('Form changed via change event');
        });
        
        form.addEventListener('input', function(e) {
            formChanged = true;
            console.log('Form changed via input event');
        });
        
        // Also track Select2 changes on selects within the form
        const selects = form.querySelectorAll('select');
        selects.forEach(select => {
            if (window.$ && $(select).data('select2')) {
                $(select).on('change', function() {
                    formChanged = true;
                    console.log('Form changed via Select2 change event');
                });
            }
        });
    }
    
    // Global click interceptor for all links - Outside of form check
    document.addEventListener('click', function(e) {
        // Check if clicked element is a link
        let link = e.target.closest('a');
        
        console.log('Link clicked:', link ? link.href : 'not a link');
        
        if (link && formChanged) {
            // Get the href
            const href = link.getAttribute('href');
            
            console.log('Checking href:', href, 'formChanged:', formChanged);
            
            // Check if it's a navigation link (not modal, not anchor, not javascript)
            if (href && !href.startsWith('#') && !link.getAttribute('data-bs-toggle') && !href.startsWith('javascript:')) {
                console.log('Preventing navigation to:', href);
                e.preventDefault();
                e.stopPropagation();
                
                // Show confirmation modal
                const navModalHtml = `
                    <div class="modal fade" id="navConfirmationModal" tabindex="-1" role="dialog" aria-labelledby="navConfirmationLabel" aria-hidden="true">
                        <div class="modal-dialog" role="document">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h5 class="modal-title" id="navConfirmationLabel">Confirm Navigation</h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                </div>
                                <div class="modal-body">
                                    <p>Are you sure you want to leave this page? All unsaved data will be lost.</p>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                    <button type="button" class="btn btn-primary" id="confirm-nav">OK</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                // Remove any existing modal
                const existingModal = document.getElementById('navConfirmationModal');
                if (existingModal) existingModal.remove();
                
                // Add new modal to body
                document.body.insertAdjacentHTML('beforeend', navModalHtml);
                
                // Show the modal
                const navModal = new bootstrap.Modal(document.getElementById('navConfirmationModal'));
                navModal.show();
                
                // Store the target URL
                const targetUrl = href;
                
                // Handle the confirmation
                document.getElementById('confirm-nav').addEventListener('click', function() {
                    formChanged = false; // Reset to allow navigation
                    window.location.href = targetUrl;
                });
                
                // Clean up modal when it's hidden
                document.getElementById('navConfirmationModal').addEventListener('hidden.bs.modal', function () {
                    document.getElementById('navConfirmationModal').remove();
                });
            }
        }
    }, true); // Use capture phase for better event handling
});