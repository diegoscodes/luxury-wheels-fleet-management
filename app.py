from flask import Flask, render_template, request, redirect, send_file, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import criar_tabelas, conectar_bd
from datetime import datetime, timedelta, date
import matplotlib.ticker as mticker
import os
import pandas as pd
import sqlite3
from flask import session
import matplotlib
matplotlib.use("Agg")  # ⬅️ Linha que evita uso de GUI
import matplotlib.pyplot as plt
import json

import io
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message



# Define explicitamente a pasta de templates
app = Flask(__name__, template_folder="templates")
app.secret_key = "luxury123"

# Configurações do servidor SMTP do Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'diegopuke37@gmail.com'
app.config['MAIL_PASSWORD'] = 'sxzomysxbnqghhpm'
app.config['MAIL_DEFAULT_SENDER'] = 'diegopuke37@gmail.com'
mail = Mail(app)




# Garante que as tabelas sejam criadas ao iniciar o app
criar_tabelas()

def verificar_envio_diario():
    caminho = "alerta_status.json"
    hoje = str(date.today())

    # Se o arquivo não existe, cria e envia o e-mail
    if not os.path.exists(caminho):
        with open(caminho, "w") as f:
            json.dump({"data": hoje}, f)
        return True  # deve enviar

    # Se existe, verifica a data
    with open(caminho, "r") as f:
        dados = json.load(f)

    if dados.get("data") != hoje:
        with open(caminho, "w") as f:
            json.dump({"data": hoje}, f)
        return True  # deve enviar

    return False  # já foi enviado hoje




@app.route("/")
def home():
    if "usuario" not in session:
        return redirect(url_for("login"))

    vencidas, proximas, _ = buscar_revisoes_pendentes()

    if verificar_envio_diario():
        enviar_email_alerta(proximas)

    return render_template("index.html", vencidas=vencidas, proximas=proximas)







#--------------------- ENVIAR EMAIL ----------------
def enviar_email_alerta(revisoes):
    if not revisoes:
        print("Nenhuma revisão para enviar por e-mail.")
        return

    remetente = "diegopuke37@gmail.com"
    senha = "sxzomysxbnqghhpm"  # sua senha de app aqui
    destinatario = "diegopuke37@gmail.com"

    # Garante que tudo será convertido corretamente
    try:
        corpo = "<h3>Revisoes pendentes nos proximos 5 dias:</h3><ul>"
        for r in revisoes:
            if len(r) < 4:
                print("⚠️ Tupla incompleta:", r)
                continue
            modelo = str(r[1])
            placa = str(r[2])
            data = str(r[3])
            corpo += f"<li>Veiculo: {modelo} (Placa: {placa}) - Revisao em {data}</li>"
        corpo += "</ul>"
    except Exception as e:
        print("Erro ao montar corpo do e-mail:", e)
        return

    try:
        mensagem = MIMEMultipart()
        mensagem["From"] = remetente
        mensagem["To"] = destinatario
        mensagem["Subject"] = str("Alerta de Revisao de Veiculos")

        parte_html = MIMEText(corpo.encode('utf-8'), "html", "utf-8")
        mensagem.attach(parte_html)

        with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(remetente, senha)
            servidor.sendmail(remetente, destinatario, mensagem.as_string())
            print("✅ E-mail enviado com sucesso.")
    except Exception as e:
        print("❌ Falha ao enviar e-mail:", e)


#-------------------LOGIN----------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conexao = conectar_bd()
        cursor = conexao.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,))
        user = cursor.fetchone()
        conexao.close()

        if user and check_password_hash(user[3], senha):
            session["usuario"] = user[1]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("home"))
        else:
            flash("Usuário ou senha inválidos!", "danger")

    return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
    nome = request.form["nome"]
    usuario = request.form["usuario"]
    senha = request.form["senha"]
    confirmar = request.form["confirmar"]

    if senha != confirmar:
        flash("As senhas não conferem!", "danger")
        return redirect(url_for("login"))

    senha_hash = generate_password_hash(senha)

    try:
        conexao = conectar_bd()
        cursor = conexao.cursor()
        cursor.execute("INSERT INTO usuarios (nome, usuario, senha) VALUES (?, ?, ?)",
                       (nome, usuario, senha_hash))
        conexao.commit()
        conexao.close()
        flash("Usuário registrado com sucesso! Faça o login.", "success")
    except sqlite3.IntegrityError:
        flash("Usuário já existe!", "danger")

    return redirect(url_for("login"))




@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))


#-----------------busca revisoes pendente --------------------
from datetime import datetime, timedelta

