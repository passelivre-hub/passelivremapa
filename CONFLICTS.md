# Resumo dos conflitos recentes

Durante o merge entre a branch `codex/troubleshoot-site-not-opening-on-git-pages-lnpyvj` e o código antigo, o Git apontou quatro áreas de conflito em `static/js/app.js`. Todas já estão resolvidas no commit atual:

1. **Ordem e normalização das faixas etárias** – A branch nova trazia `faixaOrder` para manter a ordem preferencial, enquanto o código antigo usava um objeto fixo com faixas pré-definidas. O resultado final mantém `faixaOrder` e normaliza dinamicamente os dados por faixa/tipo ao construir o painel demográfico. 【F:static/js/app.js†L2-L101】
2. **Rótulos de valores nos gráficos** – O plugin de rótulos passou a iterar por todos os datasets (necessário para barras empilhadas por tipo de deficiência), em vez de assumir apenas um dataset único. 【F:static/js/app.js†L130-L167】
3. **Criação de gráficos com datasets prontos** – O merge conciliou a criação automática de um dataset padrão com a possibilidade de receber conjuntos de dados já montados (como os vários tipos de deficiência). 【F:static/js/app.js†L169-L212】
4. **Carregamento de assets no GitHub Pages** – Entradas antigas buscavam os arquivos com caminhos absolutos; a versão atual adiciona `resolveAssetPath` e o usa para CSV e GeoJSON, garantindo que os assets sejam carregados mesmo quando o site é servido de uma subpasta no GitHub Pages. 【F:static/js/app.js†L291-L366】
