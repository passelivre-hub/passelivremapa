import csv
import os
from typing import Dict, List, Tuple

CSV_FILE = os.environ.get("CSV_FILE", "dados.csv")
DEMO_FILE = os.environ.get("DEMO_FILE", "demografia.csv")


def to_non_negative_int(value, default=0):
    try:
        return max(int(str(value).strip() or default), 0)
    except (TypeError, ValueError):
        return default


def normalize_numeric_field(value):
    return str(to_non_negative_int(value, 0))


def load_dados() -> Tuple[Dict[str, str], Dict[str, List[dict]], Dict[str, int]]:
    instituicoes: Dict[str, List[dict]] = {}
    todos_municipios = set()
    municipios_totais: Dict[str, int] = {}

    def safe_str(row, key):
        return (row.get(key) or "").strip()

    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                municipio = safe_str(row, "municipio")
                if not municipio:
                    continue
                todos_municipios.add(municipio)

                inst_nome = safe_str(row, "nome")
                if inst_nome:
                    qt_ciptea = to_non_negative_int(row.get("quantidade_ciptea", 0), 0)
                    qt_cipf = to_non_negative_int(row.get("quantidade_cipf", 0), 0)
                    qt_passe = to_non_negative_int(row.get("quantidade_passe_livre", 0), 0)

                    inst = {
                        "nome": inst_nome,
                        "regiao": safe_str(row, "regiao"),
                        "tipo": safe_str(row, "tipo"),
                        "endereco": safe_str(row, "endereco"),
                        "telefone": safe_str(row, "telefone"),
                        "email": safe_str(row, "email"),
                        "quantidade_ciptea": normalize_numeric_field(qt_ciptea),
                        "quantidade_cipf": normalize_numeric_field(qt_cipf),
                        "quantidade_passe_livre": normalize_numeric_field(qt_passe),
                    }
                    if municipio not in instituicoes:
                        instituicoes[municipio] = []
                    instituicoes[municipio].append(inst)

                    municipios_totais[municipio] = municipios_totais.get(municipio, 0) + qt_ciptea + qt_cipf + qt_passe

    municipios_status: Dict[str, str] = {}
    for municipio in todos_municipios:
        insts = instituicoes.get(municipio, [])
        tipos = set(inst["tipo"] for inst in insts)
        if not tipos:
            status = "Nenhum"
        else:
            status = " e ".join(sorted(tipos))
        municipios_status[municipio] = status

    return municipios_status, instituicoes, municipios_totais


def load_demografia_rows() -> List[dict]:
    registros: List[dict] = []
    if os.path.exists(DEMO_FILE):
        with open(DEMO_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tipo = (row.get("tipo_deficiencia") or "").strip()
                faixa = (row.get("faixa_etaria") or row.get("faixa") or "").strip()
                quantidade = to_non_negative_int(row.get("quantidade", 0), 0)

                if not tipo or not faixa:
                    continue

                registros.append({
                    "tipo_deficiencia": tipo,
                    "faixa_etaria": faixa,
                    "quantidade": quantidade,
                })

    return registros


def preparar_demografia_por_deficiencia(registros: List[dict]):
    faixas_padrao = ["0-12", "13-17", "18-59", "60+"]
    tipos = sorted({r["tipo_deficiencia"] for r in registros})
    estrutura = {tipo: {faixa: 0 for faixa in faixas_padrao} for tipo in tipos}

    total = 0
    for registro in registros:
        tipo = registro["tipo_deficiencia"]
        faixa = registro["faixa_etaria"]
        if faixa not in faixas_padrao:
            continue
        quantidade = to_non_negative_int(registro["quantidade"], 0)
        estrutura[tipo][faixa] = estrutura[tipo].get(faixa, 0) + quantidade
        total += quantidade

    return {
        "faixas": faixas_padrao,
        "tipos": tipos,
        "data": estrutura,
        "total": total,
    }


def resumir_instituicoes(instituicoes: Dict[str, List[dict]]):
    totais = {"ciptea": 0, "cipf": 0, "passe_livre": 0}
    regioes: Dict[str, int] = {}

    for insts in instituicoes.values():
        for inst in insts:
            qt_ciptea = to_non_negative_int(inst.get("quantidade_ciptea", 0), 0)
            qt_cipf = to_non_negative_int(inst.get("quantidade_cipf", 0), 0)
            qt_passe = to_non_negative_int(inst.get("quantidade_passe_livre", 0), 0)

            totais["ciptea"] += qt_ciptea
            totais["cipf"] += qt_cipf
            totais["passe_livre"] += qt_passe

            regiao = (inst.get("regiao") or "").strip()
            if not regiao or regiao.lower() in {"não informada", "nao informada", "não informado", "nao informado"}:
                continue

            regioes[regiao] = regioes.get(regiao, 0) + qt_ciptea + qt_cipf + qt_passe

    return {"totais": totais, "regioes": regioes}


def save_demografia(linhas: List[dict]):
    with open(DEMO_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["tipo_deficiencia", "faixa_etaria", "quantidade"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for linha in linhas:
            writer.writerow({
                "tipo_deficiencia": linha.get("tipo_deficiencia", ""),
                "faixa_etaria": linha.get("faixa_etaria", ""),
                "quantidade": normalize_numeric_field(linha.get("quantidade", 0)),
            })


def save_instituicoes(instituicoes: Dict[str, List[dict]]):
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "municipio",
            "regiao",
            "nome",
            "tipo",
            "endereco",
            "telefone",
            "email",
            "quantidade_ciptea",
            "quantidade_cipf",
            "quantidade_passe_livre",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for municipio, insts in instituicoes.items():
            for inst in insts:
                row = {"municipio": municipio}
                row.update(inst)
                writer.writerow(row)
