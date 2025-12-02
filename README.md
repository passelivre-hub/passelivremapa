# passelivremapa

Painel público e área administrativa para acompanhar carteiras CIPTEA, CIPF e Passe Livre em Santa Catarina.

## Estrutura
- **app/**: aplicação Flask modularizada com blueprints (`public` para o mapa e `admin` para o painel de gestão).
- **templates/**: páginas separadas para o mapa (`index.html`), login (`login.html`) e painel admin (`admin.html`).
- **dados.csv / demografia.csv**: armazenam as informações inseridas via painel admin. São iniciados apenas com cabeçalhos, sem dados de exemplo.

## Como executar
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Exporte variáveis de ambiente (opcional) para credenciais do admin e chave de sessão:
   ```bash
   export SECRET_KEY="sua-chave"
   export ADMIN_USER="admin"
   export ADMIN_PASS="senha"
   ```
3. Rode localmente:
   ```bash
   python app.py
   ```
4. Acesse:
   - Mapa público: `http://localhost:5000/`
   - Login/Admin: `http://localhost:5000/login` e `http://localhost:5000/admin`

## Deploy
O `Procfile` está preparado para o modelo de aplicação fábrica do Flask:
```bash
web: gunicorn 'app:create_app()'
```

Os dados permanecerão salvos em `dados.csv` e `demografia.csv` no diretório raiz, sem sementes automáticas, permitindo iniciar o painel do zero.
