"""
Processa o CSV bruto do relatório e preenche os contadores de carteiras
(CIPTEA, CIPF, Passe Livre) e faixas etárias agrupadas (0-12, 13-17, 18-59, 60+).

Fluxo:
1. Lê o relatório de entrada (colunas necessárias: Instituição Credenciadora, Idade, Deficiência).
2. Usa o dicionário de equivalências de instituições para casar os nomes do relatório com os
   nomes oficiais cadastrados em `dados.csv`.
3. Mapeia a coluna Deficiência para os tipos `ciptea`, `cipf` ou `passe_livre` via
   `deficiencias_para_tipo.json`.
4. Classifica idade nas faixas 0-12, 13-17, 18-59 e 60+.
5. Gera novos `dados.csv` (contagens por instituição) e `demografia.csv` (contagens por faixa e tipo).

Linhas que não puderem ser mapeadas ficam registradas em um CSV auxiliar para facilitar
os ajustes no dicionário de equivalências.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RELATORIO = REPO_ROOT / "relatorio.csv"
DEFAULT_DADOS = REPO_ROOT / "dados.csv"
DEFAULT_DEMOGRAFIA = REPO_ROOT / "demografia.csv"
DEFAULT_EQUIVALENCIAS = Path(__file__).resolve().parent / "instituicoes_equivalencias.json"
DEFAULT_MAPA_DEFICIENCIAS = Path(__file__).resolve().parent / "deficiencias_para_tipo.json"
DEFAULT_PENDENCIAS = Path(__file__).resolve().parent / "etl_relatorio_pendencias.csv"

AGE_BINS: List[Tuple[str, int, int | None]] = [
    ("0-12", 0, 12),
    ("13-17", 13, 17),
    ("18-59", 18, 59),
    ("60+", 60, None),
]
TIPOS = ("ciptea", "cipf", "passe_livre")


def normalize_text(texto: str) -> str:
    """Remove acentuação, capitaliza e comprime espaços."""
    texto = texto or ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return " ".join(texto.upper().split())


def carregar_json(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        conteudo = json.load(f)
    return {normalize_text(k): str(v) for k, v in conteudo.items()}


def detectar_delimitador(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as f:
        amostra = f.read(2048)
        try:
            dialect = csv.Sniffer().sniff(amostra)
            return dialect.delimiter
        except csv.Error:
            return ","


def ler_relatorio(path: Path) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
    delimitador = detectar_delimitador(path)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimitador)
        linhas = [row for row in reader]
        campos = {normalize_text(h): h for h in (reader.fieldnames or [])}
    return linhas, campos


def escolher_coluna(campos_normalizados: Dict[str, str], candidatos: Iterable[str]) -> str:
    for candidato in candidatos:
        chave = normalize_text(candidato).replace(" ", "")
        for normalizado, original in campos_normalizados.items():
            if normalize_text(normalizado).replace(" ", "") == chave:
                return original
    raise ValueError(f"Não encontrei a coluna obrigatória: {', '.join(candidatos)}")


def parse_idade(valor: str) -> int | None:
    match = re.search(r"(\d+)", valor or "")
    return int(match.group(1)) if match else None


def faixa_etaria(idade: int | None) -> str | None:
    if idade is None:
        return None
    for faixa, minimo, maximo in AGE_BINS:
        if idade >= minimo and (maximo is None or idade <= maximo):
            return faixa
    return None


def carregar_instituicoes_base(path: Path) -> Tuple[List[Dict[str, str]], Dict[str, Dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        linhas = []
        for row in reader:
            for tipo in TIPOS:
                row[f"quantidade_{tipo}"] = 0
            linhas.append(row)
    lookup = {normalize_text(row.get("nome", "")): row for row in linhas if row.get("nome")}
    return linhas, lookup


def aplicar_equivalencias(nome_relatorio: str, equivalencias: Dict[str, str], lookup: Dict[str, Dict[str, str]]):
    normalizado = normalize_text(nome_relatorio)
    if not normalizado:
        return None, normalizado

    if normalizado in equivalencias:
        alvo = normalize_text(equivalencias[normalizado])
        if alvo in lookup:
            return lookup[alvo], alvo

    if normalizado in lookup:
        return lookup[normalizado], normalizado

    return None, normalizado


def mapear_deficiencia(valor: str, mapa: Dict[str, str]) -> str | None:
    normalizado = normalize_text(valor)
    if not normalizado:
        return None
    if normalizado in mapa:
        return mapa[normalizado]

    for chave, tipo in mapa.items():
        if chave in normalizado:
            return tipo
    return None


def preparar_demografia() -> Dict[str, Dict[str, int]]:
    return {faixa: {tipo: 0 for tipo in TIPOS} for faixa, _, _ in AGE_BINS}


def escrever_csv(path: Path, linhas: List[Dict[str, str]], fieldnames: List[str]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(linhas)


def salvar_pendencias(path: Path, pendencias: List[Dict[str, str]]):
    if not pendencias:
        return
    fieldnames = ["instituicao_original", "deficiencia_original", "idade", "motivo"]
    escrever_csv(path, pendencias, fieldnames)


def processar_relatorio(
    relatorio: Path,
    dados_path: Path,
    demografia_path: Path,
    equivalencias_path: Path,
    mapa_deficiencias_path: Path,
    pendencias_path: Path,
):
    linhas_relatorio, campos = ler_relatorio(relatorio)
    col_inst = escolher_coluna(campos, ["instituicao credenciadora", "instituição credenciadora", "instituicao"])
    col_idade = escolher_coluna(campos, ["idade"])
    col_def = escolher_coluna(campos, ["deficiencia", "deficiência", "deficiencia / condicao"])

    equivalencias = carregar_json(equivalencias_path)
    mapa_deficiencias = carregar_json(mapa_deficiencias_path)

    instituicoes, lookup = carregar_instituicoes_base(dados_path)
    demografia = preparar_demografia()
    pendencias: List[Dict[str, str]] = []

    for row in linhas_relatorio:
        inst_row, inst_normalizado = aplicar_equivalencias(row.get(col_inst, ""), equivalencias, lookup)
        idade = parse_idade(row.get(col_idade, ""))
        faixa = faixa_etaria(idade)
        tipo = mapear_deficiencia(row.get(col_def, ""), mapa_deficiencias)

        if not inst_row:
            pendencias.append({
                "instituicao_original": row.get(col_inst, ""),
                "deficiencia_original": row.get(col_def, ""),
                "idade": row.get(col_idade, ""),
                "motivo": "instituicao_nao_encontrada",
            })
            continue

        if tipo is None:
            pendencias.append({
                "instituicao_original": row.get(col_inst, ""),
                "deficiencia_original": row.get(col_def, ""),
                "idade": row.get(col_idade, ""),
                "motivo": "deficiencia_nao_mapeada",
            })
            continue

        if faixa is None:
            pendencias.append({
                "instituicao_original": row.get(col_inst, ""),
                "deficiencia_original": row.get(col_def, ""),
                "idade": row.get(col_idade, ""),
                "motivo": "idade_invalida",
            })
            continue

        inst_row[f"quantidade_{tipo}"] = inst_row.get(f"quantidade_{tipo}", 0) + 1
        demografia[faixa][tipo] += 1

    # Grava dados.csv com os campos originais preservados
    if instituicoes:
        fieldnames = list(instituicoes[0].keys())
        for linha in instituicoes:
            for tipo in TIPOS:
                chave = f"quantidade_{tipo}"
                linha[chave] = str(linha.get(chave, 0))
        escrever_csv(dados_path, instituicoes, fieldnames)

    # Grava demografia.csv com colunas por tipo
    demografia_linhas = [
        {
            "faixa_etaria": faixa,
            "ciptea": demografia[faixa]["ciptea"],
            "cipf": demografia[faixa]["cipf"],
            "passe_livre": demografia[faixa]["passe_livre"],
        }
        for faixa, _, _ in AGE_BINS
    ]
    escrever_csv(demografia_path, demografia_linhas, ["faixa_etaria", "ciptea", "cipf", "passe_livre"])

    salvar_pendencias(pendencias_path, pendencias)
    print(f"Processadas {len(linhas_relatorio)} linhas.")
    print(f"Pendências registradas: {len(pendencias)} (arquivo: {pendencias_path})")
    print(f"dados.csv atualizado em: {dados_path}")
    print(f"demografia.csv atualizada em: {demografia_path}")


def main():
    parser = argparse.ArgumentParser(description="Processa o relatório CSV e atualiza os dados do painel.")
    parser.add_argument("--input", "-i", dest="relatorio", default=DEFAULT_RELATORIO, type=Path,
                        help="Caminho do CSV bruto exportado pelo sistema.")
    parser.add_argument("--dados", dest="dados", default=DEFAULT_DADOS, type=Path,
                        help="Caminho do dados.csv a ser sobrescrito.")
    parser.add_argument("--demografia", dest="demografia", default=DEFAULT_DEMOGRAFIA, type=Path,
                        help="Caminho do demografia.csv a ser sobrescrito.")
    parser.add_argument("--equivalencias", dest="equivalencias", default=DEFAULT_EQUIVALENCIAS, type=Path,
                        help="JSON com mapeamento de nomes do relatório para nomes oficiais.")
    parser.add_argument("--mapa-deficiencias", dest="mapa_deficiencias", default=DEFAULT_MAPA_DEFICIENCIAS, type=Path,
                        help="JSON que relaciona a coluna Deficiência ao tipo (ciptea, cipf, passe_livre).")
    parser.add_argument("--pendencias", dest="pendencias", default=DEFAULT_PENDENCIAS, type=Path,
                        help="Arquivo CSV onde serão registradas linhas não mapeadas.")

    args = parser.parse_args()
    processar_relatorio(
        args.relatorio,
        args.dados,
        args.demografia,
        args.equivalencias,
        args.mapa_deficiencias,
        args.pendencias,
    )


if __name__ == "__main__":
    main()
