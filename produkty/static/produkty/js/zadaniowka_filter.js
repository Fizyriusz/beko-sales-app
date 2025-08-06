document.addEventListener('DOMContentLoaded', () => {
    const filterInput = document.getElementById('product-filter');
    const productList = document.getElementById('product-list');
    if (!filterInput || !productList) {
        return;
    }
    filterInput.addEventListener('input', () => {
        const filter = filterInput.value.toLowerCase();
        const items = productList.querySelectorAll('.col-md-4');
        items.forEach(item => {
            const label = item.querySelector('.form-check-label').textContent.toLowerCase();
            item.style.display = label.includes(filter) ? '' : 'none';
        });
    });
});
