function initAutocomplete(players, preselected = []) {
    const input = document.getElementById('player-input');
    const tagsContainer = document.getElementById('player-tags');
    const hiddenInput = document.getElementById('players_json');
    let selectedPlayers = [...preselected];

    // ایجاد datalist
    const datalist = document.createElement('datalist');
    datalist.id = 'players-list';
    players.forEach(p => {
        const option = document.createElement('option');
        option.value = p.name;
        datalist.appendChild(option);
    });
    document.body.appendChild(datalist);

    function renderTags() {
        tagsContainer.innerHTML = '';
        selectedPlayers.forEach(id => {
            const player = players.find(p => p.id === id);
            if (player) {
                const tag = document.createElement('span');
                tag.className = 'inline-flex items-center max-h-[44px] bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-2 rounded-full text-sm font-bold shadow';
                tag.innerHTML = `
                    ${player.name}
                    <button type="button" class="mr-3 text-white hover:text-gray-200 text-lg">×</button>
                `;
                tag.querySelector('button').onclick = () => {
                    selectedPlayers = selectedPlayers.filter(p => p !== id);
                    renderTags();
                    updateHidden();
                };
                tagsContainer.appendChild(tag);
            }
        });
    }

    function updateHidden() {
        hiddenInput.value = JSON.stringify(selectedPlayers);
    }

    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const name = input.value.trim();
            const player = players.find(p => p.name === name);
            if (player && !selectedPlayers.includes(player.id)) {
                selectedPlayers.push(player.id);
                renderTags();
                updateHidden();
                input.value = '';
            }
        }
    });

    // نمایش بازیکنان از پیش انتخاب شده
    renderTags();
    updateHidden();
}

// برای دیباگ
window.initAutocomplete = initAutocomplete;