def buscar_revisoes_pendentes():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    hoje = datetime.today().date()
    proximos_15 = hoje + timedelta(days=15)

    # Converter as datas para strings no formato ISO (YYYY-MM-DD)
    hoje_str = hoje.isoformat()
    proximos_15_str = proximos_15.isoformat()

    # Revisões vencidas
    cursor.execute("SELECT * FROM veiculos WHERE proxima_revisao < ?", (hoje_str,))
    revisoes_vencidas = cursor.fetchall()

    # Revisões nos próximos 15 dias
    cursor.execute("SELECT * FROM veiculos WHERE proxima_revisao BETWEEN ? AND ?", (hoje_str, proximos_15_str))
    revisoes_proximas = cursor.fetchall()

    # Inspeções nos próximos 15 dias
    cursor.execute("SELECT * FROM veiculos WHERE inspecao BETWEEN ? AND ?", (hoje_str, proximos_15_str))
    inspecoes_proximas = cursor.fetchall()

    conexao.close()

    return revisoes_vencidas, revisoes_proximas, inspecoes_proximas








# ------------------ Funções auxiliares para o Dashboard ------------------

def obter_dados_dashboard():
    """ Obtém dados do banco de dados para exibição no Dashboard """
    conexao = conectar_bd()

    # Verifica se as tabelas existem antes de consultar
    try:
        df_veiculos = pd.read_sql_query("SELECT * FROM veiculos", conexao)
    except:
        df_veiculos = pd.DataFrame()

    try:
        df_reservas = pd.read_sql_query("SELECT * FROM reservas", conexao)
    except:
        df_reservas = pd.DataFrame()

    try:
        df_manutencoes = pd.read_sql_query("SELECT * FROM manutencoes", conexao)
    except:
        df_manutencoes = pd.DataFrame()

    conexao.close()

    # DEBUG 👇
    #print("🔍 Total de veículos carregados:", df_veiculos.shape[0])
    #if not df_veiculos.empty:
        #print(df_veiculos[["id", "modelo", "tipo", "categoria", "status"]])

    return df_veiculos, df_reservas, df_manutencoes


def obter_veiculos_alugados():
    conexao = conectar_bd()
    cursor = conexao.cursor()
    query = """
        SELECT v.modelo, c.nome, r.data_fim
        FROM reservas r
        JOIN veiculos v ON r.veiculo_id = v.id
        JOIN clientes c ON r.cliente_id = c.id
        WHERE r.status = 'Confirmada'
    """
    cursor.execute(query)
    alugados = cursor.fetchall()
    conexao.close()

    # Calcula dias restantes
    resultado = []
    hoje = datetime.today().date()
    for modelo, cliente, data_fim in alugados:
        if isinstance(data_fim, str):
            data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        dias_restantes = (data_fim - hoje).days
        resultado.append((modelo, cliente, data_fim, dias_restantes))

    return resultado



def gerar_grafico(df, x_col, titulo):
    """ Gera um gráfico de barras e o converte em base64 """
    if df.empty or x_col not in df.columns:
        return None

    plt.figure(figsize=(6, 4))
    df[x_col].value_counts().plot(kind="bar", color="royalblue")

    # Configurações
    plt.title(titulo)
    plt.xlabel(x_col)
    plt.ylabel("Quantidade")
    plt.gca().yaxis.set_major_locator(mticker.MaxNLocator(integer=True))  # 👈 Força valores inteiros no eixo Y

    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{graph_url}"



@app.route("/enviar-email-teste")
def enviar_teste_manual():
    _, proximas = buscar_revisoes_pendentes()
    try:
        enviar_email_alerta(proximas)
        flash("✅ E-mail de alerta enviado com sucesso!", "success")
    except Exception as e:
        flash("❌ Falha ao enviar e-mail de alerta.", "danger")
        print("Erro ao enviar e-mail:", e)
    return redirect(url_for("home"))


#------------------- Rota exibir imagem veiculos-----------------

