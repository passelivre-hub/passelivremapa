# passelivremapa

Mapa interativo de instituições credenciadas para CIPTEA, CIPF e Passe Livre em SC.

## Como publicar no GitHub Pages

A página agora é 100% estática e lê os dados diretamente dos arquivos presentes no repositório:

- `dados.csv`: instituições por município.
- `demografia.csv`: distribuição por faixa etária.
- `sc_municipios.geojson`: geometria dos municípios de SC.

Para publicar:

1. Faça push para o branch principal.
2. Ative o GitHub Pages nas configurações do repositório, usando a raiz (`/`) como fonte.
3. Aguarde a publicação; o `index.html` na raiz carregará os dados dos CSV/GeoJSON.

Se atualizar os CSV ou o GeoJSON, o painel recarrega automaticamente com os novos números.
