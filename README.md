# passelivremapa

Mapa interativo de instituições credenciadas para CIPTEA, CIPF e Passe Livre em SC.

## Como publicar e acessar no GitHub Pages

A página agora é 100% estática e lê os dados diretamente dos arquivos presentes no repositório:

- `dados.csv`: instituições por município.
- `demografia.csv`: distribuição por faixa etária e tipo de deficiência (colunas `faixa_etaria`, `tipo_deficiencia` e `quantidade`).
- `sc_municipios.geojson`: geometria dos municípios de SC.

Para publicar e abrir o painel estático:

1. Faça push para o branch principal (os arquivos `index.html`, `static/js/app.js` e os dados já estão na raiz).
2. Ative o GitHub Pages nas configurações do repositório, escolhendo a **raiz (`/`)** como fonte (não use `/docs`).
3. Aguarde a publicação e acesse `https://<usuario>.github.io/<repositorio>/` — o `index.html` é carregado direto da raiz e lê os arquivos `dados.csv`, `demografia.csv` e `sc_municipios.geojson` automaticamente.

Se você atualizar os CSV ou o GeoJSON, basta fazer novo push; o painel no Pages recarrega com os números mais recentes assim que a publicação terminar.

> ⚠️ O GitHub Pages só serve a versão estática do mapa. O painel administrativo continua exigindo o backend Flask executando em algum servidor (local ou hospedagem Python).

## Como acessar o admin

O painel administrativo exige o backend Flask (não funciona no GitHub Pages, pois é apenas a versão estática). Para usá-lo:

1. Instale as dependências (`pip install -r requirements.txt`).
2. Defina as credenciais via variáveis de ambiente, se quiser mudar o padrão:
   - `ADMIN_USER` (padrão: `admin`)
   - `ADMIN_PASS` (padrão: `fcee2025`)
   - `SECRET_KEY` (recomendado trocar em produção)
3. Suba o servidor localmente (`python app.py`) ou em um serviço que execute Python (Render, Railway, etc.).
4. Acesse `http://localhost:5000/login` e faça login; a tela de administração estará em `/admin`.
