// Estado global
let processos = {};
let processosConteudo = {}; // Cache de conteudo para busca
let processoSelecionado = null;
let conteudoCache = {};
let favoritos = new Set(); // Processos marcados como favoritos

// Elementos DOM
const busca = document.getElementById('busca');
const btnImportar = document.getElementById('btn-importar');
const btnAtualizar = document.getElementById('btn-atualizar');
const btnTema = document.getElementById('btn-tema');
const contador = document.getElementById('contador');
const previewModal = document.getElementById('preview-modal');
const previewTitulo = document.getElementById('preview-titulo');
const previewRisco = document.getElementById('preview-risco');
const previewOrdem = document.getElementById('preview-ordem');
const previewEmenta = document.getElementById('preview-ementa');
const previewAnalise = document.getElementById('preview-analise');
const btnFecharPreview = document.getElementById('btn-fechar-preview');
const btnDeAcordo = document.getElementById('btn-de-acordo');
const btnDestacar = document.getElementById('btn-destacar');
const btnCopiarNumero = document.getElementById('btn-copiar-numero');
const btnRelatorio = document.getElementById('btn-relatorio');
const btnPdfProcesso = document.getElementById('btn-pdf-processo');

// Modal de importacao
const importarModal = document.getElementById('importar-modal');
const btnFecharImportar = document.getElementById('btn-fechar-importar');
const btnCancelarImportar = document.getElementById('btn-cancelar-importar');
const btnConfirmarImportar = document.getElementById('btn-confirmar-importar');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const textoColar = document.getElementById('texto-colar');

// Loading overlay
const loadingOverlay = document.getElementById('loading-overlay');
const loadingMessage = document.getElementById('loading-message');

// Inicializacao
document.addEventListener('DOMContentLoaded', () => {
    carregarTema();
    carregarFavoritos();
    carregarProcessos();
    configurarEventos();
});

// Gerenciamento de Tema
function carregarTema() {
    const temaSalvo = localStorage.getItem('lista-trf-tema') || 'escuro';
    document.body.className = temaSalvo === 'claro' ? 'tema-claro' : 'tema-escuro';
}

function alternarTema() {
    const isClaro = document.body.classList.contains('tema-claro');
    document.body.className = isClaro ? 'tema-escuro' : 'tema-claro';
    localStorage.setItem('lista-trf-tema', isClaro ? 'escuro' : 'claro');
}

// Gerenciamento de Favoritos
function carregarFavoritos() {
    const salvos = localStorage.getItem('lista-trf-favoritos');
    if (salvos) {
        favoritos = new Set(JSON.parse(salvos));
    }
}

function salvarFavoritos() {
    localStorage.setItem('lista-trf-favoritos', JSON.stringify([...favoritos]));
}

function toggleFavorito(numero) {
    if (favoritos.has(numero)) {
        favoritos.delete(numero);
    } else {
        favoritos.add(numero);
    }
    salvarFavoritos();
}

function isFavorito(numero) {
    return favoritos.has(numero);
}

// Carregar processos da API
async function carregarProcessos() {
    try {
        const response = await fetch('/api/processos');
        processos = await response.json();

        // Carregar conteudo para busca
        await carregarConteudoParaBusca();

        renderizarKanban();
        atualizarContador();
    } catch (error) {
        console.error('Erro ao carregar processos:', error);
    }
}

// Carregar conteudo dos documentos para permitir busca
async function carregarConteudoParaBusca() {
    processosConteudo = {};

    for (const estado of Object.keys(processos)) {
        for (const proc of processos[estado]) {
            try {
                const response = await fetch(`/api/processo/${estado}/${proc.numero}`);
                const conteudo = await response.json();
                processosConteudo[proc.numero] = {
                    ementa: (conteudo.ementa || '').toLowerCase(),
                    analise: (conteudo.analise || '').toLowerCase()
                };
            } catch (e) {
                processosConteudo[proc.numero] = { ementa: '', analise: '' };
            }
        }
    }
}

