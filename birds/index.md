---
layout: default
title: "Bird lifers map"
wide: true
---

# Bird lifers map

For those interested, I also have many photographs available on [Flickr](https://www.flickr.com/photos/chrisdown/albums/72157711447135721?layout=justified).

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.3.0/papaparse.min.js"></script>
<script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.4.1/MarkerCluster.css"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.4.1/MarkerCluster.Default.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.4.1/leaflet.markercluster.js"></script>

<div id="map"></div>
<div id="sightings-table-container">
    <table id="sightings-table">
        <thead>
            <tr>
                <th>Lifer number</th>
                <th>Common name</th>
                <th>Scientific name</th>
                <th>Date</th>
            </tr>
        </thead>
        <tbody>
            <!-- Rows will be added here dynamically -->
        </tbody>
    </table>
</div>

<script>
    var map = L.map('map').setView([0, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
    }).addTo(map);
    L.Control.textbox = L.Control.extend({
        onAdd: function(map) {
            var text = L.DomUtil.create('div');
            text.id = "bird_tips";
            text.innerHTML = "<span style=\"background-color: rgba(0, 0, 0, 0.5); padding: 0.2em\">Click an entry in the table to focus the map</span>"
            return text;
        },

        onRemove: function(map) { }
    });
    L.control.textbox = function(opts) { return new L.Control.textbox(opts);}
    L.control.textbox({ position: 'bottomleft' }).addTo(map);

    var zoomLevel = 18;

    // disableClusteringAtZoom value should match the same as map.setView()
    var markers = L.markerClusterGroup({ maxClusterRadius: 50, disableClusteringAtZoom: zoomLevel });

    function processCSVData(csvURI) {
        Papa.parse(csvURI, {
            download: true,
            header: true,
            dynamicTyping: true,
            complete: function(results) {
                var data = results.data;
                var firstSightings = {};

                data.forEach(sighting => {
                    // TODO: huh, why does papa give an extra one?
                    if (!sighting || sighting.id === null) {
                        return;
                    }

                    var species = sighting.common_name;
                    var sightingDate = new Date(sighting.date);
                    var sightingDateUTC = new Date(sightingDate.getUTCFullYear(), sightingDate.getUTCMonth(), sightingDate.getUTCDate());

                    if (!firstSightings[species] || new Date(firstSightings[species].date) > sightingDateUTC) {
                        sighting.date = sightingDateUTC.toISOString().split('T')[0];
                        firstSightings[species] = sighting;
                    }
                });

                updateMapAndTable(firstSightings);
            }
        });
    }

    function updateMapAndTable(sightings) {
        var tableBody = document.getElementById('sightings-table').getElementsByTagName('tbody')[0];
        var sightingsArray = Object.values(sightings).reverse();
        var liferNumber = sightingsArray.length;

        sightingsArray.forEach((sighting, index) => {
            var roundedLatitude = sighting.latitude.toFixed(5);
            var roundedLongitude = sighting.longitude.toFixed(5);
            var markerId = `marker-${index}`;

            var wikiLink = `https://en.wikipedia.org/wiki/${sighting.scientific_name.replace(/ /g, '_')}`;
            var marker = L.marker([sighting.latitude, sighting.longitude])
                .bindPopup(`${sighting.common_name}<br><span style="font-style: italic">${sighting.scientific_name}</span><br>${sighting.date}<br>${roundedLatitude}, ${roundedLongitude}<br><a href="${wikiLink}" target="_blank">Wikipedia</a>`);
            markers.addLayer(marker);

            // Scroll table on view
            marker.on('click', function() {
                var row = document.querySelector(`[data-marker-id="${markerId}"]`);
                if (row) {
                    row.scrollIntoView({behavior: "smooth", block: "center"});
                    document.querySelectorAll('#sightings-table tbody tr').forEach(tr => {
                        tr.style.fontWeight = 'normal';
                        tr.classList.remove('flash');
                    });
                    row.style.fontWeight = 'bold';
                    row.classList.add('flash');
                }

                var row = document.querySelector(`[data-marker-id="${markerId}"]`);
                if (row) {
                    row.scrollIntoView({behavior: "instant", block: "center"});
                    document.querySelectorAll('#sightings-table tbody tr').forEach(tr => tr.style.fontWeight = 'normal');
                    row.style.fontWeight = 'bold';
                }
            });

            var row = tableBody.insertRow();
            row.setAttribute('data-marker-id', markerId);
            row.insertCell(0).textContent = liferNumber--;
            row.insertCell(1).textContent = sighting.common_name;
            row.insertCell(2).textContent = sighting.scientific_name;
            row.insertCell(3).textContent = sighting.date;

            row.addEventListener('click', function() {
                map.setView(marker.getLatLng(), zoomLevel);
                marker.openPopup();
            });
        });

        map.addLayer(markers);
    }

    var csvURI = '/birds/data.csv'; // Updated CSV file URI
    processCSVData(csvURI);
</script>