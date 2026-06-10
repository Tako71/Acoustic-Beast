document.addEventListener('DOMContentLoaded', function () {
    const btn        = document.getElementById('generateFields');
    const container  = document.getElementById('pointsContainer');
    const body       = document.getElementById('pointsBody');
    const hint       = document.getElementById('strategyHint');
    const submitBtn  = document.getElementById('submitBtn');

    const strategyHints = {
        operation: 'Укажите уровень шума (дБ) и длительность операции (мин) для каждой точки.',
        function:  'Укажите уровень шума (дБ) и продолжительность функции (мин) для каждой точки.',
        day:       'Укажите уровень шума (дБ) для каждой точки замера.',
    };

    function getStrategy() {
        const checked = document.querySelector('input[name="strategy"]:checked');
        return checked ? checked.value : 'day';
    }

    function buildFields() {
        const numEl    = document.querySelector('input[name="num_points"]');
        const numPoints = parseInt(numEl ? numEl.value : 0) || 0;
        const strategy  = getStrategy();

        if (numPoints < 1 || numPoints > 50) {
            container.innerHTML = `
                <div style="color:var(--danger);font-size:13px;padding:4px 0">
                    Укажите от 1 до 50 точек замеров.
                </div>`;
            body.style.display = 'block';
            submitBtn.disabled = true;
            return;
        }

        hint.textContent = strategyHints[strategy] || '';
        const needDuration = strategy === 'operation' || strategy === 'function';
        const durLabel = strategy === 'operation' ? 'Длит. операции, мин' : 'Длит. функции, мин';

        let html = `<div class="points-table">`;

        // Header row
        html += `<div class="pt-row ${needDuration ? 'has-duration' : 'no-duration'} header pt-header">
            <div class="pt-num">#</div>
            <div>Уровень шума, дБ</div>
            ${needDuration ? `<div>${durLabel}</div>` : ''}
        </div>`;

        for (let i = 1; i <= numPoints; i++) {
            html += `<div class="pt-row ${needDuration ? 'has-duration' : 'no-duration'} pt-data-row"
                         style="opacity:0;animation:fadeInRow .3s ease ${i * 40}ms forwards">
                <div class="pt-num">${i}</div>
                <div>
                    <input type="number" name="noise_${i}" step="0.1" min="0" max="200"
                           class="form-control" placeholder="напр. 78.5" required>
                </div>
                ${needDuration ? `<div>
                    <input type="number" name="duration_${i}" step="0.1" min="0.1"
                           class="form-control" placeholder="напр. 120" required>
                </div>` : ''}
            </div>`;
        }

        html += `</div>`;
        container.innerHTML = html;
        body.style.display = 'block';
        submitBtn.disabled = false;
    }

    btn.addEventListener('click', function () {
        buildFields();
        // Scroll to points section
        setTimeout(() => body.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 100);
    });

    document.querySelectorAll('input[name="strategy"]').forEach(radio => {
        radio.addEventListener('change', function () {
            hint.textContent = strategyHints[this.value] || '';
            if (body.style.display !== 'none') buildFields();
        });
    });

    // Show spinner on submit
    document.getElementById('calculateForm').addEventListener('submit', function () {
        submitBtn.innerHTML = 'Считаем...';
        submitBtn.disabled = true;
    });
});