// Verificar se processo corresponde ao filtro
function processoCorrespondeAoFiltro(proc, filtro) {
    if (!filtro) return true;

    // Busca no numero do processo
    if (proc.numero.toLowerCase().includes(filtro)) return true;

    // Busca no tema
    if (proc.tema && proc.tema.toLowerCase().includes(filtro)) return true;

    // Busca no conteudo
    const conteudo = processosConteudo[proc.numero];
    if (conteudo) {
        if (conteudo.ementa.includes(filtro)) return true;
        if (conteudo.analise.includes(filtro)) return true;
    }

    return false;
}

// Obter icone de risco
function getIconeRisco(risco) {
    switch (risco) {
        case 'vermelho': return '🔴';
        case 'amarelo': return '🟡';
        case 'verde': return '🟢';
        default: return '⚪';
    }
}

// Obter classe CSS de risco
function getClasseRisco(risco) {
    switch (risco) {
        case 'vermelho': return 'risco-vermelho';
        case 'amarelo': return 'risco-amarelo';
        case 'verde': return 'risco-verde';
        default: return 'risco-neutro';
    }
}

// Renderizar Kanban
function renderizarKanban() {
    const filtro = busca.value.toLowerCase().trim();

    Object.keys(processos).forEach(estado => {
        const coluna = document.querySelector(`[data-estado="${estado}"] .kanban-cards`);
        const countSpan = document.querySelector(`[data-estado="${estado}"] .count`);

        if (!coluna) return;

        // Filtrar processos
        let processosFiltrados = processos[estado].filter(p =>
            processoCorrespondeAoFiltro(p, filtro)
        );

        // Ordenar pela ordem da lista (campo 'ordem')
        processosFiltrados.sort((a, b) => {
            const ordemA = a.ordem || 9999;
            const ordemB = b.ordem || 9999;
            return ordemA - ordemB;
        });

        // Atualizar contador da coluna
        countSpan.textContent = processosFiltrados.length;

        // Limpar e renderizar cards
        coluna.innerHTML = '';
        processosFiltrados.forEach(proc => {
            const card = criarCard(proc);
            coluna.appendChild(card);
        });

        // Inicializar drag-and-drop
        new Sortable(coluna, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'dragging',
            onEnd: handleDragEnd
        });
    });
}

