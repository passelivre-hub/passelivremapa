# passelivremapa
Mapa interativo de instituições credenciadas para CIPTEA, CIPF e Passe Livre em SC

## ETL a partir do relatório CSV
Um script de apoio (`scripts/etl_relatorio.py`) processa o CSV bruto emitido pelo sistema
e preenche os contadores usados pelo painel:

- **Entradas obrigatórias**: colunas de Instituição Credenciadora, Idade e Deficiência.
- **Faixas etárias**: 0-12, 13-17, 18-59 e 60+ (mantidas separadamente para cada tipo).
- **Mapeamentos configuráveis**:
  - `scripts/instituicoes_equivalencias.json`: dicionário para aproximar nomes do relatório
    aos nomes oficiais cadastrados em `dados.csv`.
  - `scripts/deficiencias_para_tipo.json`: relaciona valores da coluna Deficiência aos
    tipos esperados pelo painel (`ciptea`, `cipf`, `passe_livre`).
- **Saídas**: atualiza `dados.csv`, `demografia.csv` (colunas por tipo) e registra pendências
  não mapeadas em `scripts/etl_relatorio_pendencias.csv` para revisão manual.

Execução padrão (usa os caminhos acima por conveniência):

```bash
python scripts/etl_relatorio.py --input caminho/do/relatorio.csv
```
