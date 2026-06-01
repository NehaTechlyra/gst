// search items
document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.getElementById("itemSearchInput");
    const tableContainer = document.getElementById("itemTableContainer");

    let timeout = null;

    searchInput.addEventListener("keyup", function() {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            const query = searchInput.value;

            fetch(`?q=${encodeURIComponent(query)}`, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(response => response.text())
            .then(html => {
                // Create a temporary DOM to extract the table only
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = html;
                const newTable = tempDiv.querySelector("#itemTableContainer");
                if (newTable) {
                    tableContainer.innerHTML = newTable.innerHTML;
                }
            });
        }, 300); // Wait 300ms after typing
    });
});


