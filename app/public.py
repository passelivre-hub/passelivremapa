from pathlib import Path
from flask import Blueprint, current_app, render_template, send_from_directory

from .storage import (
    load_dados,
    load_demografia_rows,
    preparar_demografia_por_deficiencia,
    resumir_instituicoes,
)

bp = Blueprint('public', __name__)


@bp.route('/')
def index():
    municipios_status, municipios_instituicoes, municipios_totais = load_dados()
    demografia_registros = load_demografia_rows()
    instituicoes_resumo = resumir_instituicoes(municipios_instituicoes)
    return render_template(
        'index.html',
        municipiosStatus=municipios_status,
        municipiosInstituicoes=municipios_instituicoes,
        municipiosTotais=municipios_totais,
        demografia_distribuicao=preparar_demografia_por_deficiencia(demografia_registros),
        instituicoes_resumo=instituicoes_resumo,
    )


@bp.route('/sc_municipios.geojson')
def geojson():
    root_dir = Path(current_app.root_path).parent
    return send_from_directory(root_dir, 'sc_municipios.geojson')