// Criar card
function criarCard(processo) {
    const card = document.createElement('div');
    card.className = `kanban-card ${getClasseRisco(processo.risco)}`;
    card.dataset.numero = processo.numero;
    card.dataset.estado = processo.estado;
    card.dataset.caminho = processo.caminho;

    // Icone de risco
    const iconeRisco = getIconeRisco(processo.risco);

    // Botao de favorito (estrela)
    const favoritoAtivo = isFavorito(processo.numero) ? 'ativo' : '';
    const estrela = isFavorito(processo.numero) ? '★' : '☆';

    // Tema vinculante (ao lado do risco)
    const temaVinculante = processo.tema_vinculante
        ? `<span class="card-tema-vinculante">${processo.tema_vinculante}</span>`
        : '';

    // Numero da ordem na lista (discreto)
    const ordemBadge = processo.ordem
        ? `<span class="card-ordem" title="N na lista de julgamento">${processo.ordem}</span>`
        : '';

    // Tema resumido (descricao)
    const tema = processo.tema ? `<div class="card-tema">${processo.tema}</div>` : '';

    // Botoes de acao rapida (V e X) - mostrar apenas se nao estiver na coluna final
    const mostrarBtnDeAcordo = processo.estado !== 'de-acordo';
    const mostrarBtnDestacar = processo.estado !== 'destacar';

    card.innerHTML = `
        ${ordemBadge}
        <button class="btn-favorito ${favoritoAtivo}" title="Marcar como favorito">${estrela}</button>
        <div class="card-header">
            <span class="card-risco">${iconeRisco}</span>
            ${temaVinculante}
        </div>
        <div class="card-numero">${processo.numero}</div>
        ${tema}
        <div class="card-acoes-rapidas">
            ${mostrarBtnDeAcordo ? '<button class="btn-acao-rapida btn-de-acordo-rapido" title="De acordo">✓</button>' : ''}
            ${mostrarBtnDestacar ? '<button class="btn-acao-rapida btn-destacar-rapido" title="Destacar">✗</button>' : ''}
        </div>
    `;

    // Evento de clique no card (ignorar cliques nos botoes)
    card.addEventListener('click', (e) => {
        if (!e.target.classList.contains('btn-favorito') &&
            !e.target.classList.contains('btn-acao-rapida')) {
            selecionarProcesso(processo);
        }
    });

    // Evento do botao favorito
    const btnFavorito = card.querySelector('.btn-favorito');
    if (btnFavorito) {
        btnFavorito.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleFavorito(processo.numero);
            // Atualizar visual
            btnFavorito.classList.toggle('ativo');
            btnFavorito.textContent = btnFavorito.classList.contains('ativo') ? '★' : '☆';
        });
    }

    // Evento do botao de acordo rapido
    const btnDeAcordoRapido = card.querySelector('.btn-de-acordo-rapido');
    if (btnDeAcordoRapido) {
        btnDeAcordoRapido.addEventListener('click', (e) => {
            e.stopPropagation();
            marcarDeAcordo(processo.numero, processo.estado);
        });
    }

    // Evento do botao destacar rapido
    const btnDestacarRapido = card.querySelector('.btn-destacar-rapido');
    if (btnDestacarRapido) {
        btnDestacarRapido.addEventListener('click', (e) => {
            e.stopPropagation();
            marcarDestacar(processo.numero, processo.estado);
        });
    }

    return card;
}

// Mover processo para De Acordo
async function marcarDeAcordo(numero, estadoOrigem) {
    if (estadoOrigem === 'de-acordo') return;

    try {
        const response = await fetch('/api/mover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                numero: numero,
                estado_origem: estadoOrigem,
                estado_destino: 'de-acordo'
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Erro ao mover processo');
        }

        // Fechar modal se o processo estava aberto
        if (processoSelecionado && processoSelecionado.numero === numero) {
            fecharModal();
        }

        // Recarregar
        await carregarProcessos();

    } catch (error) {
        console.error('Erro ao marcar de acordo:', error);
        alert('Erro: ' + error.message);
    }
}

// Mover processo para Destacar
async function marcarDestacar(numero, estadoOrigem) {
    if (estadoOrigem === 'destacar') return;

    try {
        const response = await fetch('/api/mover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                numero: numero,
                estado_origem: estadoOrigem,
                estado_destino: 'destacar'
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Erro ao mover processo');
        }

        // Fechar modal se o processo estava aberto
        if (processoSelecionado && processoSelecionado.numero === numero) {
            fecharModal();
        }

        // Recarregar
        await carregarProcessos();

    } catch (error) {
        console.error('Erro ao destacar:', error);
        alert('Erro: ' + error.message);
    }
}

// Handle drag end
async function handleDragEnd(evt) {
    const card = evt.item;
    const numero = card.dataset.numero;
    const estadoOrigem = card.dataset.estado;
    const estadoDestino = evt.to.closest('.kanban-coluna').dataset.estado;

    if (estadoOrigem === estadoDestino) return;

    try {
        const response = await fetch('/api/mover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                numero: numero,
                estado_origem: estadoOrigem,
                estado_destino: estadoDestino
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Erro ao mover processo');
        }

        // Atualizar estado local
        card.dataset.estado = estadoDestino;

        // Atualizar dados
        await carregarProcessos();

        // Se o processo movido estava selecionado, atualizar
        if (processoSelecionado && processoSelecionado.numero === numero) {
            processoSelecionado.estado = estadoDestino;
        }

    } catch (error) {
        console.error('Erro ao mover:', error);
        alert('Erro ao mover processo: ' + error.message);
        carregarProcessos();
    }
}

