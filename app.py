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
def load_dados():
    instituicoes = {}
    todos_municipios = set()

    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                municipio = row["municipio"].strip()
                todos_municipios.add(municipio)

                if row["nome"].strip():
                    inst = {
                        "nome": row["nome"].strip(),
                        "tipo": row["tipo"].strip(),
                        "regiao": row.get("regiao", "").strip(),
                        "endereco": row["endereco"].strip(),
                        "telefone": row["telefone"].strip(),
                        "email": row["email"].strip(),
                        "quantidade_ciptea": row.get("quantidade_ciptea", "").strip(),
                        "quantidade_cipf": row.get("quantidade_cipf", "").strip(),
                        "quantidade_passe_livre": row.get("quantidade_passe_livre", "").strip()
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
                linhas.append({
                    "faixa_etaria": row.get("faixa_etaria", "").strip(),
                    "quantidade": row.get("quantidade", "0").strip(),
                })

    return linhas


def resumir_demografia(faixas_linhas, deficiencia_totais, regiao_totais):
    por_faixa = {}

    for row in faixas_linhas:
        qtd = int(row.get("quantidade", 0) or 0)
        por_faixa[row["faixa_etaria"]] = por_faixa.get(row["faixa_etaria"], 0) + qtd

    return {
        "por_deficiencia": deficiencia_totais,
        "por_faixa": por_faixa,
        "por_regiao": regiao_totais,
    }


def resumir_instituicoes(instituicoes):
    por_deficiencia = {"TEA": 0, "Fibromialgia": 0, "Demais Def.": 0}
    por_regiao = {}

    for insts in instituicoes.values():
        for inst in insts:
            ciptea = int(inst.get("quantidade_ciptea") or 0)
            cipf = int(inst.get("quantidade_cipf") or 0)
            passe = int(inst.get("quantidade_passe_livre") or 0)
            regiao = inst.get("regiao", "") or "Não informado"

            por_deficiencia["TEA"] += ciptea
            por_deficiencia["Fibromialgia"] += cipf
            por_deficiencia["Demais Def."] += passe

            por_regiao[regiao] = por_regiao.get(regiao, 0) + ciptea + cipf + passe

    return por_deficiencia, por_regiao


def save_demografia(linhas):
    with open(DEMO_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["faixa_etaria", "quantidade"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in linhas:
            writer.writerow(row)


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
    municipiosStatus, municipiosInstituicoes = load_dados()
    demografia_linhas = load_demografia_rows()
    deficiencia_totais, regiao_totais = resumir_instituicoes(municipiosInstituicoes)
    demografia = resumir_demografia(demografia_linhas, deficiencia_totais, regiao_totais)
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
                        instituicoes[municipio][idx]["tipo"] = request.form.get(f"tipo_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["regiao"] = request.form.get(f"regiao_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["endereco"] = request.form.get(f"endereco_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["telefone"] = request.form.get(f"telefone_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["email"] = request.form.get(f"email_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["quantidade_ciptea"] = request.form.get(f"quantidade_ciptea_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["quantidade_cipf"] = request.form.get(f"quantidade_cipf_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["quantidade_passe_livre"] = request.form.get(f"quantidade_passe_livre_{municipio}_{idx}", "").strip()

            if request.form.get("add"):
                municipio = request.form.get("municipio", "").strip()
                if municipio:
                    inst = {
                        "nome": request.form.get("nome", "").strip(),
                        "tipo": request.form.get("tipo", "").strip(),
                        "regiao": request.form.get("regiao", "").strip(),
                        "endereco": request.form.get("endereco", "").strip(),
                        "telefone": request.form.get("telefone", "").strip(),
                        "email": request.form.get("email", "").strip(),
                        "quantidade_ciptea": request.form.get("quantidade_ciptea", "").strip(),
                        "quantidade_cipf": request.form.get("quantidade_cipf", "").strip(),
                        "quantidade_passe_livre": request.form.get("quantidade_passe_livre", "").strip()
                    }
                    if municipio not in instituicoes:
                        instituicoes[municipio] = []
                    instituicoes[municipio].append(inst)

            save_instituicoes(instituicoes)

        if form_type == "demografia":
            faixas_labels = ["0-12", "13-17", "18-59", "60+"]
            atualizadas = []

            for faixa in faixas_labels:
                field_name = faixa.replace("+", "mais").replace("-", "_")
                quantidade = request.form.get(f"faixa_{field_name}", "0").strip()
                atualizadas.append({
                    "faixa_etaria": faixa,
                    "quantidade": quantidade or "0",
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
