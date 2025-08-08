document.addEventListener('DOMContentLoaded', () => {
    const typSelect = document.getElementById('typ');
    if (!typSelect) {
        return;
    }

    function updateVisibility() {
        const typ = typSelect.value;
        const groups = document.querySelectorAll('.mix-prowizja-only, .mix-mnoznik-only, .konkretne-modele-only');
        groups.forEach(el => {
            el.style.display = 'none';
        });

        if (typ === 'MIX_PROWIZJA') {
            document.querySelectorAll('.mix-prowizja-only').forEach(el => {
                el.style.display = '';
            });
        } else if (typ === 'MIX_MNOZNIK') {
            document.querySelectorAll('.mix-mnoznik-only').forEach(el => {
                el.style.display = '';
            });
        } else if (typ === 'KONKRETNE_MODELE') {
            document.querySelectorAll('.konkretne-modele-only').forEach(el => {
                el.style.display = '';
            });
        }
    }

    typSelect.addEventListener('change', updateVisibility);
    updateVisibility();
});

