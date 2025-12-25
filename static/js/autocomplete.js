// static/js/autocomplete.js — полностью рабочая версия

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.autocomplete').forEach(input => {
        const type = input.dataset.type; // "city" или "country"
        const endpoint = type === 'city' ? '/api/cities' : '/api/countries';
        let dropdown = null;

        const createDropdown = () => {
            dropdown = document.createElement('div');
            dropdown.className = 'autocomplete-dropdown';
            dropdown.style.position = 'absolute';
            dropdown.style.background = 'white';
            dropdown.style.border = '1px solid #ccc';
            dropdown.style.borderRadius = '6px';
            dropdown.style.maxHeight = '200px';
            dropdown.style.overflowY = 'auto';
            dropdown.style.zIndex = '1000';
            dropdown.style.width = '100%';
            dropdown.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            dropdown.style.marginTop = '2px';
            input.parentNode.style.position = 'relative';
            input.parentNode.appendChild(dropdown);
        };

        const removeDropdown = () => {
            if (dropdown && dropdown.parentNode) {
                dropdown.parentNode.removeChild(dropdown);
                dropdown = null;
            }
        };

        input.addEventListener('input', async () => {
            const q = input.value.trim();
            removeDropdown();
            if (q.length < 2) return;

            try {
                const response = await fetch(`${endpoint}?q=${encodeURIComponent(q)}`);
                if (!response.ok) return;
                const suggestions = await response.json();
                if (suggestions.length === 0) return;

                createDropdown();
                suggestions.forEach(suggestion => {
                    const item = document.createElement('div');
                    item.textContent = suggestion;
                    item.style.padding = '10px 12px';
                    item.style.cursor = 'pointer';
                    item.onmouseover = () => item.style.backgroundColor = '#f0f0f0';
                    item.onmouseout = () => item.style.backgroundColor = 'white';
                    item.onclick = () => {
                        input.value = suggestion;
                        removeDropdown();
                    };
                    dropdown.appendChild(item);
                });
            } catch (err) {
                console.error('Ошибка автокомплита:', err);
            }
        });

        // Скрывать дропдаун при клике вне поля
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && dropdown && !dropdown.contains(e.target)) {
                removeDropdown();
            }
        });
    });
});