// Selecionar processo para preview
async function selecionarProcesso(processo) {
    processoSelecionado = processo;

    // Destacar card selecionado
    document.querySelectorAll('.kanban-card').forEach(c => c.classList.remove('selected'));
    document.querySelector(`[data-numero="${processo.numero}"]`)?.classList.add('selected');

    // Mostrar modal
    previewModal.classList.remove('hidden');
    previewTitulo.textContent = processo.numero;

    // Atualizar badge de ordem (numero na lista)
    if (processo.ordem) {
        previewOrdem.textContent = `#${processo.ordem}`;
        previewOrdem.style.display = 'inline-block';
    } else {
        previewOrdem.style.display = 'none';
    }

    // Atualizar badge de risco
    previewRisco.textContent = getIconeRisco(processo.risco);
    previewRisco.className = `risco-badge ${getClasseRisco(processo.risco)}`;

    // Mostrar/esconder botoes baseado no estado
    if (processo.estado === 'de-acordo') {
        btnDeAcordo.style.display = 'none';
        btnDestacar.style.display = 'block';
    } else if (processo.estado === 'destacar') {
        btnDeAcordo.style.display = 'block';
        btnDestacar.style.display = 'none';
    } else {
        btnDeAcordo.style.display = 'block';
        btnDestacar.style.display = 'block';
    }

    // Carregar conteudo
    try {
        const response = await fetch(`/api/processo/${processo.estado}/${processo.numero}`);
        conteudoCache = await response.json();

        // Renderizar colunas
        const ementa = conteudoCache.ementa || '*Ementa nao encontrada*';
        const analise = conteudoCache.analise || '*Analise ainda nao gerada. Execute o processamento.*';

        previewEmenta.innerHTML = marked.parse(ementa);
        previewAnalise.innerHTML = marked.parse(analise);

    } catch (error) {
        console.error('Erro ao carregar preview:', error);
        previewEmenta.innerHTML = '<p>Erro ao carregar conteudo.</p>';
        previewAnalise.innerHTML = '<p>Erro ao carregar conteudo.</p>';
    }
}

// Fechar modal
function fecharModal() {
    previewModal.classList.add('hidden');
    processoSelecionado = null;
    document.querySelectorAll('.kanban-card').forEach(c => c.classList.remove('selected'));
}

// Copiar numero do processo
async function copiarNumeroProcesso() {
    if (!processoSelecionado) return;

    try {
        await navigator.clipboard.writeText(processoSelecionado.numero);
        btnCopiarNumero.textContent = 'Copiado!';
        btnCopiarNumero.classList.add('copiado');

        setTimeout(() => {
            btnCopiarNumero.textContent = 'Copiar';
            btnCopiarNumero.classList.remove('copiado');
        }, 2000);

    } catch (error) {
        console.error('Erro ao copiar:', error);
    }
}

// Modal de Importacao
function abrirModalImportar() {
    importarModal.classList.remove('hidden');
    textoColar.value = '';
    fileInput.value = '';
}

function fecharModalImportar() {
    importarModal.classList.add('hidden');
}

// Mostrar loading
function mostrarLoading(mensagem) {
    loadingMessage.textContent = mensagem;
    loadingOverlay.classList.remove('hidden');
}

function esconderLoading() {
    loadingOverlay.classList.add('hidden');
}

