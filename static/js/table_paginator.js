/**
 * DataTablePaginator - Componente Reutilizável de Paginação e Filtragem Rápida
 * Estilo Padronizado SESMOB V2 / Triagem AIT
 */
class DataTablePaginator {
    constructor(tableSelector, options = {}) {
        this.table = typeof tableSelector === 'string' ? document.querySelector(tableSelector) : tableSelector;
        if (!this.table) return;

        this.options = Object.assign({
            pageSize: 10,
            pageSizeOptions: [10, 25, 50, 100, -1],
            searchPlaceholder: 'Pesquisar por qualquer informação...',
            searchEnabled: true,
            perPageEnabled: true
        }, options);

        this.currentPage = 1;
        this.pageSize = this.options.pageSize;
        this.searchQuery = '';
        
        this.init();
    }

    init() {
        this.tbody = this.table.querySelector('tbody');
        if (!this.tbody) return;

        this.allRows = Array.from(this.tbody.querySelectorAll('tr')).filter(tr => {
            if (tr.classList.contains('no-paginate') || tr.classList.contains('datatable-no-results')) return false;
            const singleTd = tr.querySelector('td[colspan]');
            if (singleTd && tr.children.length === 1) {
                tr.classList.add('no-paginate');
                return false;
            }
            return true;
        });
        this.filteredRows = [...this.allRows];

        // Cria container wrapper se não existir
        if (!this.table.parentElement.classList.contains('datatable-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'datatable-wrapper';
            this.table.parentNode.insertBefore(wrapper, this.table);
            wrapper.appendChild(this.table);
            this.wrapper = wrapper;
        } else {
            this.wrapper = this.table.parentElement;
        }

        this.renderToolbar();
        this.renderFooter();
        this.update();
    }

    renderToolbar() {
        // Remove toolbar anterior se houver
        const oldToolbar = this.wrapper.querySelector('.datatable-toolbar');
        if (oldToolbar) oldToolbar.remove();

        const toolbar = document.createElement('div');
        toolbar.className = 'datatable-toolbar';

        // Campo de Pesquisa
        if (this.options.searchEnabled) {
            const searchDiv = document.createElement('div');
            searchDiv.className = 'datatable-search';
            searchDiv.innerHTML = `
                <i class="fa-solid fa-magnifying-glass"></i>
                <input type="text" placeholder="${this.options.searchPlaceholder}" autocomplete="off">
            `;
            const input = searchDiv.querySelector('input');
            input.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.trim().toLowerCase();
                this.currentPage = 1;
                this.filter();
            });
            toolbar.appendChild(searchDiv);
        }

        // Seletor de Registros por Página
        if (this.options.perPageEnabled) {
            const perPageDiv = document.createElement('div');
            perPageDiv.className = 'datatable-perpage';
            let optionsHtml = this.options.pageSizeOptions.map(opt => {
                const label = opt === -1 ? 'Todos' : opt;
                return `<option value="${opt}" ${opt === this.pageSize ? 'selected' : ''}>${label}</option>`;
            }).join('');

            perPageDiv.innerHTML = `
                <label><i class="fa-solid fa-list-ol"></i> Exibir:</label>
                <select>${optionsHtml}</select>
                <span>registros</span>
            `;

            const select = perPageDiv.querySelector('select');
            select.addEventListener('change', (e) => {
                this.pageSize = parseInt(e.target.value, 10);
                this.currentPage = 1;
                this.update();
            });
            toolbar.appendChild(perPageDiv);
        }

