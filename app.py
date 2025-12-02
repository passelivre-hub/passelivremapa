import csv
import os
from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-secreta-trocar")

# 🔐 Usuário e senha definidos via variáveis de ambiente
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "fcee2025")

CSV_FILE = "dados.csv"
DEMO_FILE = "demografia.csv"


# -------- Funções utilitárias -------- #
def to_non_negative_int(value, default=0):
    try:
        return max(int(str(value).strip() or default), 0)
    except (TypeError, ValueError):
        return default


def normalize_numeric_field(value):
    return str(to_non_negative_int(value, 0))


def normalize_tipo(valor):
    tipo = (valor or "").strip()
    if tipo.lower() == "ambos":
        return "Todos"
    return tipo


def load_dados():
    instituicoes = {}
    todos_municipios = set()
    municipios_totais = {}
    municipio_regiao = {}

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

                    regiao = safe_str(row, "regiao")
                    if regiao:
                        municipio_regiao[municipio] = regiao

                    inst = {
                        "nome": inst_nome,
                        "regiao": regiao,
                        "tipo": normalize_tipo(safe_str(row, "tipo")),
                        "endereco": safe_str(row, "endereco"),
                        "telefone": safe_str(row, "telefone"),
                        "email": safe_str(row, "email"),
                        "quantidade_ciptea": normalize_numeric_field(qt_ciptea),
                        "quantidade_cipf": normalize_numeric_field(qt_cipf),
                        "quantidade_passe_livre": normalize_numeric_field(qt_passe)
                    }
                    if municipio not in instituicoes:
                        instituicoes[municipio] = []
                    instituicoes[municipio].append(inst)

                    municipios_totais[municipio] = municipios_totais.get(municipio, 0) + qt_ciptea + qt_cipf + qt_passe

    municipiosStatus = {}
    for municipio in todos_municipios:
        insts = instituicoes.get(municipio, [])
        tipos = set(inst["tipo"] for inst in insts)
        if not tipos:
            status = "Nenhum"
        elif "Todos" in tipos:
            status = "Todos"
        else:
            status = " e ".join(sorted(tipos))
        municipiosStatus[municipio] = status

    return municipiosStatus, instituicoes, municipios_totais, municipio_regiao


def load_demografia_rows():
    registros = []
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
                    "quantidade": quantidade
                })

    return registros


def preparar_demografia_por_deficiencia(registros):
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
        "total": total
    }


def resumir_instituicoes(instituicoes):
    totais = {"ciptea": 0, "cipf": 0, "passe_livre": 0}
    regioes = {}

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


def resumir_por_municipio(instituicoes):
    resumo = {}
    for municipio, insts in instituicoes.items():
        dados = {
            "regiao": "",
            "instituicoes": len(insts),
            "ciptea": 0,
            "cipf": 0,
            "passe_livre": 0,
        }

        for inst in insts:
            dados["regiao"] = inst.get("regiao") or dados["regiao"]
            dados["ciptea"] += to_non_negative_int(inst.get("quantidade_ciptea", 0), 0)
            dados["cipf"] += to_non_negative_int(inst.get("quantidade_cipf", 0), 0)
            dados["passe_livre"] += to_non_negative_int(inst.get("quantidade_passe_livre", 0), 0)

        resumo[municipio] = dados

    return resumo