@app.route("/veiculos/imagem/<int:veiculo_id>")
def exibir_imagem_veiculo(veiculo_id):
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT modelo, imagem, marca, categoria, transmissao, capacidade, status, placa
        FROM veiculos WHERE id=?
    """, (veiculo_id,))
    veiculo = cursor.fetchone()
    conexao.close()

    if veiculo:
        return render_template("exibir_imagem.html",
                               modelo=veiculo[0],
                               imagem=veiculo[1],
                               marca=veiculo[2],
                               categoria=veiculo[3],
                               transmissao=veiculo[4],
                               capacidade=veiculo[5],
                               status=veiculo[6],
                               placa=veiculo[7])
    else:
        flash("Veículo não encontrado.", "warning")
        return redirect(url_for("listar_veiculos"))



# ------------------ Rota do Dashboard ------------------

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    df_veiculos, df_reservas, df_manutencoes = obter_dados_dashboard()

    filtro_status = request.form.get("status") if request.method == "POST" else None
    filtro_tipo = request.form.get("tipo") if request.method == "POST" else None
    filtro_categoria = request.form.get("categoria") if request.method == "POST" else None
    filtro_secao = request.form.get("secao") if request.method == "POST" else None

    # Aplicar filtros nos veículos
    if filtro_status:
        df_veiculos = df_veiculos[df_veiculos["status"] == filtro_status]
    if filtro_tipo:
        df_veiculos = df_veiculos[df_veiculos["tipo"] == filtro_tipo]
    if filtro_categoria:
        df_veiculos = df_veiculos[df_veiculos["categoria"] == filtro_categoria]

    grafico_reservas = gerar_grafico(df_reservas, "veiculo_id", "Reservas por Veículo")
    grafico_manutencao = gerar_grafico(df_manutencoes, "veiculo_id", "Manutenções por Veículo")

    total_veiculos = len(df_veiculos)
    total_reservas = len(df_reservas)
    total_manutencoes = len(df_manutencoes)

    vencidas, proximas, inspecoes = buscar_revisoes_pendentes()
    veiculos_alerta = {}

    for v in proximas:
        veiculos_alerta[v[0]] = {
            "modelo": v[2],
            "placa": v[13],
            "proxima_revisao": v[10],
            "inspecao": None
        }

    for v in inspecoes:
        if v[0] in veiculos_alerta:
            veiculos_alerta[v[0]]["inspecao"] = v[11]
        else:
            veiculos_alerta[v[0]] = {
                "modelo": v[2],
                "placa": v[13],
                "proxima_revisao": None,
                "inspecao": v[11]
            }

    veiculos_alugados = obter_veiculos_alugados()
    ultimos_clientes = obter_ultimos_clientes()
    veiculos_por_tipo = contar_veiculos_disponiveis_por_tipo()
    veiculos_por_categoria = contar_veiculos_disponiveis_por_categoria()
    total_reservas_mes, total_financeiro_mes = obter_reservas_e_financas_mes()

    return render_template(
        "dashboard.html",
        total_veiculos=total_veiculos,
        total_reservas=total_reservas,
        total_manutencoes=total_manutencoes,
        grafico_reservas=grafico_reservas,
        grafico_manutencao=grafico_manutencao,
        vencidas=vencidas,
        proximas=proximas,
        inspecoes=inspecoes,
        veiculos_alugados=veiculos_alugados,
        ultimos_clientes=ultimos_clientes,
        veiculos_por_tipo=veiculos_por_tipo,
        veiculos_por_categoria=veiculos_por_categoria,
        total_reservas_mes=total_reservas_mes,
        total_financeiro_mes=total_financeiro_mes,
        veiculos_alerta=veiculos_alerta.values(),
        filtro_status=filtro_status,
        filtro_tipo=filtro_tipo,
        filtro_categoria=filtro_categoria,
        filtro_secao=filtro_secao
    )


#------------------- contar veiculos disponiveis ------------

def contar_veiculos_disponiveis_por_tipo():
    conexao = conectar_bd()
    query = "SELECT tipo, COUNT(*) as total FROM veiculos GROUP BY tipo"
    df = pd.read_sql_query(query, conexao)
    conexao.close()
    return df



def contar_veiculos_disponiveis_por_categoria():
    conexao = conectar_bd()
    query = "SELECT categoria, COUNT(*) as total FROM veiculos GROUP BY categoria"
    df = pd.read_sql_query(query, conexao)
    conexao.close()
    return df






# ------------------ EXPORTAÇÃO DE DADOS ------------------

@app.route("/exportar/<tabela>/<formato>")
def exportar_dados(tabela, formato):
    """ Exporta dados do banco de dados para CSV ou Excel """
    conexao = conectar_bd()
    tabelas_validas = ["veiculos", "utilizadores", "reservas", "formas_pagamento"]

    if tabela not in tabelas_validas:
        return "Tabela inválida! Escolha entre: veiculos, utilizadores, reservas, formas_pagamento.", 400

    try:
        query = f"SELECT * FROM {tabela}"
        df = pd.read_sql_query(query, conexao)
    except Exception as e:
        return f"Erro ao consultar a tabela: {e}", 500
    finally:
        conexao.close()

    file_path = f"export_{tabela}.{formato}"

    try:
        if formato == "csv":
            df.to_csv(file_path, index=False)
        elif formato == "xlsx":
            df.to_excel(file_path, index=False, engine="openpyxl")
        else:
            return "Formato inválido! Escolha 'csv' ou 'xlsx'.", 400

        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return str(e), 500


# ------------------ VEÍCULOS ------------------

@app.route("/veiculos", methods=["GET", "POST"])
def listar_veiculos():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    filtro_marca = None
    filtro_modelo = None
    filtro_tipo = None
    filtro_categoria = None
    filtro_status = None
    parametros = []

    if request.method == "POST":
        filtro_marca = request.form.get("marca")
        filtro_modelo = request.form.get("modelo")
        filtro_tipo = request.form.get("tipo")
        filtro_categoria = request.form.get("categoria")
        filtro_status = request.form.get("status")

    query = "SELECT * FROM veiculos WHERE 1=1"

    if filtro_marca:
        query += " AND marca LIKE ?"
        parametros.append(f"%{filtro_marca}%")

    if filtro_modelo:
        query += " AND modelo LIKE ?"
        parametros.append(f"%{filtro_modelo}%")

    if filtro_tipo:
        query += " AND tipo = ?"
        parametros.append(filtro_tipo)

    if filtro_categoria:
        query += " AND categoria = ?"
        parametros.append(filtro_categoria)

    if filtro_status:
        query += " AND status = ?"
        parametros.append(filtro_status)

    cursor.execute(query, parametros)
    veiculos = cursor.fetchall()
    conexao.close()

    return render_template("vehicles.html",
                           veiculos=veiculos,
                           filtro_marca=filtro_marca,
                           filtro_modelo=filtro_modelo,
                           filtro_categoria=filtro_categoria,
                           filtro_status=filtro_status)



@app.route("/veiculos/novo", methods=["GET", "POST"])
def cadastrar_veiculo():
    if request.method == "POST":
        marca = request.form["marca"]
        modelo = request.form["modelo"]
        categoria = request.form["categoria"]
        transmissao = request.form["transmissao"]
        tipo = request.form["tipo"]
        capacidade = request.form["capacidade"]
        placa = request.form["placa"]
        diaria = request.form["diaria"]
        status = request.form["status"]
        ultima_revisao = request.form["ultima_revisao"]
        proxima_revisao = request.form["proxima_revisao"]
        inspecao = request.form["inspecao"]
        imagem = request.form.get("imagem") or None # Novo campo

        conexao = conectar_bd()
        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO veiculos 
            (marca, modelo, categoria, transmissao, tipo, capacidade, placa, diaria, status, ultima_revisao, proxima_revisao, inspecao, imagem)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (marca, modelo, categoria, transmissao, tipo, capacidade, placa, diaria, status, ultima_revisao, proxima_revisao, inspecao, imagem))

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_veiculos"))

    return render_template("add_vehicle.html")






@app.route("/editar_veiculo/<int:id>", methods=["GET", "POST"])
def editar_veiculo(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        marca = request.form["marca"]
        modelo = request.form["modelo"]
        categoria = request.form["categoria"]
        transmissao = request.form["transmissao"]
        tipo = request.form["tipo"]
        capacidade = request.form["capacidade"]
        imagem = request.form["imagem"]
        diaria = request.form["diaria"]
        ultima_revisao = request.form["ultima_revisao"]
        proxima_revisao = request.form["proxima_revisao"]
        inspecao = request.form["inspecao"]
        status = request.form["status"]
        placa = request.form["placa"]

        cursor.execute("""
            UPDATE veiculos SET
                marca = ?, modelo = ?, categoria = ?, transmissao = ?, tipo = ?, capacidade = ?, imagem = ?, diaria = ?,
                ultima_revisao = ?, proxima_revisao = ?, inspecao = ?, status = ?, placa = ?
            WHERE id = ?
        """, (
            marca, modelo, categoria, transmissao, tipo, capacidade, imagem, diaria,
            ultima_revisao, proxima_revisao, inspecao, status, placa, id
        ))

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_veiculos"))

    # GET
    cursor.execute("SELECT * FROM veiculos WHERE id = ?", (id,))
    veiculo = cursor.fetchone()
    conexao.close()
    return render_template("edit_vehicle.html", veiculo=veiculo)






@app.route("/veiculos/deletar/<int:id>", methods=["POST"])
def deletar_veiculo(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM veiculos WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("listar_veiculos"))


#------------------- MANUTENCAO -------------------------------

@app.route("/manutencoes", methods=["GET", "POST"])
def listar_manutencoes():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    filtro_veiculo = None
    filtro_data_inicio = None
    filtro_data_fim = None
    parametros = []

    if request.method == "POST":
        filtro_veiculo = request.form.get("veiculo")
        filtro_data_inicio = request.form.get("data_inicio")
        filtro_data_fim = request.form.get("data_fim")

    query = """
        SELECT m.id, v.modelo, v.placa, m.descricao, m.custo, m.data
        FROM manutencoes m
        JOIN veiculos v ON m.veiculo_id = v.id
        WHERE 1=1
    """

    if filtro_veiculo:
        query += " AND v.modelo LIKE ?"
        parametros.append(f"%{filtro_veiculo}%")

    if filtro_data_inicio:
        query += " AND m.data >= ?"
        parametros.append(filtro_data_inicio)

    if filtro_data_fim:
        query += " AND m.data <= ?"
        parametros.append(filtro_data_fim)

    cursor.execute(query, parametros)
    manutencoes = cursor.fetchall()
    conexao.close()

    return render_template("manutencoes.html",
                           manutencoes=manutencoes,
                           filtro_veiculo=filtro_veiculo,
                           filtro_data_inicio=filtro_data_inicio,
                           filtro_data_fim=filtro_data_fim)


@app.route("/manutencoes/novo", methods=["GET", "POST"])
def adicionar_manutencao():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        veiculo_id = request.form["veiculo_id"]
        descricao = request.form["descricao"]
        custo = request.form["custo"]
        data = request.form["data"]

        cursor.execute("""
            INSERT INTO manutencoes (veiculo_id, descricao, custo, data)
            VALUES (?, ?, ?, ?)
        """, (veiculo_id, descricao, custo, data))

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_manutencoes"))

    cursor.execute("SELECT id, modelo, placa FROM veiculos")
    veiculos = cursor.fetchall()
    conexao.close()
    return render_template("add_manutencao.html", veiculos=veiculos)


@app.route("/manutencoes/editar/<int:id>", methods=["GET", "POST"])
def editar_manutencao(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        veiculo_id = request.form["veiculo_id"]
        descricao = request.form["descricao"]
        custo = request.form["custo"]
        data = request.form["data"]

        cursor.execute("""
            UPDATE manutencoes SET veiculo_id=?, descricao=?, custo=?, data=?
            WHERE id=?
        """, (veiculo_id, descricao, custo, data, id))

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_manutencoes"))

    cursor.execute("SELECT * FROM manutencoes WHERE id=?", (id,))
    manutencao = cursor.fetchone()
    cursor.execute("SELECT id, modelo, placa FROM veiculos")
    veiculos = cursor.fetchall()
    conexao.close()
    return render_template("edit_manutencao.html", manutencao=manutencao, veiculos=veiculos)


@app.route("/manutencoes/deletar/<int:id>", methods=["POST"])
def deletar_manutencao(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM manutencoes WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("listar_manutencoes"))





# ------------------ RELATÓRIO DE MANUTENÇÃO ------------------

@app.route("/relatorio_manutencao")
def relatorio_manutencao():
    """ Gera um relatório de manutenção em Excel """
    conexao = conectar_bd()

    try:
        query = """
        SELECT v.modelo, v.placa, m.descricao, m.custo, m.data
        FROM manutencoes m
        JOIN veiculos v ON m.veiculo_id = v.id
        """
        df = pd.read_sql_query(query, conexao)
    except Exception as e:
        return f"Erro ao gerar relatório: {e}", 500
    finally:
        conexao.close()

    file_path = "relatorio_manutencao.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# ------------------ CLIENTES ------------------

@app.route("/clientes", methods=["GET", "POST"])
def listar_clientes():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    # Inicializa os filtros com None
    filtro_nome = None
    filtro_email = None
    filtro_telefone = None
    parametros = []

    if request.method == "POST":
        filtro_nome = request.form.get("nome")
        filtro_email = request.form.get("email")
        filtro_telefone = request.form.get("telefone")

    # Monta a query dinamicamente
    query = "SELECT * FROM clientes WHERE 1=1"

    if filtro_nome:
        query += " AND nome LIKE ?"
        parametros.append(f"%{filtro_nome}%")

    if filtro_email:
        query += " AND email LIKE ?"
        parametros.append(f"%{filtro_email}%")

    if filtro_telefone:
        query += " AND telefone LIKE ?"
        parametros.append(f"%{filtro_telefone}%")

    cursor.execute(query, parametros)
    clientes = cursor.fetchall()
    conexao.close()

    return render_template("users.html",
                           clientes=clientes,
                           filtro_nome=filtro_nome,
                           filtro_email=filtro_email,
                           filtro_telefone=filtro_telefone)




@app.route("/clientes/novo", methods=["GET", "POST"])
def adicionar_cliente():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        telefone = request.form["telefone"]

        conexao = conectar_bd()
        cursor = conexao.cursor()
        cursor.execute("INSERT INTO clientes (nome, email, telefone) VALUES (?, ?, ?)", (nome, email, telefone))
        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_clientes"))

    return render_template("add_user.html")


@app.route("/clientes/editar/<int:id>", methods=["GET", "POST"])
def editar_cliente(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        telefone = request.form["telefone"]

        cursor.execute("UPDATE clientes SET nome=?, email=?, telefone=? WHERE id=?", (nome, email, telefone, id))
        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_clientes"))

    cursor.execute("SELECT * FROM clientes WHERE id=?", (id,))
    cliente = cursor.fetchone()
    conexao.close()
    return render_template("edit_user.html", cliente=cliente)


@app.route("/clientes/deletar/<int:id>", methods=["POST"])
def deletar_cliente(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM clientes WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("listar_clientes"))


# ------------------ RESERVAS ------------------

@app.route("/reservas", methods=["GET", "POST"])
def listar_reservas():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    filtro_cliente = None
    filtro_veiculo = None
    filtro_status = None
    filtro_data_inicio = None
    filtro_data_fim = None
    parametros = []

    if request.method == "POST":
        filtro_cliente = request.form.get("cliente")
        filtro_veiculo = request.form.get("veiculo")
        filtro_status = request.form.get("status")
        filtro_data_inicio = request.form.get("data_inicio")
        filtro_data_fim = request.form.get("data_fim")

    query = """
        SELECT r.id, c.nome, v.modelo, r.data_inicio, r.data_fim, r.status
        FROM reservas r
        JOIN clientes c ON r.cliente_id = c.id
        JOIN veiculos v ON r.veiculo_id = v.id
        WHERE 1=1
    """

    if filtro_cliente:
        query += " AND c.nome LIKE ?"
        parametros.append(f"%{filtro_cliente}%")

    if filtro_veiculo:
        query += " AND v.modelo LIKE ?"
        parametros.append(f"%{filtro_veiculo}%")

    if filtro_status:
        query += " AND r.status = ?"
        parametros.append(filtro_status)

    if filtro_data_inicio:
        query += " AND r.data_inicio >= ?"
        parametros.append(filtro_data_inicio)

    if filtro_data_fim:
        query += " AND r.data_fim <= ?"
        parametros.append(filtro_data_fim)

    cursor.execute(query, parametros)
    reservas = cursor.fetchall()
    conexao.close()

    return render_template("reservas.html",
                           reservas=reservas,
                           filtro_cliente=filtro_cliente,
                           filtro_veiculo=filtro_veiculo,
                           filtro_status=filtro_status,
                           filtro_data_inicio=filtro_data_inicio,
                           filtro_data_fim=filtro_data_fim)


@app.route("/reservas/novo", methods=["GET", "POST"])
def adicionar_reserva():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        veiculo_id = request.form["veiculo_id"]
        cliente_id = request.form["cliente_id"]
        data_inicio = request.form["data_inicio"]
        data_fim = request.form["data_fim"]
        status = request.form["status"]

        cursor.execute("""
            INSERT INTO reservas (veiculo_id, cliente_id, data_inicio, data_fim, status)
            VALUES (?, ?, ?, ?, ?)
        """, (veiculo_id, cliente_id, data_inicio, data_fim, status))

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_reservas"))

    # Buscar clientes e veículos para os selects
    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    cursor.execute("SELECT id, modelo FROM veiculos")
    veiculos = cursor.fetchall()
    conexao.close()
    return render_template("add_reserva.html", clientes=clientes, veiculos=veiculos)


@app.route("/reservas/editar/<int:id>", methods=["GET", "POST"])
def editar_reserva(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        veiculo_id = request.form["veiculo_id"]
        cliente_id = request.form["cliente_id"]
        data_inicio = request.form["data_inicio"]
        data_fim = request.form["data_fim"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE reservas SET veiculo_id=?, cliente_id=?, data_inicio=?, data_fim=?, status=?
            WHERE id=?
        """, (veiculo_id, cliente_id, data_inicio, data_fim, status, id))

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_reservas"))

    # Dados da reserva
    cursor.execute("SELECT * FROM reservas WHERE id=?", (id,))
    reserva = cursor.fetchone()

    # Listas para dropdown
    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    cursor.execute("SELECT id, modelo FROM veiculos")
    veiculos = cursor.fetchall()

    conexao.close()
    return render_template("edit_reserva.html", reserva=reserva, clientes=clientes, veiculos=veiculos)