// Importar arquivo
async function importarArquivo(file) {
    mostrarLoading('Importando lista...');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/importar/arquivo', {
            method: 'POST',
            body: formData
        });

        const resultado = await response.json();

        if (!response.ok) {
            throw new Error(resultado.detail || 'Erro ao importar');
        }

        esconderLoading();
        fecharModalImportar();

        // Mostrar resultado
        alert(`Importacao concluida!\n\nTotal: ${resultado.total}\nCriados: ${resultado.criados}\nErros: ${resultado.erros.length}`);

        // Recarregar
        await carregarProcessos();

    } catch (error) {
        esconderLoading();
        console.error('Erro ao importar:', error);
        alert('Erro ao importar: ' + error.message);
    }
}

// Limpar lista (arquivar todos os processos)
async function confirmarLimparLista() {
    // Contar total de processos
    let total = 0;
    for (const estado in processos) {
        total += processos[estado].length;
    }

    if (total === 0) {
        alert('Nao ha processos para arquivar.');
        return;
    }

    const confirmacao = confirm(
        `Deseja arquivar todos os ${total} processos?\n\n` +
        `Os processos serao movidos para a pasta "arquivados" ` +
        `e removidos do sistema.\n\n` +
        `Esta acao nao pode ser desfeita.`
    );

    if (!confirmacao) return;

    mostrarLoading('Arquivando processos...');

    try {
        const response = await fetch('/api/arquivar', {
            method: 'POST'
        });

        const resultado = await response.json();
        esconderLoading();

        if (resultado.sucesso || resultado.arquivados > 0) {
            alert(`${resultado.arquivados} processo(s) arquivado(s) com sucesso!`);
            carregarProcessos(); // Recarregar lista vazia
        } else {
            alert('Erro ao arquivar: ' + (resultado.mensagem || 'Erro desconhecido'));
        }
    } catch (error) {
        esconderLoading();
        console.error('Erro ao arquivar:', error);
        alert('Erro ao arquivar processos: ' + error.message);
    }
}

// Importar texto colado
async function importarTexto() {
    const texto = textoColar.value.trim();

    if (!texto) {
        alert('Cole o texto da lista primeiro.');
        return;
    }

    mostrarLoading('Importando lista...');

    try {
        const response = await fetch('/api/importar/texto', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto: texto })
        });

        const resultado = await response.json();

        if (!response.ok) {
            throw new Error(resultado.detail || 'Erro ao importar');
        }

        esconderLoading();
        fecharModalImportar();

        // Mostrar resultado
        alert(`Importacao concluida!\n\nTotal: ${resultado.total}\nCriados: ${resultado.criados}\nErros: ${resultado.erros.length}`);

        // Recarregar
        await carregarProcessos();

    } catch (error) {
        esconderLoading();
        console.error('Erro ao importar:', error);
        alert('Erro ao importar: ' + error.message);
    }
}