def save_demografia(linhas):
    with open(DEMO_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["tipo_deficiencia", "faixa_etaria", "quantidade"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for linha in linhas:
            writer.writerow({
                "tipo_deficiencia": linha.get("tipo_deficiencia", ""),
                "faixa_etaria": linha.get("faixa_etaria", ""),
                "quantidade": normalize_numeric_field(linha.get("quantidade", 0))
            })


def save_instituicoes(instituicoes):
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "municipio","regiao","nome","tipo","endereco","telefone","email",
            "quantidade_ciptea","quantidade_cipf","quantidade_passe_livre"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for municipio, insts in instituicoes.items():
            for inst in insts:
                row = {"municipio": municipio}
                row.update(inst)
                writer.writerow(row)


# -------- Rotas -------- #

@app.route('/')
def index():
    municipiosStatus, municipiosInstituicoes, municipios_totais, municipio_regiao = load_dados()
    demografia_registros = load_demografia_rows()
    instituicoes_resumo = resumir_instituicoes(municipiosInstituicoes)
    municipios_resumo = resumir_por_municipio(municipiosInstituicoes)
    return render_template(
        'index.html',
        municipiosStatus=municipiosStatus,
        municipiosInstituicoes=municipiosInstituicoes,
        municipiosTotais=municipios_totais,
        demografia_distribuicao=preparar_demografia_por_deficiencia(demografia_registros),
        instituicoes_resumo=instituicoes_resumo,
        municipios_resumo=municipios_resumo,
        municipio_regiao=municipio_regiao,
    )


# --- Tela de Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        password = request.form['password']

        if user == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error="Usuário ou senha incorretos.")

    return render_template('login.html')


# --- Logout ---
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# --- Painel Administrativo ---
@app.route('/admin', methods=['GET','POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    municipiosStatus, instituicoes, _, municipio_regiao = load_dados()
    demografia_registros = load_demografia_rows()

    regiao_opcoes = [
        "Grande Florianópolis", "Sul", "Norte", "Vale do Itajaí", "Serra", "Oeste"
    ]
    faixas_opcoes = ["0-12", "13-17", "18-59", "60+"]

    if request.method == 'POST':
        form_type = request.form.get("form_type")

        if form_type == "instituicoes":
            deletes = request.form.getlist("delete")
            if deletes:
                new_instituicoes = {}
                for municipio, insts in instituicoes.items():
                    new_instituicoes[municipio] = []
                    for i, inst in enumerate(insts):
                        if f"{municipio}_{i}" not in deletes:
                            new_instituicoes[municipio].append(inst)
                instituicoes = new_instituicoes

            for key in request.form:
                if key.startswith("nome_"):
                    parts = key.split("_")
                    municipio = parts[1]
                    idx = int(parts[2])
                    if municipio in instituicoes and idx < len(instituicoes[municipio]):
                        instituicoes[municipio][idx]["nome"] = request.form[key].strip()
                        instituicoes[municipio][idx]["regiao"] = request.form.get(f"regiao_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["tipo"] = normalize_tipo(request.form.get(f"tipo_{municipio}_{idx}", ""))
                        instituicoes[municipio][idx]["endereco"] = request.form.get(f"endereco_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["telefone"] = request.form.get(f"telefone_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["email"] = request.form.get(f"email_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["quantidade_ciptea"] = normalize_numeric_field(request.form.get(f"quantidade_ciptea_{municipio}_{idx}", ""))
                        instituicoes[municipio][idx]["quantidade_cipf"] = normalize_numeric_field(request.form.get(f"quantidade_cipf_{municipio}_{idx}", ""))
                        instituicoes[municipio][idx]["quantidade_passe_livre"] = normalize_numeric_field(request.form.get(f"quantidade_passe_livre_{municipio}_{idx}", ""))

            if request.form.get("add"):
                municipio = request.form.get("municipio", "").strip()
                if municipio:
                    inst = {
                        "nome": request.form.get("nome", "").strip(),
                        "regiao": request.form.get("regiao", "").strip(),
                        "tipo": normalize_tipo(request.form.get("tipo", "")),
                        "endereco": request.form.get("endereco", "").strip(),
                        "telefone": request.form.get("telefone", "").strip(),
                        "email": request.form.get("email", "").strip(),
                        "quantidade_ciptea": normalize_numeric_field(request.form.get("quantidade_ciptea", "")),
                        "quantidade_cipf": normalize_numeric_field(request.form.get("quantidade_cipf", "")),
                        "quantidade_passe_livre": normalize_numeric_field(request.form.get("quantidade_passe_livre", ""))
                    }
                    if municipio not in instituicoes:
                        instituicoes[municipio] = []
                    instituicoes[municipio].append(inst)

            save_instituicoes(instituicoes)

        if form_type == "demografia":
            tipos = request.form.getlist("tipo_deficiencia[]")
            faixas = request.form.getlist("faixa_etaria[]")
            quantidades = request.form.getlist("quantidade[]")
            deletions = set(request.form.getlist("delete_demografia"))

            linhas = []
            for idx, (tipo, faixa, quantidade) in enumerate(zip(tipos, faixas, quantidades)):
                if str(idx) in deletions:
                    continue
                tipo = (tipo or "").strip()
                faixa = (faixa or "").strip()
                if not tipo or not faixa:
                    continue
                linhas.append({
                    "tipo_deficiencia": tipo,
                    "faixa_etaria": faixa,
                    "quantidade": quantidade
                })

            save_demografia(linhas)

        return redirect(url_for('admin'))

    return render_template(
        "admin.html",
        instituicoes=instituicoes,
        demografia_registros=demografia_registros,
        regiao_opcoes=regiao_opcoes,
        faixas_opcoes=faixas_opcoes,
        instituicoes_resumo=resumir_instituicoes(instituicoes),
        municipio_regiao=municipio_regiao,
        municipios_lista=sorted(municipio_regiao.keys()),
    )


@app.route('/sc_municipios.geojson')
def geojson():
    return send_from_directory(os.getcwd(), 'sc_municipios.geojson')


# --- Executa no Render ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
