document.addEventListener('DOMContentLoaded', function() {
    const productFilterInput = document.getElementById('product-filter');
    const productSelect = document.getElementById('id_produkty');

    if (productFilterInput && productSelect) {
        // Keep a copy of all original options
        const allOptions = Array.from(productSelect.options);

        productFilterInput.addEventListener('input', function() {
            const filterValue = this.value.toLowerCase();
            
            // Get currently selected values
            const selectedValues = Array.from(productSelect.selectedOptions).map(opt => opt.value);

            // Clear the select and re-add options that match the filter
            productSelect.innerHTML = '';

            allOptions.forEach(function(option) {
                const optionText = option.text.toLowerCase();
                const isSelected = selectedValues.includes(option.value);
                
                if (optionText.includes(filterValue) || isSelected) {
                    // Re-add the option
                    productSelect.add(option.cloneNode(true));
                    // If it was selected, re-select it
                    if (isSelected) {
                        const newOption = productSelect.querySelector(`option[value="${option.value}"]`);
                        if (newOption) {
                            newOption.selected = true;
                        }
                    }
                }
            });
        });
    }
});