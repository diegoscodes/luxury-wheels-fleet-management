from flask import Flask, render_template, request, redirect, send_file, url_for, flash
from database import criar_tabelas, conectar_bd
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from flask import session
import matplotlib
matplotlib.use("Agg")  # ⬅️ Linha que evita uso de GUI
import matplotlib.pyplot as plt

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

@app.route("/")
def home():
    if "usuario" not in session:
        return redirect(url_for("login"))
    vencidas, proximas = buscar_revisoes_pendentes()
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
        cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (usuario, senha))
        user = cursor.fetchone()
        conexao.close()

        if user:
            session["usuario"] = user[1]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("home"))
        else:
            flash("Usuário ou senha inválidos", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))


#-----------------busca revisoes pendente --------------------
def buscar_revisoes_pendentes():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    hoje = datetime.today().date()
    limite = hoje + timedelta(days=5)

    # Revisões vencidas
    cursor.execute("""
        SELECT id, modelo, placa, proxima_revisao
        FROM veiculos
        WHERE proxima_revisao IS NOT NULL
          AND DATE(proxima_revisao) < ?
    """, (hoje,))
    vencidas = cursor.fetchall()

    # Revisões nos próximos 5 dias
    cursor.execute("""
        SELECT id, modelo, placa, proxima_revisao
        FROM veiculos
        WHERE proxima_revisao IS NOT NULL
          AND DATE(proxima_revisao) BETWEEN ? AND ?
    """, (hoje, limite))
    proximas = cursor.fetchall()

    conexao.close()

    # Enviar email uma vez por dia às 8h, se houver revisões próximas
    if datetime.now().hour == 8 and proximas:
        enviar_email_alerta(proximas)

    return vencidas, proximas






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
    return df_veiculos, df_reservas, df_manutencoes


def gerar_grafico(df, x_col, titulo):
    """ Gera um gráfico de barras e o converte em base64 """
    if df.empty or x_col not in df.columns:
        return None  # Retorna None se não houver dados

    plt.figure(figsize=(6, 4))
    df[x_col].value_counts().plot(kind="bar", color="royalblue")
    plt.title(titulo)
    plt.xlabel(x_col)
    plt.ylabel("Quantidade")

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

@app.route("/dashboard")
def dashboard():
    df_veiculos, df_reservas, df_manutencoes = obter_dados_dashboard()

    grafico_reservas = gerar_grafico(df_reservas, "veiculo_id", "Reservas por Veículo")
    grafico_manutencao = gerar_grafico(df_manutencoes, "veiculo_id", "Manutenções por Veículo")

    total_veiculos = len(df_veiculos)
    total_reservas = len(df_reservas)
    total_manutencoes = len(df_manutencoes)

    vencidas, proximas = buscar_revisoes_pendentes()

    return render_template(
        "dashboard.html",
        total_veiculos=total_veiculos,
        total_reservas=total_reservas,
        total_manutencoes=total_manutencoes,
        grafico_reservas=grafico_reservas,
        grafico_manutencao=grafico_manutencao,
        vencidas=vencidas,
        proximas=proximas
    )




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
    conexao.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    cursor = conexao.cursor()

    if request.method == "POST":
        filtro_ano = request.form["ano"]
        cursor.execute("SELECT * FROM veiculos WHERE ano=?", (filtro_ano,))
    else:
        cursor.execute("SELECT * FROM veiculos")

    veiculos = cursor.fetchall()
    conexao.close()
    print("🚗 Dados carregados do banco:", [dict(v) for v in veiculos])  # Debug mais legível
    return render_template("vehicles.html", veiculos=veiculos)



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
        imagem = request.form["imagem"]  # Novo campo

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





@app.route("/veiculos/editar/<int:id>", methods=["GET", "POST"])
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
        placa = request.form["placa"]
        diaria = request.form["diaria"]
        status = request.form["status"]
        ultima_revisao = request.form["ultima_revisao"]
        proxima_revisao = request.form["proxima_revisao"]
        inspecao = request.form["inspecao"]
        imagem = request.form["imagem"]  # Novo campo

        cursor.execute("""
            UPDATE veiculos SET 
                marca=?, modelo=?, categoria=?, transmissao=?, tipo=?, capacidade=?, 
                placa=?, diaria=?, status=?, ultima_revisao=?, proxima_revisao=?, inspecao=?, imagem=?
            WHERE id=?
        """, (marca, modelo, categoria, transmissao, tipo, capacidade, placa, diaria, status, ultima_revisao, proxima_revisao, inspecao, imagem, id))

        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_veiculos"))

    cursor.execute("SELECT * FROM veiculos WHERE id=?", (id,))
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

@app.route("/manutencoes")
def listar_manutencoes():
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT m.id, v.modelo, v.placa, m.descricao, m.custo, m.data
        FROM manutencoes m
        JOIN veiculos v ON m.veiculo_id = v.id
    """)
    manutencoes = cursor.fetchall()
    conexao.close()
    return render_template("manutencoes.html", manutencoes=manutencoes)


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

@app.route("/clientes")
def listar_clientes():
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()
    conexao.close()
    return render_template("users.html", clientes=clientes)



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

@app.route("/reservas")
def listar_reservas():
    conexao = conectar_bd()
    cursor = conexao.cursor()
    query = """
        SELECT r.id, c.nome, v.modelo, r.data_inicio, r.data_fim, r.status
        FROM reservas r
        JOIN clientes c ON r.cliente_id = c.id
        JOIN veiculos v ON r.veiculo_id = v.id
    """
    cursor.execute(query)
    reservas = cursor.fetchall()
    conexao.close()
    return render_template("reservas.html", reservas=reservas)


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
            UPDATE pagamentos SET reserva_id=?, forma_id=?, valor=?, data_pagamento=?, status=?
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






# ------------------ INICIALIZAÇÃO DO APP ------------------

if __name__ == "__main__":
    app.run(debug=True, port=5001)
