document.addEventListener('DOMContentLoaded', function() {
    const availableProductsContainer = document.getElementById('available-products');
    const selectedProductsContainer = document.getElementById('selected-products');
    const productFilter = document.getElementById('product-filter');
    const formProdukty = document.querySelector('[name="produkty"]');
    const form = document.querySelector('form');

    function moveProduct(item, fromContainer, toContainer) {
        toContainer.appendChild(item);
        // Re-run filter to ensure correct visibility in both lists
        filterAndSortLists();
    }

    function onItemClick(event) {
        event.preventDefault();
        const item = event.currentTarget;
        const fromContainer = item.parentElement;
        const toContainer = fromContainer.id === 'available-products' ? selectedProductsContainer : availableProductsContainer;
        moveProduct(item, fromContainer, toContainer);
    }

    function filterAndSortLists() {
        const filterText = productFilter.value.toLowerCase();
        const selectedValues = new Set(Array.from(selectedProductsContainer.children).map(item => item.dataset.value));

        // Create a fragment to hold all items and sort them, to avoid layout thrashing
        const availableFragment = document.createDocumentFragment();
        const allItems = Array.from(availableProductsContainer.children).concat(Array.from(selectedProductsContainer.children));
        
        // Sort all items alphabetically by text content
        allItems.sort((a, b) => a.textContent.localeCompare(b.textContent));

        // Clear containers and re-append sorted items
        availableProductsContainer.innerHTML = '';
        
        allItems.forEach(item => {
            const isSelected = selectedValues.has(item.dataset.value);
            if (!isSelected) {
                availableFragment.appendChild(item);
                const matchesFilter = item.textContent.toLowerCase().includes(filterText);
                item.style.display = matchesFilter ? '' : 'none';
            }
        });

        availableProductsContainer.appendChild(availableFragment);
    }
    
    // Initial Setup
    function initialize() {
        // Attach event listeners to all product items
        const allItems = document.querySelectorAll('#available-products .list-group-item, #selected-products .list-group-item');
        allItems.forEach(item => {
            item.addEventListener('click', onItemClick);
        });

        // Perform initial filtering and sorting
        filterAndSortLists();
    }

    productFilter.addEventListener('input', filterAndSortLists);

    form.addEventListener('submit', function() {
        // Clear previous selections
        Array.from(formProdukty.options).forEach(option => {
            option.selected = false;
        });
        // Select items in the selected products container
        Array.from(selectedProductsContainer.children).forEach(item => {
            const option = formProdukty.querySelector(`option[value="${item.dataset.value}"]`);
            if (option) {
                option.selected = true;
            }
        });
    });

    initialize();
});
