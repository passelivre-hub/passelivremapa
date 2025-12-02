const mainGreen = '#A1C84D';
const defaultFaixas = { '0-12': 0, '13-17': 0, '18-59': 0, '60+': 0 };
const defaultFaixaRanges = [
  { label: '0-12', start: 0, end: 12 },
  { label: '13-17', start: 13, end: 17 },
  { label: '18-59', start: 18, end: 59 },
  { label: '60+', start: 60, end: Infinity },
];

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

function parseFaixaRange(faixa) {
  const normalized = faixa.replace(/\s+/g, '');
  const betweenMatch = normalized.match(/^(\d+)-(\d+)$/);
  if (betweenMatch) {
    return { start: Number(betweenMatch[1]), end: Number(betweenMatch[2]) };
  }

  const plusMatch = normalized.match(/^(\d+)\+$/);
  if (plusMatch) {
    return { start: Number(plusMatch[1]), end: Infinity };
  }

  return null;
}

function splitQuantidadeAcrossDefaultRanges(range, quantidade) {
  const faixasValores = defaultFaixaRanges.map(({ label }) => ({ label, valor: 0 }));
  if (!range) return faixasValores;

  if (!Number.isFinite(range.end)) {
    const faixaDestino = defaultFaixaRanges.find((faixa) => range.start >= faixa.start && range.start <= faixa.end);
    if (faixaDestino) {
      const entry = faixasValores.find((f) => f.label === faixaDestino.label);
      entry.valor += quantidade;
    }
    return faixasValores;
  }

  const totalIntervalo = range.end - range.start + 1;
  if (totalIntervalo <= 0) return faixasValores;

  const rawShares = defaultFaixaRanges.map((faixa) => {
    const overlapStart = Math.max(range.start, faixa.start);
    const overlapEnd = Math.min(range.end, faixa.end);
    const hasOverlap = overlapStart <= overlapEnd;
    const overlapLength = hasOverlap ? overlapEnd - overlapStart + 1 : 0;
    const valor = (quantidade * overlapLength) / totalIntervalo;
    return { label: faixa.label, raw: valor };
  });

  const roundedShares = rawShares.map((share) => ({
    label: share.label,
    valor: Math.round(share.raw),
  }));

  const roundedTotal = roundedShares.reduce((sum, item) => sum + item.valor, 0);
  const diff = quantidade - roundedTotal;
  if (diff !== 0) {
    const adjustmentTarget = rawShares.reduce((max, current) => (current.raw > max.raw ? current : max), rawShares[0]);
    const targetEntry = roundedShares.find((share) => share.label === adjustmentTarget.label);
    if (targetEntry) targetEntry.valor += diff;
  }

  roundedShares.forEach(({ label, valor }) => {
    const entry = faixasValores.find((f) => f.label === label);
    entry.valor += Math.max(valor, 0);
  });

  return faixasValores;
}

