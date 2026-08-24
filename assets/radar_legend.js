// Toggle radar legend visibility when radar layer is toggled
(function() {
    'use strict';

    function setupLegendToggle(mapId, legendId, radarLayerName) {
        let retries = 0;
        const maxRetries = 40;

        const checkInterval = setInterval(function() {
            retries++;

            const mapElement = document.getElementById(mapId);
            const legend = document.getElementById(legendId);

            if (!mapElement || !legend) {
                if (retries >= maxRetries) clearInterval(checkInterval);
                return;
            }

            // Find the layers control within this map
            const layersControl = mapElement.querySelector('.leaflet-control-layers');

            if (layersControl) {
                clearInterval(checkInterval);

                // Find the checkbox for the radar layer
                const labels = layersControl.querySelectorAll('label');
                let radarCheckbox = null;

                labels.forEach(function(label) {
                    const text = label.textContent.trim();
                    if (text === radarLayerName) {
                        radarCheckbox = label.querySelector('input[type="checkbox"]');
                    }
                });

                if (radarCheckbox) {
                    // Set initial state
                    legend.style.display = radarCheckbox.checked ? 'block' : 'none';

                    // Listen to checkbox changes
                    radarCheckbox.addEventListener('change', function() {
                        legend.style.display = this.checked ? 'block' : 'none';
                    });

                    // Backup observer for checkbox state changes
                    const observer = new MutationObserver(function() {
                        legend.style.display = radarCheckbox.checked ? 'block' : 'none';
                    });
                    observer.observe(radarCheckbox, { attributes: true, attributeFilter: ['checked'] });
                }

            } else if (retries >= maxRetries) {
                clearInterval(checkInterval);
            }
        }, 250);
    }

    // Initialize
    function init() {
        setTimeout(function() {
            setupLegendToggle('map', 'radar-legend', 'Radar');
            setupLegendToggle('map-point', 'radar-legend-point', 'RADOLAN');
        }, 2000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
