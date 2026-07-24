// Dynamiczne filtrowanie listy produktow po modelu (bez przeladowania strony).
document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('modelLiveFilter');
    if (!input) return;

    const emptyMsg = document.getElementById('liveFilterEmpty');
    // Wszystkie wiersze produktow (dzialaja zarowno w widoku tabeli, jak i w grupowaniu).
    const rows = Array.from(document.querySelectorAll('tr[data-model]'));
    const groupItems = Array.from(document.querySelectorAll('[data-group-item]'));

    function applyFilter() {
        const q = input.value.trim().toLowerCase();
        let visibleCount = 0;

        rows.forEach(function (row) {
            const model = row.getAttribute('data-model') || '';
            const match = q === '' || model.indexOf(q) !== -1;
            row.style.display = match ? '' : 'none';
            if (match) visibleCount++;
        });

        // Widok grupowany: pokazuj tylko grupy, ktore maja pasujace wiersze,
        // i automatycznie rozwijaj je podczas wyszukiwania.
        groupItems.forEach(function (item) {
            const itemRows = item.querySelectorAll('tr[data-model]');
            let anyVisible = false;
            itemRows.forEach(function (r) {
                if (r.style.display !== 'none') anyVisible = true;
            });
            item.style.display = anyVisible ? '' : 'none';

            const collapse = item.querySelector('.accordion-collapse');
            const button = item.querySelector('.accordion-button');
            if (collapse && button) {
                if (q !== '' && anyVisible) {
                    collapse.classList.add('show');
                    button.classList.remove('collapsed');
                    button.setAttribute('aria-expanded', 'true');
                } else if (q === '') {
                    // Po wyczyszczeniu pola przywracamy zwiniete grupy.
                    collapse.classList.remove('show');
                    button.classList.add('collapsed');
                    button.setAttribute('aria-expanded', 'false');
                }
            }
        });

        if (emptyMsg) {
            emptyMsg.classList.toggle('d-none', visibleCount !== 0);
        }
    }

    input.addEventListener('input', applyFilter);

    // Jesli pole ma juz wartosc (np. po przeslaniu formularza), zastosuj od razu.
    if (input.value.trim() !== '') applyFilter();
});