function buildDemografia(rows) {
  const faixas = { ...defaultFaixas };
  const porTipo = {};

  rows.forEach((row) => {
    const faixaLabel = safeStr(row, 'faixa_etaria') || safeStr(row, 'faixa');
    const faixaRange = faixaLabel ? parseFaixaRange(faixaLabel) : null;
    const quantidade = normalizeNumericField(row.quantidade);
    if (!faixaRange || quantidade <= 0) return;

    const tipo = safeStr(row, 'tipo_deficiencia') || 'Outros';
    if (!porTipo[tipo]) {
      porTipo[tipo] = { ...defaultFaixas };
    }

    const distribuicoes = splitQuantidadeAcrossDefaultRanges(faixaRange, quantidade);
    distribuicoes.forEach(({ label, valor }) => {
      faixas[label] = (faixas[label] || 0) + valor;
      porTipo[tipo][label] = (porTipo[tipo][label] || 0) + valor;
    });
  });

  return { totais: faixas, porTipo };
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
      const { ctx, data, options } = chart;
      if (!data?.datasets?.length) return;

      ctx.save();
      ctx.fillStyle = '#0f172a';
      ctx.font = 'bold 12px "Segoe UI", Arial, sans-serif';

      const indexAxis = options.indexAxis || 'x';
      const xScale = chart.scales.x;
      const yScale = chart.scales.y;

      data.labels.forEach((label, index) => {
        const total = data.datasets.reduce((sum, ds) => sum + (Number(ds.data?.[index]) || 0), 0);
        if (total === null || total === undefined) return;

        if (indexAxis === 'y') {
          const y = yScale.getPixelForValue(index);
          const x = xScale.getPixelForValue(total) + 12;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText(total, x, y);
        } else {
          const x = xScale.getPixelForValue(index);
          const y = yScale.getPixelForValue(total) - 8;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'bottom';
          ctx.fillText(total, x, y);
        }
      });

      ctx.restore();
    },
  };

  Chart.register(valueLabelsPlugin);
}

function renderChart(ctxId, labels, dataOrDatasets, title, type = 'bar', chartOptions = {}) {
  const ctx = document.getElementById(ctxId);
  if (!ctx) return null;

  const isDatasetArray =
    Array.isArray(dataOrDatasets) &&
    dataOrDatasets.length > 0 &&
    dataOrDatasets.every((entry) => entry && typeof entry === 'object' && Array.isArray(entry.data));

  const datasets = isDatasetArray
    ? dataOrDatasets
    : [
        {
          label: title,
          data: Array.isArray(dataOrDatasets) ? dataOrDatasets : [],
          borderColor: mainGreen,
          backgroundColor: 'rgba(161, 200, 77, 0.2)',
          borderWidth: 3,
          tension: 0.3,
          fill: type === 'line',
        },
      ];

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

  const faixas = demografia?.totais || defaultFaixas;
  const faixaLabels = defaultFaixaRanges.map((faixa) => faixa.label);
  const faixaValores = faixaLabels.map((f) => Number(faixas[f]) || 0);
  const totalFaixa = faixaValores.reduce((a, b) => a + b, 0);
  const totalFaixaEl = document.getElementById('totalFaixa');
  if (totalFaixaEl) totalFaixaEl.innerText = `${totalFaixa} carteiras`;
  const faixasPorTipo = demografia?.porTipo || {};
  const tiposDeficiencia = Object.keys(faixasPorTipo);
  const palette = [
    '#A1C84D',
    '#5E854E',
    '#84B18B',
    '#3E6654',
    '#C4DFA0',
    '#4A5A30',
  ];
  const stackedDatasets = tiposDeficiencia.length
    ? tiposDeficiencia.map((tipo, idx) => ({
        label: tipo,
        data: faixaLabels.map((label) => faixasPorTipo[tipo][label] || 0),
        backgroundColor: palette[idx % palette.length],
        borderWidth: 1,
        borderColor: palette[idx % palette.length],
      }))
    : [
        {
          label: 'Total',
          data: faixaValores,
          backgroundColor: 'rgba(161, 200, 77, 0.2)',
          borderColor: mainGreen,
          borderWidth: 3,
        },
      ];
  renderChart('chartFaixa', faixaLabels, stackedDatasets, 'Por faixa etária', 'bar', {
    scales: {
      x: { stacked: true },
      y: { stacked: true, beginAtZero: true },
    },
    plugins: { legend: { display: true } },
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

async function setupMap(municipiosStatus, municipiosInstituicoes) {
  const map = L.map('map').setView([-27.2, -50.5], 7);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap',
  }).addTo(map);

  const response = await fetch('sc_municipios.geojson');
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
  const response = await fetch(path);
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
    alert('Não foi possível carregar os dados. Verifique se os arquivos CSV e GeoJSON estão acessíveis.');
  }
}

window.addEventListener('load', init);
