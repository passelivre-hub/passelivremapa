from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from .storage import (
    load_dados,
    load_demografia_rows,
    normalize_numeric_field,
    resumir_instituicoes,
    save_demografia,
    save_instituicoes,
    to_non_negative_int,
)

bp = Blueprint('admin', __name__)


def _is_logged_in():
    return session.get('logged_in') is True


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        password = request.form['password']

        admin_user = current_app.config.get('ADMIN_USER')
        admin_pass = current_app.config.get('ADMIN_PASS')

        if user == admin_user and password == admin_pass:
            session['logged_in'] = True
            return redirect(url_for('admin.admin_home'))
        else:
            return render_template('login.html', error="Usuário ou senha incorretos.")

    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin.login'))


@bp.route('/admin', methods=['GET', 'POST'])
def admin_home():
    if not _is_logged_in():
        return redirect(url_for('admin.login'))

    _, instituicoes, _ = load_dados()
    demografia_registros = load_demografia_rows()

    regiao_opcoes = [
        "Grande Florianópolis", "Sul", "Norte", "Vale do Itajaí", "Serra", "Oeste"
    ]
    faixas_opcoes = ["0-12", "13-17", "18-59", "60+"]

    if request.method == 'POST':
        form_type = request.form.get("form_type")

        if form_type == "instituicoes":
            deletes = set(request.form.getlist("delete"))
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
                        "regiao": request.form.get("regiao", "").strip(),
                        "tipo": request.form.get("tipo", "").strip(),
                        "endereco": request.form.get("endereco", "").strip(),
                        "telefone": request.form.get("telefone", "").strip(),
                        "email": request.form.get("email", "").strip(),
                        "quantidade_ciptea": normalize_numeric_field(request.form.get("quantidade_ciptea", "")),
                        "quantidade_cipf": normalize_numeric_field(request.form.get("quantidade_cipf", "")),
                        "quantidade_passe_livre": normalize_numeric_field(request.form.get("quantidade_passe_livre", "")),
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
                    "quantidade": to_non_negative_int(quantidade, 0),
                })

            save_demografia(linhas)

        return redirect(url_for('admin.admin_home'))

    return render_template(
        "admin.html",
        instituicoes=instituicoes,
        demografia_registros=demografia_registros,
        regiao_opcoes=regiao_opcoes,
        faixas_opcoes=faixas_opcoes,
        instituicoes_resumo=resumir_instituicoes(instituicoes),
    )
