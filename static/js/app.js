const mainGreen = '#A1C84D';
const faixaOrder = ['0-12', '13-17', '18-29', '30-44', '45-59', '18-59', '60+', '0-17'];

function toNonNegativeInt(value, fallback = 0) {
  const parsed = parseInt(String(value ?? '').trim(), 10);
  return Number.isFinite(parsed) ? Math.max(parsed, 0) : fallback;
}

function normalizeNumericField(value) {
  return toNonNegativeInt(value, 0);
}

function safeStr(row, key) {
  return (row?.[key] ?? '').trim();
}

function buildDados(rows) {
  const instituicoes = {};
  const todosMunicipios = new Set();

  rows.forEach((row) => {
    const municipio = safeStr(row, 'municipio');
    if (!municipio) return;
    todosMunicipios.add(municipio);

    const instNome = safeStr(row, 'nome');
    if (!instNome) return;

    const inst = {
      nome: instNome,
      regiao: safeStr(row, 'regiao'),
      tipo: safeStr(row, 'tipo'),
      endereco: safeStr(row, 'endereco'),
      telefone: safeStr(row, 'telefone'),
      email: safeStr(row, 'email'),
      quantidade_ciptea: String(normalizeNumericField(row.quantidade_ciptea)),
      quantidade_cipf: String(normalizeNumericField(row.quantidade_cipf)),
      quantidade_passe_livre: String(normalizeNumericField(row.quantidade_passe_livre)),
    };

    if (!instituicoes[municipio]) {
      instituicoes[municipio] = [];
    }
    instituicoes[municipio].push(inst);
  });

  const municipiosStatus = {};
  todosMunicipios.forEach((municipio) => {
    const insts = instituicoes[municipio] || [];
    const tipos = [...new Set(insts.map((inst) => inst.tipo).filter(Boolean))];
    municipiosStatus[municipio] = tipos.length ? tipos.sort().join(' e ') : 'Nenhum';
  });

  return { municipiosStatus, municipiosInstituicoes: instituicoes };
}

function buildDemografia(rows) {
  const faixasSet = new Set();
  const tiposSet = new Set();
  const porTipo = {};
  const totalPorFaixa = {};

  rows.forEach((row) => {
    const faixa = safeStr(row, 'faixa_etaria') || safeStr(row, 'faixa');
    const tipo = safeStr(row, 'tipo_deficiencia') || safeStr(row, 'tipo');
    const quantidade = normalizeNumericField(row.quantidade);

    if (!faixa || !tipo) return;

    faixasSet.add(faixa);
    tiposSet.add(tipo);

    if (!porTipo[tipo]) porTipo[tipo] = {};
    porTipo[tipo][faixa] = (porTipo[tipo][faixa] || 0) + quantidade;
    totalPorFaixa[faixa] = (totalPorFaixa[faixa] || 0) + quantidade;
  });

  const faixaLabels = [
    ...faixaOrder.filter((faixa) => faixasSet.has(faixa)),
    ...[...faixasSet].filter((faixa) => !faixaOrder.includes(faixa)).sort(),
  ];

  const porTipoNormalizado = {};
  [...tiposSet].forEach((tipo) => {
    porTipoNormalizado[tipo] = {};
    faixaLabels.forEach((faixa) => {
      porTipoNormalizado[tipo][faixa] = porTipo?.[tipo]?.[faixa] || 0;
    });
  });

  const totalPorFaixaCompleto = {};
  faixaLabels.forEach((faixa) => {
    totalPorFaixaCompleto[faixa] = totalPorFaixa[faixa] || 0;
  });

  return {
    faixaLabels,
    tipos: [...tiposSet].sort(),
    porTipo: porTipoNormalizado,
    totalPorFaixa: totalPorFaixaCompleto,
  };
}

function resumirInstituicoes(instituicoes) {
  const totais = { ciptea: 0, cipf: 0, passe_livre: 0 };
  const regioes = {};

  Object.values(instituicoes).forEach((insts) => {
    insts.forEach((inst) => {
      const qtCiptea = toNonNegativeInt(inst.quantidade_ciptea, 0);
      const qtCipf = toNonNegativeInt(inst.quantidade_cipf, 0);
      const qtPasse = toNonNegativeInt(inst.quantidade_passe_livre, 0);

      totais.ciptea += qtCiptea;
      totais.cipf += qtCipf;
      totais.passe_livre += qtPasse;

      const regiao = (inst.regiao || '').trim();
      if (!regiao || ['não informada', 'nao informada', 'não informado', 'nao informado'].includes(regiao.toLowerCase())) {
        return;
      }

      regioes[regiao] = (regioes[regiao] || 0) + qtCiptea + qtCipf + qtPasse;
    });
  });

  return { totais, regioes };
}

