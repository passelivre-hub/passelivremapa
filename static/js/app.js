const mainGreen = '#A1C84D';
const defaultFaixas = { '0-12': 0, '13-17': 0, '18-59': 0, '60+': 0 };

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
  const faixas = { ...defaultFaixas };

  rows.forEach((row) => {
    const faixa = safeStr(row, 'faixa_etaria') || safeStr(row, 'faixa');
    if (!faixa || !(faixa in faixas)) return;
    faixas[faixa] = normalizeNumericField(row.quantidade);
  });

  return faixas;
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
      const dataset = data.datasets[0];
      const meta = chart.getDatasetMeta(0);
      if (!dataset || !meta) return;

      ctx.save();
      ctx.fillStyle = '#0f172a';
      ctx.font = 'bold 12px "Segoe UI", Arial, sans-serif';

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

      ctx.restore();
    },
  };

  Chart.register(valueLabelsPlugin);
}

function renderChart(ctxId, labels, data, title, type = 'bar', chartOptions = {}) {
  const ctx = document.getElementById(ctxId);
  if (!ctx) return null;

  return new Chart(ctx, {
    type,
    data: {
      labels,
      datasets: [
        {
          label: title,
          data,
          borderColor: mainGreen,
          backgroundColor: 'rgba(161, 200, 77, 0.2)',
          borderWidth: 3,
          tension: 0.3,
          fill: type === 'line',
        },
      ],
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

function renderPainel(demografiaFaixas, instituicoesResumo) {
  registerValueLabelsPlugin();

  const faixas = demografiaFaixas || {};
  const faixaLabels = Object.keys(faixas);
  const faixaValores = faixaLabels.map((f) => Number(faixas[f]) || 0);
  const totalFaixa = faixaValores.reduce((a, b) => a + b, 0);
  const totalFaixaEl = document.getElementById('totalFaixa');
  if (totalFaixaEl) totalFaixaEl.innerText = `${totalFaixa} carteiras`;
  renderChart('chartFaixa', faixaLabels, faixaValores, 'Por faixa etária');

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
