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


def load_dados():
    instituicoes = {}
    todos_municipios = set()

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
                    inst = {
                        "nome": inst_nome,
                        "tipo": safe_str(row, "tipo"),
                        "endereco": safe_str(row, "endereco"),
                        "telefone": safe_str(row, "telefone"),
                        "email": safe_str(row, "email"),
                        "quantidade_ciptea": normalize_numeric_field(row.get("quantidade_ciptea", "")),
                        "quantidade_cipf": normalize_numeric_field(row.get("quantidade_cipf", "")),
                        "quantidade_passe_livre": normalize_numeric_field(row.get("quantidade_passe_livre", ""))
                    }
                    if municipio not in instituicoes:
                        instituicoes[municipio] = []
                    instituicoes[municipio].append(inst)

    municipiosStatus = {}
    for municipio in todos_municipios:
        insts = instituicoes.get(municipio, [])
        tipos = set(inst["tipo"] for inst in insts)
        if not tipos:
            status = "Nenhum"
        else:
            status = " e ".join(sorted(tipos))
        municipiosStatus[municipio] = status

    return municipiosStatus, instituicoes


def load_demografia_rows():
    linhas = []

    if os.path.exists(DEMO_FILE):
        with open(DEMO_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                municipio = (row.get("municipio") or "").strip()
                if not municipio:
                    continue

                linhas.append({
                    "municipio": municipio,
                    "regiao": (row.get("regiao") or "").strip(),
                    "tipo_deficiencia": (row.get("tipo_deficiencia") or "").strip(),
                    "faixa_etaria": (row.get("faixa_etaria") or "").strip(),
                    "mes": (row.get("mes") or "").strip(),
                    "quantidade": normalize_numeric_field(row.get("quantidade", "0")),
                })

    return linhas


def resumir_demografia(linhas):
    por_deficiencia = {}
    por_faixa = {}
    por_regiao = {}
    por_mes = {}

    for row in linhas:
        qtd = to_non_negative_int(row.get("quantidade", 0), 0)
        tipo = row.get("tipo_deficiencia") or "Não informado"
        faixa = row.get("faixa_etaria") or "Não informado"
        regiao = row.get("regiao") or "Não informada"
        mes = row.get("mes") or "Não informado"

        por_deficiencia[tipo] = por_deficiencia.get(tipo, 0) + qtd
        por_faixa[faixa] = por_faixa.get(faixa, 0) + qtd
        por_regiao[regiao] = por_regiao.get(regiao, 0) + qtd
        por_mes[mes] = por_mes.get(mes, 0) + qtd

    return {
        "por_deficiencia": por_deficiencia,
        "por_faixa": por_faixa,
        "por_regiao": por_regiao,
        "por_mes": por_mes,
    }


def save_demografia(linhas):
    with open(DEMO_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["municipio", "regiao", "tipo_deficiencia", "faixa_etaria", "mes", "quantidade"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in linhas:
            writer.writerow(row)


def save_instituicoes(instituicoes):
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "municipio","nome","tipo","endereco","telefone","email",
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
    municipiosStatus, municipiosInstituicoes = load_dados()
    demografia_linhas = load_demografia_rows()
    demografia = resumir_demografia(demografia_linhas)
    return render_template('index.html',
                           municipiosStatus=municipiosStatus,
                           municipiosInstituicoes=municipiosInstituicoes,
                           demografia=demografia)


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

    municipiosStatus, instituicoes = load_dados()
    demografia_linhas = load_demografia_rows()

    regiao_opcoes = [
        "Grande Florianópolis", "Sul", "Norte", "Vale do Itajaí", "Serra", "Oeste"
    ]
    tipo_deficiencia_opcoes = ["TEA", "Fibromialgia", "Demais Def."]
    faixas_opcoes = ["0-17", "18-29", "30-44", "45-59", "60+"]

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
                        instituicoes[municipio][idx]["tipo"] = request.form.get(f"tipo_{municipio}_{idx}", "").strip()
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
                        "tipo": request.form.get("tipo", "").strip(),
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
            deletes = set(request.form.getlist("delete_demografia"))
            atualizadas = []
            for idx, linha in enumerate(demografia_linhas):
                if str(idx) in deletes:
                    continue
                atualizadas.append({
                    "municipio": request.form.get(f"dem_municipio_{idx}", "").strip(),
                    "regiao": request.form.get(f"dem_regiao_{idx}", "").strip(),
                    "tipo_deficiencia": request.form.get(f"dem_tipo_{idx}", "").strip(),
                    "faixa_etaria": request.form.get(f"dem_faixa_{idx}", "").strip(),
                    "mes": request.form.get(f"dem_mes_{idx}", "").strip(),
                    "quantidade": normalize_numeric_field(request.form.get(f"dem_quantidade_{idx}", "0")),
                })

            if request.form.get("add_demografia"):
                atualizadas.append({
                    "municipio": request.form.get("novo_municipio", "").strip(),
                    "regiao": request.form.get("novo_regiao", "").strip(),
                    "tipo_deficiencia": request.form.get("novo_tipo_deficiencia", "").strip(),
                    "faixa_etaria": request.form.get("novo_faixa_etaria", "").strip(),
                    "mes": request.form.get("novo_mes", "").strip(),
                    "quantidade": normalize_numeric_field(request.form.get("novo_quantidade", "0")),
                })

            save_demografia(atualizadas)

        return redirect(url_for('admin'))

    return render_template("admin.html", instituicoes=instituicoes,
                           demografia=demografia_linhas,
                           regiao_opcoes=regiao_opcoes,
                           tipo_deficiencia_opcoes=tipo_deficiencia_opcoes,
                           faixas_opcoes=faixas_opcoes)


@app.route('/sc_municipios.geojson')
def geojson():
    return send_from_directory(os.getcwd(), 'sc_municipios.geojson')


# --- Executa no Render ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