function registerValueLabelsPlugin() {
  const valueLabelsPlugin = {
    id: 'valueLabels',
    afterDatasetsDraw(chart) {
      const { ctx, data, config } = chart;
      if (!data?.datasets?.length) return;

      ctx.save();
      ctx.fillStyle = '#0f172a';
      ctx.font = 'bold 12px "Segoe UI", Arial, sans-serif';

      data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (!meta) return;

        meta.data.forEach((element, index) => {
          const value = dataset.data[index];
          if (value === null || value === undefined) return;

          const isHorizontal = config.options.indexAxis === 'y';
          if (isHorizontal) {
            ctx.textAlign = 'left';
            ctx.textBaseline = 'middle';
            ctx.fillText(value, element.x + 12, element.y);
          } else {
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(value, element.x, element.y - 8);
          }
        });
      });

      ctx.restore();
    },
  };

  Chart.register(valueLabelsPlugin);
}

function renderChart(ctxId, labels, data, title, type = 'bar', chartOptions = {}) {
  const ctx = document.getElementById(ctxId);
  if (!ctx) return null;

  const isPrebuiltDataset =
    Array.isArray(data) && data.length && typeof data[0] === 'object' && data[0].data !== undefined;

  const datasets = isPrebuiltDataset
    ? data
    : [
        {
          label: title,
          data,
          borderColor: mainGreen,
          backgroundColor: 'rgba(161, 200, 77, 0.2)',
          borderWidth: 3,
          tension: type === 'line' ? 0.3 : 0,
          fill: type === 'line',
        },
      ];

  datasets.forEach((dataset) => {
    if (!dataset.borderColor) dataset.borderColor = mainGreen;
    if (!dataset.backgroundColor) dataset.backgroundColor = 'rgba(161, 200, 77, 0.15)';
    if (dataset.borderWidth === undefined) dataset.borderWidth = 3;
    if (dataset.tension === undefined) dataset.tension = type === 'line' ? 0.3 : 0;
    if (dataset.fill === undefined) dataset.fill = type === 'line';
  });

  return new Chart(ctx, {
    type,
    data: {
      labels,
      datasets,
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      layout: { padding: { right: 30, top: 10, left: 4, bottom: 6 } },
      scales: { y: { beginAtZero: true } },
      indexAxis: 'x',
      ...chartOptions,
    },
  });
}

function renderPainel(demografia, instituicoesResumo) {
  registerValueLabelsPlugin();

  const demografiaData = demografia || { faixaLabels: [], tipos: [], porTipo: {}, totalPorFaixa: {} };
  const faixaLabels = demografiaData.faixaLabels;
  const faixaValores = faixaLabels.map((faixa) => Number(demografiaData.totalPorFaixa[faixa]) || 0);
  const totalFaixa = faixaValores.reduce((a, b) => a + b, 0);
  const totalFaixaEl = document.getElementById('totalFaixa');
  if (totalFaixaEl) totalFaixaEl.innerText = `${totalFaixa} carteiras`;

  const tipoColors = ['#A1C84D', '#5B8DEF', '#F59E0B', '#EC4899', '#10B981', '#8B5CF6'];
  const datasets = demografiaData.tipos.map((tipo, index) => ({
    label: tipo,
    data: faixaLabels.map((faixa) => demografiaData?.porTipo?.[tipo]?.[faixa] || 0),
    backgroundColor: tipoColors[index % tipoColors.length],
    borderColor: tipoColors[index % tipoColors.length],
  }));

  renderChart('chartFaixa', faixaLabels, datasets, 'Por faixa etária', 'bar', {
    plugins: { legend: { display: true, position: 'top' } },
    scales: { x: { stacked: true }, y: { beginAtZero: true, stacked: true } },
    layout: { padding: { right: 30, top: 10, left: 4, bottom: 6 } },
  });

  const totais = instituicoesResumo?.totais || {};
  const tipoLabels = ['CIPTEA', 'CIPF', 'Passe Livre'];
  const tipoValores = [totais.ciptea || 0, totais.cipf || 0, totais.passe_livre || 0];
  const totalTipos = tipoValores.reduce((a, b) => a + b, 0);
  const totalTiposEl = document.getElementById('totalTipos');
  if (totalTiposEl) totalTiposEl.innerText = `${totalTipos} emissões`;
  renderChart('chartTipos', tipoLabels, tipoValores, 'Por tipo de carteira');

  const regioes = instituicoesResumo?.regioes || {};
  const regiaoLabels = Object.keys(regioes).length ? Object.keys(regioes) : ['Sem dados'];
  const regiaoValores = regiaoLabels.map((r) => regioes[r] || 0);
  const totalRegiao = regiaoValores.reduce((a, b) => a + b, 0);
  const totalRegiaoEl = document.getElementById('totalRegiao');
  if (totalRegiaoEl) totalRegiaoEl.innerText = `${totalRegiao} carteiras`;
  renderChart('chartRegiao', regiaoLabels, regiaoValores, 'Carteiras por região', 'bar', {
    indexAxis: 'y',
    scales: { x: { beginAtZero: true } },
    layout: { padding: { right: 50, top: 10, left: 4, bottom: 6 } },
  });
}

function getColor(status) {
  return status && status !== 'Nenhum' ? mainGreen : '#e5e7eb';
}