        this.wrapper.insertBefore(toolbar, this.table);
    }

    renderFooter() {
        // Remove footer anterior se houver
        const oldFooter = this.wrapper.querySelector('.datatable-footer');
        if (oldFooter) oldFooter.remove();

        const footer = document.createElement('div');
        footer.className = 'datatable-footer';
        footer.innerHTML = `
            <div class="datatable-info"></div>
            <div class="datatable-pagination"></div>
        `;

        this.wrapper.appendChild(footer);
        this.infoEl = footer.querySelector('.datatable-info');
        this.paginationEl = footer.querySelector('.datatable-pagination');
    }

    filter() {
        if (!this.searchQuery) {
            this.filteredRows = [...this.allRows];
        } else {
            this.filteredRows = this.allRows.filter(row => {
                const text = row.innerText.toLowerCase();
                return text.includes(this.searchQuery);
            });
        }
        this.update();
    }

    update() {
        const total = this.allRows.length;
        const filteredTotal = this.filteredRows.length;
        const effectivePageSize = this.pageSize === -1 ? filteredTotal : this.pageSize;
        const totalPages = effectivePageSize > 0 ? Math.ceil(filteredTotal / effectivePageSize) : 1;

        if (this.currentPage > totalPages) {
            this.currentPage = totalPages || 1;
        }

        const startIndex = (this.currentPage - 1) * effectivePageSize;
        const endIndex = this.pageSize === -1 ? filteredTotal : Math.min(startIndex + effectivePageSize, filteredTotal);

        // Oculta todas as linhas e exibe apenas as da página atual
        this.allRows.forEach(row => row.style.display = 'none');

        if (filteredTotal === 0) {
            let noRow = this.tbody.querySelector('.datatable-no-results');
            if (!noRow) {
                noRow = document.createElement('tr');
                noRow.className = 'datatable-no-results no-paginate';
                const colCount = this.table.querySelectorAll('thead th').length || 8;
                noRow.innerHTML = `<td colspan="${colCount}" style="text-align: center; padding: 2rem; color: #94a3b8;"><i class="fa-solid fa-inbox" style="font-size: 1.8rem; margin-bottom: 0.5rem; display: block; color: #64748b;"></i>Nenhum registro correspondente encontrado.</td>`;
                this.tbody.appendChild(noRow);
            }
            noRow.style.display = '';
        } else {
            const noRow = this.tbody.querySelector('.datatable-no-results');
            if (noRow) noRow.style.display = 'none';

            for (let i = startIndex; i < endIndex; i++) {
                if (this.filteredRows[i]) {
                    this.filteredRows[i].style.display = '';
                }
            }
        }

        // Atualiza Informações do Rodapé
        if (this.infoEl) {
            if (filteredTotal === 0) {
                this.infoEl.innerHTML = `Mostrando <strong>0</strong> registros (total: <strong>${total}</strong>)`;
            } else if (filteredTotal === total) {
                this.infoEl.innerHTML = `Mostrando <strong>${startIndex + 1}</strong> a <strong>${endIndex}</strong> de <strong>${total}</strong> registros`;
            } else {
                this.infoEl.innerHTML = `Mostrando <strong>${startIndex + 1}</strong> a <strong>${endIndex}</strong> de <strong>${filteredTotal}</strong> registros filtrados (total: <strong>${total}</strong>)`;
            }
        }

        // Atualiza Botões de Paginação
        this.renderPaginationButtons(totalPages);
    }

    renderPaginationButtons(totalPages) {
        if (!this.paginationEl) return;
        this.paginationEl.innerHTML = '';

        if (totalPages <= 1) return;

        // Botão Anterior
        const prevBtn = document.createElement('button');
        prevBtn.type = 'button';
        prevBtn.className = 'page-btn';
        prevBtn.innerHTML = '<i class="fa-solid fa-chevron-left"></i> Anterior';
        prevBtn.disabled = this.currentPage === 1;
        prevBtn.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.update();
            }
        });
        this.paginationEl.appendChild(prevBtn);

        // Gera números de página com elipses se necessário
        const maxVisible = 5;
        let startPage = Math.max(1, this.currentPage - 2);
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);

        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        if (startPage > 1) {
            this.addPageNumberBtn(1);
            if (startPage > 2) {
                const el = document.createElement('span');
                el.className = 'page-ellipsis';
                el.textContent = '...';
                this.paginationEl.appendChild(el);
            }
        }

        for (let p = startPage; p <= endPage; p++) {
            this.addPageNumberBtn(p);
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                const el = document.createElement('span');
                el.className = 'page-ellipsis';
                el.textContent = '...';
                this.paginationEl.appendChild(el);
            }
            this.addPageNumberBtn(totalPages);
        }

        // Botão Próximo
        const nextBtn = document.createElement('button');
        nextBtn.type = 'button';
        nextBtn.className = 'page-btn';
        nextBtn.innerHTML = 'Próximo <i class="fa-solid fa-chevron-right"></i>';
        nextBtn.disabled = this.currentPage === totalPages;
        nextBtn.addEventListener('click', () => {
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.update();
            }
        });
        this.paginationEl.appendChild(nextBtn);
    }

    addPageNumberBtn(pageNum) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'page-btn' + (pageNum === this.currentPage ? ' active' : '');
        btn.textContent = pageNum;
        btn.addEventListener('click', () => {
            this.currentPage = pageNum;
            this.update();
        });
        this.paginationEl.appendChild(btn);
    }

    refresh() {
        this.allRows = Array.from(this.tbody.querySelectorAll('tr')).filter(tr => {
            if (tr.classList.contains('no-paginate') || tr.classList.contains('datatable-no-results')) return false;
            const singleTd = tr.querySelector('td[colspan]');
            if (singleTd && tr.children.length === 1) {
                tr.classList.add('no-paginate');
                return false;
            }
            return true;
        });
        this.filter();
    }
}

// Inicialização automática para tabelas com atributo data-paginate="true"
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('table[data-paginate="true"]').forEach(tbl => {
        const placeholder = tbl.dataset.searchPlaceholder || 'Pesquisar registros...';
        const pageSize = parseInt(tbl.dataset.pageSize || '10', 10);
        new DataTablePaginator(tbl, { searchPlaceholder: placeholder, pageSize: pageSize });
    });
});