@app.route("/reservas/deletar/<int:id>", methods=["POST"])
def deletar_reserva(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM reservas WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("listar_reservas"))


# ------------------ PAGAMENTOS ------------------

@app.route("/pagamentos", methods=["GET", "POST"])
def listar_pagamentos():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    filtro_status = None
    filtro_cliente = None
    filtro_data_inicio = None
    filtro_data_fim = None

    if request.method == "POST":
        filtro_status = request.form.get("status")
        filtro_cliente = request.form.get("cliente")
        filtro_data_inicio = request.form.get("data_inicio")
        filtro_data_fim = request.form.get("data_fim")

    query = """
        SELECT 
            p.id, 
            c.id AS cliente_id, 
            c.nome, 
            f.id AS forma_id, 
            f.tipo, 
            p.valor, 
            p.data_pagamento, 
            p.status
        FROM pagamentos p
        JOIN reservas r ON p.reserva_id = r.id
        JOIN clientes c ON r.cliente_id = c.id
        JOIN formas_pagamento f ON p.forma_pagamento_id = f.id
        WHERE 1=1
    """

    parametros = []

    if filtro_status:
        query += " AND p.status = ?"
        parametros.append(filtro_status)

    if filtro_cliente:
        query += " AND c.nome LIKE ?"
        parametros.append(f"%{filtro_cliente}%")

    if filtro_data_inicio:
        query += " AND p.data_pagamento >= ?"
        parametros.append(filtro_data_inicio)

    if filtro_data_fim:
        query += " AND p.data_pagamento <= ?"
        parametros.append(filtro_data_fim)

    cursor.execute(query, parametros)
    pagamentos = cursor.fetchall()
    conexao.close()
    return render_template(
        "payments.html",
        pagamentos=pagamentos,
        filtro_status=filtro_status,
        filtro_cliente=filtro_cliente,
        filtro_data_inicio=filtro_data_inicio,
        filtro_data_fim=filtro_data_fim
    )