function buildPopupHtml(nome, status, municipiosInstituicoes) {
  let adjustedStatus = status;
  if (status === 'Passe Livre' || status === 'CIPTEA e Passe Livre' || status === 'Ambos') {
    adjustedStatus = status === 'Passe Livre' ? 'CIPF e Passe Livre' : 'CIPTEA, Passe Livre e CIPF';
  }

  let popupHtml = `<b>${nome}</b><br>Status: ${adjustedStatus}`;

  if (municipiosInstituicoes[nome]) {
    popupHtml += '<br><br><b>Instituições credenciadas:</b><ul>';
    municipiosInstituicoes[nome].forEach((inst) => {
      popupHtml += `
        <li>
          <b>${inst.nome}</b> (${inst.tipo})<br>
          ${inst.endereco}<br>
          Tel: ${inst.telefone}<br>
          Email: ${inst.email}<br>
          Quantidade: CIPTEA: ${inst.quantidade_ciptea || 0}, CIPF: ${inst.quantidade_cipf || 0}, Passe Livre: ${inst.quantidade_passe_livre || 0}
        </li>
      `;
    });
    popupHtml += '</ul>';
  }

  return popupHtml;
}

function resolveAssetPath(fileName) {
  const base = window.location.pathname.endsWith('/index.html')
    ? window.location.pathname.replace(/\/index\.html$/, '/')
    : window.location.pathname.endsWith('/')
      ? window.location.pathname
      : `${window.location.pathname.replace(/[^/]*$/, '')}`;

  return `${base}${fileName}`;
}

async function setupMap(municipiosStatus, municipiosInstituicoes) {
  const map = L.map('map').setView([-27.2, -50.5], 7);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap',
  }).addTo(map);

  const response = await fetch(resolveAssetPath('sc_municipios.geojson'));
  const data = await response.json();

  const geoLayer = L.geoJson(data, {
    style: (feature) => ({
      color: '#333',
      weight: 1,
      fillColor: getColor(municipiosStatus[feature.properties.name] || 'Nenhum'),
      fillOpacity: 0.65,
    }),
    onEachFeature: (feature, layer) => {
      const nome = feature.properties.name;
      const status = municipiosStatus[nome] || 'Nenhum';
      const popupHtml = buildPopupHtml(nome, status, municipiosInstituicoes);

      layer.bindPopup(popupHtml);
      layer.featureStatus = status;
    },
  }).addTo(map);

  return { map, geoLayer };
}

function setupSearch(map, geoLayer) {
  const searchBox = document.getElementById('searchBox');
  if (!searchBox) return;

  searchBox.addEventListener('keyup', (e) => {
    if (e.key !== 'Enter' || !geoLayer) return;

    const query = searchBox.value.toLowerCase();
    geoLayer.eachLayer((layer) => {
      if (layer.feature?.properties?.name?.toLowerCase() === query) {
        map.fitBounds(layer.getBounds());
        layer.openPopup();
      }
    });
  });
}

function parseCsv(text) {
  return new Promise((resolve, reject) => {
    Papa.parse(text, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => resolve(results.data),
      error: reject,
    });
  });
}

async function fetchCsvData(path) {
  const response = await fetch(resolveAssetPath(path));
  if (!response.ok) {
    throw new Error(`Não foi possível carregar ${path}`);
  }
  const text = await response.text();
  return parseCsv(text);
}

async function init() {
  try {
    const [dadosRows, demografiaRows] = await Promise.all([
      fetchCsvData('dados.csv'),
      fetchCsvData('demografia.csv').catch(() => []),
    ]);

    const { municipiosStatus, municipiosInstituicoes } = buildDados(dadosRows);
    const demografiaFaixas = buildDemografia(demografiaRows || []);
    const instituicoesResumo = resumirInstituicoes(municipiosInstituicoes);

    renderPainel(demografiaFaixas, instituicoesResumo);

    const { map, geoLayer } = await setupMap(municipiosStatus, municipiosInstituicoes);
    setupSearch(map, geoLayer);
  } catch (error) {
    console.error('Erro ao carregar dados', error);
    const existingNotice = document.getElementById('loadError');
    if (!existingNotice) {
      const notice = document.createElement('div');
      notice.id = 'loadError';
      notice.style.position = 'absolute';
      notice.style.top = '20px';
      notice.style.left = '50%';
      notice.style.transform = 'translateX(-50%)';
      notice.style.background = '#fee2e2';
      notice.style.color = '#991b1b';
      notice.style.padding = '12px 16px';
      notice.style.border = '1px solid #fecaca';
      notice.style.borderRadius = '10px';
      notice.style.boxShadow = '0 8px 20px rgba(0,0,0,0.15)';
      notice.style.zIndex = '1200';
      notice.innerHTML = `
        <strong>Erro ao carregar dados.</strong><br>
        Confirme que os arquivos CSV e GeoJSON estão publicados na mesma pasta do <code>index.html</code> (GitHub Pages: fonte "Root").
      `;
      document.body.appendChild(notice);
    }
  }
}

window.addEventListener('load', init);
