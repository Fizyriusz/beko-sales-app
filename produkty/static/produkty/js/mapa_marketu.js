// Renderer mapy marketu z lotu ptaka.
// Rysuje alejki (pionowe/poziome, o roznej dlugosci) oraz obiekty/wykluczenia
// na siatce wspolrzednych. Uzywany przez podglad i wersje do druku/PDF.
(function (global) {
    'use strict';

    var CELL = 28;      // rozmiar kratki w px
    var BOX = 16;       // rozmiar prostokata produktu
    var GAP = 3;
    var GRUB = 2;       // grubosc alejki w kratkach
    var MARGIN = 20;

    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
        });
    }

    function kolorProduktu(p) {
        return p.moja_marka ? '#378ADD' : '#D85A30';
    }

    // Rysuje produkty wzdluz alejki. Zwraca fragment SVG.
    function rysujProdukty(items, startX, startY, poziomo, dostepneMiejsce) {
        var max = Math.max(0, Math.floor((dostepneMiejsce - 6) / (BOX + GAP)));
        var out = '';
        items.slice(0, max).forEach(function (p, i) {
            var przesuniecie = i * (BOX + GAP);
            var x = poziomo ? startX + przesuniecie : startX;
            var y = poziomo ? startY : startY + przesuniecie;
            out += '<rect x="' + x + '" y="' + y + '" width="' + BOX + '" height="' + BOX +
                '" rx="2" fill="' + kolorProduktu(p) + '">' +
                '<title>' + esc(p.marka) + ' ' + esc(p.model) + '</title></rect>';
        });
        if (items.length > max) {
            var przesuniecieR = max * (BOX + GAP);
            var rx = poziomo ? startX + przesuniecieR : startX;
            var ry = poziomo ? startY : startY + przesuniecieR;
            out += '<text x="' + (rx + 2) + '" y="' + (ry + 12) + '" style="font-size:10px;fill:#555;">+' +
                (items.length - max) + '</text>';
        }
        return out;
    }

    function rysujAlejke(a) {
        var poziomo = a.orientacja === 'H';
        var x = MARGIN + a.x * CELL;
        var y = MARGIN + a.y * CELL;
        var w = poziomo ? a.dlugosc * CELL : GRUB * CELL;
        var h = poziomo ? GRUB * CELL : a.dlugosc * CELL;
        var dlugoscPx = poziomo ? w : h;

        var svg = '<g class="mapa-alejka" data-id="' + a.id + '" style="cursor:pointer;">';
        svg += '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h +
            '" rx="5" fill="#ffffff" stroke="#c7ccd1"></rect>';

        // Os alejki (ciemny pasek) - jak czarne kreski na szkicu
        if (poziomo) {
            svg += '<rect class="bar" x="' + x + '" y="' + (y + h / 2 - 3) + '" width="' + w +
                '" height="6" rx="3" fill="#555"></rect>';
            svg += rysujProdukty(a.lewa, x + 4, y + 4, true, dlugoscPx);
            svg += rysujProdukty(a.prawa, x + 4, y + h - BOX - 4, true, dlugoscPx);
            svg += '<text x="' + (x + w / 2) + '" y="' + (y - 6) +
                '" text-anchor="middle" style="font-size:11px;fill:#222;">' + esc(a.nazwa) + '</text>';
        } else {
            svg += '<rect class="bar" x="' + (x + w / 2 - 3) + '" y="' + y + '" width="6" height="' + h +
                '" rx="3" fill="#555"></rect>';
            svg += rysujProdukty(a.lewa, x + 4, y + 4, false, dlugoscPx);
            svg += rysujProdukty(a.prawa, x + w - BOX - 4, y + 4, false, dlugoscPx);
            svg += '<text x="' + (x + w / 2) + '" y="' + (y + h + 14) +
                '" text-anchor="middle" style="font-size:11px;fill:#222;">' + esc(a.nazwa) + '</text>';
        }
        svg += '</g>';
        return svg;
    }

    function rysujObiekt(o) {
        var x = MARGIN + o.x * CELL;
        var y = MARGIN + o.y * CELL;
        var w = o.w * CELL;
        var h = o.h * CELL;
        var svg = '<g class="mapa-obiekt" data-id="' + o.id + '">';
        svg += '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h +
            '" rx="5" fill="#eceff1" stroke="#90a4ae" stroke-dasharray="5 3"></rect>';
        svg += '<title>' + esc(o.nazwa) + ' (' + esc(o.typ) + ')</title>';
        var linie = esc(o.nazwa).split(' ');
        var tekst = linie.length > 2 ? linie.slice(0, 2).join(' ') + '…' : esc(o.nazwa);
        svg += '<text x="' + (x + w / 2) + '" y="' + (y + h / 2 + 4) +
            '" text-anchor="middle" style="font-size:10px;fill:#455a64;">' + tekst + '</text>';
        svg += '</g>';
        return svg;
    }

    function render(container, alejki, obiekty) {
        var maxX = 10, maxY = 6;
        alejki.forEach(function (a) {
            var poziomo = a.orientacja === 'H';
            maxX = Math.max(maxX, a.x + (poziomo ? a.dlugosc : GRUB));
            maxY = Math.max(maxY, a.y + (poziomo ? GRUB : a.dlugosc));
        });
        obiekty.forEach(function (o) {
            maxX = Math.max(maxX, o.x + o.w);
            maxY = Math.max(maxY, o.y + o.h);
        });

        var W = MARGIN * 2 + maxX * CELL;
        var H = MARGIN * 2 + maxY * CELL + 20;

        var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" style="min-width:' +
            Math.min(W, 1100) + 'px;" xmlns="http://www.w3.org/2000/svg">';
        obiekty.forEach(function (o) { svg += rysujObiekt(o); });
        alejki.forEach(function (a) { svg += rysujAlejke(a); });
        svg += '</svg>';
        container.innerHTML = svg;
    }

    // Podpiecie panelu szczegolow (tylko w widoku interaktywnym)
    function podepnijPanel(container, alejki, panel) {
        function lista(items) {
            if (!items.length) return '<p class="text-muted small mb-2">— brak —</p>';
            return '<ul class="list-unstyled small mb-2">' + items.map(function (p) {
                var znacznik = p.z_katalogu ? '' : ' <span class="badge bg-light text-dark border">spoza katalogu</span>';
                return '<li><span style="color:' + (p.moja_marka ? '#185FA5' : '#993C1D') + ';">&#9632;</span> <strong>' +
                    esc(p.marka) + '</strong> ' + esc(p.model) + znacznik + '</li>';
            }).join('') + '</ul>';
        }
        container.querySelectorAll('.mapa-alejka').forEach(function (g) {
            g.addEventListener('click', function () {
                container.querySelectorAll('.mapa-alejka .bar').forEach(function (b) {
                    b.setAttribute('fill', '#555');
                });
                var bar = g.querySelector('.bar');
                if (bar) bar.setAttribute('fill', '#185FA5');
                var id = parseInt(g.getAttribute('data-id'), 10);
                var a = alejki.find(function (x) { return x.id === id; });
                if (!a || !panel) return;
                panel.innerHTML = '<div class="card-body">' +
                    '<h5 class="card-title">' + esc(a.nazwa) + '</h5>' +
                    '<p class="text-muted">' + (esc(a.opis) || '<em>Brak opisu</em>') + '</p>' +
                    '<h6>Strona A</h6>' + lista(a.lewa) +
                    '<h6>Strona B</h6>' + lista(a.prawa) +
                    '</div>';
            });
        });
    }

    global.MapaMarketu = { render: render, podepnijPanel: podepnijPanel };
})(window);