@app.route("/pagamentos/novo", methods=["GET", "POST"])
def adicionar_pagamento():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        reserva_id = request.form["reserva_id"]
        forma_pagamento_id = request.form["forma_pagamento_id"]  # 🔧 corrigido aqui
        valor = request.form["valor"]
        data_pagamento = request.form["data_pagamento"]
        status = request.form["status"]

        cursor.execute("""
            INSERT INTO pagamentos (reserva_id, forma_pagamento_id, valor, data_pagamento, status)
            VALUES (?, ?, ?, ?, ?)
        """, (reserva_id, forma_pagamento_id, valor, data_pagamento, status))  # 🔧 corrigido aqui também

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_pagamentos"))

    cursor.execute("SELECT id FROM reservas")
    reservas = cursor.fetchall()

    cursor.execute("SELECT id, tipo FROM formas_pagamento")
    formas = cursor.fetchall()

    conexao.close()
    return render_template("add_payment.html", reservas=reservas, formas=formas)




@app.route("/pagamentos/editar/<int:id>", methods=["GET", "POST"])
def editar_pagamento(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        reserva_id = request.form["reserva_id"]
        forma_id = request.form["forma_id"]
        valor = request.form["valor"]
        data_pagamento = request.form["data_pagamento"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE pagamentos SET reserva_id=?, forma_pagamento_id=?, valor=?, data_pagamento=?, status=?
            WHERE id=?
        """, (reserva_id, forma_id, valor, data_pagamento, status, id))

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_pagamentos"))

    cursor.execute("SELECT * FROM pagamentos WHERE id=?", (id,))
    pagamento = cursor.fetchone()

    cursor.execute("SELECT id FROM reservas")
    reservas = cursor.fetchall()

    # 🔧 Correção aqui
    cursor.execute("SELECT id, tipo FROM formas_pagamento")
    formas = cursor.fetchall()

    conexao.close()
    return render_template("edit_payment.html", pagamento=pagamento, reservas=reservas, formas=formas)



@app.route("/pagamentos/deletar/<int:id>", methods=["POST"])
def deletar_pagamento(id):
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM pagamentos WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("listar_pagamentos"))

@app.route("/exportar_pagamentos/<formato>", methods=["GET", "POST"])
def exportar_pagamentos(formato):
    conexao = conectar_bd()
    cursor = conexao.cursor()

    # Coletar filtros (caso venham via POST)
    filtro_status = request.form.get("status")
    filtro_cliente = request.form.get("cliente")
    filtro_data_inicio = request.form.get("data_inicio")
    filtro_data_fim = request.form.get("data_fim")

    query = """
        SELECT 
            p.id AS pagamento_id,
            c.id AS cliente_id,
            c.nome AS cliente,
            f.id AS forma_pagamento_id,
            f.tipo AS forma_pagamento,
            p.valor,
            p.data_pagamento,
            p.status
        FROM pagamentos p
        JOIN reservas r ON p.reserva_id = r.id
        JOIN clientes c ON r.cliente_id = c.id
        JOIN formas_pagamento f ON p.forma_pagamento_id = f.id
        WHERE 1=1
    """

    parametros = []

    if filtro_status:
        query += " AND p.status = ?"
        parametros.append(filtro_status)
    if filtro_cliente:
        query += " AND c.nome LIKE ?"
        parametros.append(f"%{filtro_cliente}%")
    if filtro_data_inicio:
        query += " AND p.data_pagamento >= ?"
        parametros.append(filtro_data_inicio)
    if filtro_data_fim:
        query += " AND p.data_pagamento <= ?"
        parametros.append(filtro_data_fim)

    df = pd.read_sql_query(query, conexao, params=parametros)
    conexao.close()

    nome_arquivo = f"pagamentos_exportados.{formato}"

    if formato == "csv":
        df.to_csv(nome_arquivo, index=False)
    elif formato == "xlsx":
        df.to_excel(nome_arquivo, index=False, engine="openpyxl")
    else:
        return "Formato inválido. Use 'csv' ou 'xlsx'.", 400

    return send_file(nome_arquivo, as_attachment=True)


#------------------ Obter ultimos clientes ----------------

def obter_ultimos_clientes(limit=5):
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT nome, email, telefone
        FROM clientes
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    ultimos = cursor.fetchall()
    conexao.close()
    return ultimos

#------------------- Obter reservas e finacas --------------

def obter_reservas_e_financas_mes():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    hoje = date.today()
    ano = hoje.year
    mes = hoje.month

    # Total de reservas
    cursor.execute("""
        SELECT COUNT(*) FROM reservas
        WHERE strftime('%Y', data_inicio) = ? AND strftime('%m', data_inicio) = ?
    """, (str(ano), f"{mes:02}"))
    total_reservas = cursor.fetchone()[0]

    # Total financeiro dos pagamentos com status 'pago'
    cursor.execute("""
        SELECT SUM(valor) FROM pagamentos
        WHERE strftime('%Y', data_pagamento) = ? AND strftime('%m', data_pagamento) = ? AND status = 'pago'
    """, (str(ano), f"{mes:02}"))
    total_financeiro = cursor.fetchone()[0] or 0

    conexao.close()
    return total_reservas, total_financeiro


#------------------- exportar tudo ---------------

@app.route("/exportar_tudo/<formato>")
def exportar_tudo(formato):
    conexao = conectar_bd()

    try:
        # Carrega todas as tabelas principais
        df_veiculos = pd.read_sql_query("SELECT * FROM veiculos", conexao)
        df_reservas = pd.read_sql_query("SELECT * FROM reservas", conexao)
        df_manutencoes = pd.read_sql_query("SELECT * FROM manutencoes", conexao)
        df_pagamentos = pd.read_sql_query("""
            SELECT 
                p.*, 
                c.nome AS cliente, 
                f.tipo AS forma_pagamento
            FROM pagamentos p
            JOIN reservas r ON p.reserva_id = r.id
            JOIN clientes c ON r.cliente_id = c.id
            JOIN formas_pagamento f ON p.forma_pagamento_id = f.id
        """, conexao)

        # Resumo financeiro
        hoje = date.today()
        ano, mes = hoje.year, hoje.month
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM reservas
            WHERE strftime('%Y', data_inicio) = ? AND strftime('%m', data_inicio) = ?
        """, (str(ano), f"{mes:02}"))
        total_reservas = cursor.fetchone()[0]

        cursor.execute("""
            SELECT SUM(valor) FROM pagamentos
            WHERE strftime('%Y', data_pagamento) = ? AND strftime('%m', data_pagamento) = ? AND status = 'pago'
        """, (str(ano), f"{mes:02}"))
        total_financeiro = cursor.fetchone()[0] or 0

        df_resumo = pd.DataFrame([{
            "Mês": f"{mes:02}/{ano}",
            "Total de Reservas": total_reservas,
            "Faturamento Confirmado (R$)": total_financeiro
        }])

    finally:
        conexao.close()

    nome_arquivo = f"relatorio_completo.{formato}"

    if formato == "xlsx":
        with pd.ExcelWriter(nome_arquivo, engine="openpyxl") as writer:
            df_veiculos.to_excel(writer, sheet_name="Veículos", index=False)
            df_reservas.to_excel(writer, sheet_name="Reservas", index=False)
            df_manutencoes.to_excel(writer, sheet_name="Manutenções", index=False)
            df_pagamentos.to_excel(writer, sheet_name="Pagamentos", index=False)
            df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
    elif formato == "csv":
        df_veiculos.to_csv("veiculos.csv", index=False)
        df_reservas.to_csv("reservas.csv", index=False)
        df_manutencoes.to_csv("manutencoes.csv", index=False)
        df_pagamentos.to_csv("pagamentos.csv", index=False)
        df_resumo.to_csv("resumo.csv", index=False)
        return "Dados exportados em arquivos CSV separados com sucesso."
    else:
        return "Formato inválido. Use 'xlsx' ou 'csv'.", 400

    return send_file(nome_arquivo, as_attachment=True)








# ------------------ INICIALIZAÇÃO DO APP ------------------

if __name__ == "__main__":
    app.run(debug=True, port=5001)