// Configurar eventos
function configurarEventos() {
    // Busca em tempo real (com debounce)
    let buscaTimeout;
    busca.addEventListener('input', () => {
        clearTimeout(buscaTimeout);
        buscaTimeout = setTimeout(renderizarKanban, 300);
    });

    // Atualizar
    btnAtualizar.addEventListener('click', carregarProcessos);

    // Limpar lista (arquivar todos)
    const btnLimpar = document.getElementById('btn-limpar');
    if (btnLimpar) {
        btnLimpar.addEventListener('click', confirmarLimparLista);
    }

    // Tema
    btnTema.addEventListener('click', alternarTema);

    // Importar
    btnImportar.addEventListener('click', abrirModalImportar);
    btnFecharImportar.addEventListener('click', fecharModalImportar);
    btnCancelarImportar.addEventListener('click', fecharModalImportar);

    // Confirmar importacao
    btnConfirmarImportar.addEventListener('click', () => {
        if (fileInput.files.length > 0) {
            importarArquivo(fileInput.files[0]);
        } else if (textoColar.value.trim()) {
            importarTexto();
        } else {
            alert('Selecione um arquivo ou cole o texto da lista.');
        }
    });

    // Drop zone - clique para selecionar arquivo
    dropZone.addEventListener('click', () => fileInput.click());

    // Drop zone - arrastar arquivo
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            fileInput.files = e.dataTransfer.files;
            dropZone.querySelector('p').textContent = file.name;
        }
    });

    // Input de arquivo
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            dropZone.querySelector('p').textContent = fileInput.files[0].name;
        }
    });

    // Fechar preview
    btnFecharPreview.addEventListener('click', fecharModal);

    // Botao home (voltar ao kanban)
    const btnHome = document.getElementById('btn-home');
    if (btnHome) {
        btnHome.addEventListener('click', (e) => {
            e.preventDefault();
            fecharModal();
        });
    }

    // Copiar numero do processo
    btnCopiarNumero.addEventListener('click', copiarNumeroProcesso);

    // Gerar relatorio PDF (todos os processos)
    btnRelatorio.addEventListener('click', gerarRelatorioDocx);

    // Gerar DOCX do processo individual
    btnPdfProcesso.addEventListener('click', gerarDocxProcesso);

    // De Acordo
    btnDeAcordo.addEventListener('click', () => {
        if (processoSelecionado) {
            marcarDeAcordo(processoSelecionado.numero, processoSelecionado.estado);
        }
    });

    // Destacar
    btnDestacar.addEventListener('click', () => {
        if (processoSelecionado) {
            marcarDestacar(processoSelecionado.numero, processoSelecionado.estado);
        }
    });

    // Atalho de teclado: Escape fecha modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!previewModal.classList.contains('hidden')) {
                fecharModal();
            } else if (!importarModal.classList.contains('hidden')) {
                fecharModalImportar();
            }
        }
    });

    // Fechar modal clicando fora
    importarModal.addEventListener('click', (e) => {
        if (e.target === importarModal) {
            fecharModalImportar();
        }
    });
}

// Atualizar contador total
function atualizarContador() {
    let total = 0;
    Object.values(processos).forEach(lista => total += lista.length);
    contador.textContent = `Processos: ${total}`;
}

// Gerar relatorio DOCX de todos os processos
async function gerarRelatorioDocx() {
    // Contar processos com analise
    let totalComAnalise = 0;
    for (const estado of Object.keys(processos)) {
        for (const proc of processos[estado]) {
            const conteudo = processosConteudo[proc.numero];
            if (conteudo && conteudo.analise) {
                totalComAnalise++;
            }
        }
    }

    if (totalComAnalise === 0) {
        alert('Nenhum processo possui analise. Analise os processos primeiro.');
        return;
    }

    const confirma = confirm(
        `Gerar relatorio Word com ${totalComAnalise} processo(s) analisado(s)?\n\n` +
        `Apenas processos com analise serao incluidos.`
    );

    if (!confirma) return;

    mostrarLoading('Gerando relatorio...');

    try {
        const url = '/api/relatorio?apenas_analisados=true';
        const response = await fetch(url);

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Erro ao gerar relatorio');
        }

        // Baixar o arquivo
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `relatorio_lista_trf_${new Date().toISOString().slice(0, 10)}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

        esconderLoading();

    } catch (error) {
        esconderLoading();
        console.error('Erro ao gerar relatorio:', error);
        alert('Erro ao gerar relatorio: ' + error.message);
    }
}

// Gerar DOCX de um processo individual
async function gerarDocxProcesso() {
    if (!processoSelecionado) return;

    mostrarLoading('Gerando documento...');

    try {
        const url = `/api/relatorio/${processoSelecionado.estado}/${processoSelecionado.numero}`;
        const response = await fetch(url);

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Erro ao gerar documento');
        }

        // Baixar o arquivo
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        const numeroLimpo = processoSelecionado.numero.replace(/\./g, '-');
        a.download = `analise_${numeroLimpo}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

        esconderLoading();

    } catch (error) {
        esconderLoading();
        console.error('Erro ao gerar documento:', error);
        alert('Erro ao gerar documento: ' + error.message);
    }
}
