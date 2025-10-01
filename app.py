import csv
from flask import Flask, render_template, request, redirect, send_from_directory
import os

app = Flask(__name__)

CSV_FILE = "dados.csv"  # atualizado para procurar por dados.csv

# Função para carregar dados e calcular status
def load_dados():
    instituicoes = {}
    todos_municipios = set()

    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                municipio = row["municipio"].strip()
                todos_municipios.add(municipio)

                if row["nome"].strip():  # se tiver instituição
                    inst = {
                        "nome": row["nome"].strip(),
                        "tipo": row["tipo"].strip(),
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

    # Calcula status final por município
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

# Função para salvar instituições
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

# Rota principal
@app.route('/')
def index():
    municipiosStatus, municipiosInstituicoes = load_dados()
    return render_template('index.html',
                           municipiosStatus=municipiosStatus,
                           municipiosInstituicoes=municipiosInstituicoes)

# Painel de administração
@app.route('/admin', methods=['GET','POST'])
def admin():
    municipiosStatus, instituicoes = load_dados()

    if request.method == 'POST':
        # Excluir instituições
        deletes = request.form.getlist("delete")
        if deletes:
            new_instituicoes = {}
            for municipio, insts in instituicoes.items():
                new_instituicoes[municipio] = []
                for i, inst in enumerate(insts):
                    if f"{municipio}_{i}" not in deletes:
                        new_instituicoes[municipio].append(inst)
            instituicoes = new_instituicoes

        # Atualizar existentes
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
                    instituicoes[municipio][idx]["quantidade_ciptea"] = request.form.get(f"quantidade_ciptea_{municipio}_{idx}", "").strip()
                    instituicoes[municipio][idx]["quantidade_cipf"] = request.form.get(f"quantidade_cipf_{municipio}_{idx}", "").strip()
                    instituicoes[municipio][idx]["quantidade_passe_livre"] = request.form.get(f"quantidade_passe_livre_{municipio}_{idx}", "").strip()

        # Adicionar nova instituição
        if request.form.get("add"):
            municipio = request.form.get("municipio", "").strip()
            if municipio:
                inst = {
                    "nome": request.form.get("nome", "").strip(),
                    "tipo": request.form.get("tipo", "").strip(),
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
        return redirect("/admin")

    return render_template("admin.html", instituicoes=instituicoes)

# Serve GeoJSON
@app.route('/sc_municipios.geojson')
def geojson():
    return send_from_directory(os.getcwd(), 'sc_municipios.geojson')

if __name__ == '__main__':
    # Configuração para rodar no Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
