/* TODO app — tema claro/escuro + drag and drop */
(function () {
    'use strict';

    // ---- Toggle de tema ----
    var toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.addEventListener('click', function () {
            var html = document.documentElement;
            var next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', next);
            try { localStorage.setItem('todo-theme', next); } catch (e) {}
        });
    }

    // ---- Drag and drop para reordenar ----
    var list = document.getElementById('todo-list');
    if (!list) return;

    var dragged = null;

    list.querySelectorAll('.todo').forEach(function (item) {
        item.addEventListener('dragstart', function () {
            dragged = item;
            setTimeout(function () { item.classList.add('dragging'); }, 0);
        });
        item.addEventListener('dragend', function () {
            item.classList.remove('dragging');
            dragged = null;
        });
    });

    list.addEventListener('dragover', function (e) {
        e.preventDefault();
        if (!dragged) return;
        var after = null;
        list.querySelectorAll('.todo:not(.dragging)').forEach(function (item) {
            var box = item.getBoundingClientRect();
            if (e.clientY > box.top + box.height / 2) after = item;
        });
        if (after == null) list.prepend(dragged);
        else after.after(dragged);
    });

    list.addEventListener('drop', function (e) {
        e.preventDefault();
        var ordem = [];
        list.querySelectorAll('.todo').forEach(function (item) {
            ordem.push(item.getAttribute('data-id'));
        });
        fetch('/reordenar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ordem: ordem })
        }).catch(function () { window.location.reload(); });
    });
})();
