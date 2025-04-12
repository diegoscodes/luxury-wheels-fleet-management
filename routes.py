from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session
from database import conectar_bd
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

routes = Blueprint('routes', __name__)

# -------------------- LOGIN --------------------
@routes.route("/login", methods=["GET", "POST"])
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
            return redirect(url_for("routes.home"))
        else:
            flash("Usuário ou senha inválidos", "danger")
    return render_template("login.html")


@routes.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("routes.login"))

# -------------------- HOME --------------------
@routes.route("/")
def home():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))
    return render_template("index.html")

# -------------------- DASHBOARD --------------------
@routes.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    query = "SELECT strftime('%Y-%m', data) AS mes, SUM(custo) AS total FROM manutencoes GROUP BY mes"
    df = pd.read_sql(query, conexao)
    conexao.close()

    grafico_url = None
    if not df.empty:
        fig, ax = plt.subplots()
        ax.plot(df['mes'], df['total'], marker='o', linestyle='-')
        ax.set_xlabel('Mês')
        ax.set_ylabel('Custo Total')
        ax.set_title('Custos de Manutenção por Mês')
        plt.xticks(rotation=45)

        img = io.BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)
        grafico_url = base64.b64encode(img.getvalue()).decode('utf8')

    return render_template("dashboard.html", grafico_url=grafico_url)


# ------------------ VEÍCULOS ------------------
@routes.route("/veiculos")
def listar_veiculos():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM veiculos")
    veiculos = cursor.fetchall()
    conexao.close()
    return render_template("vehicles.html", veiculos=veiculos)


@routes.route("/veiculos/novo", methods=["GET", "POST"])
def cadastrar_veiculo():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        dados = (
            request.form["marca"], request.form["modelo"], request.form["categoria"],
            request.form["transmissao"], request.form["tipo"], request.form["capacidade"],
            request.form["placa"], request.form["diaria"], request.form["status"],
            request.form["ultima_revisao"], request.form["proxima_revisao"], request.form["inspecao"]
        )
        conexao = conectar_bd()
        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO veiculos (marca, modelo, categoria, transmissao, tipo, capacidade, placa,
            diaria, status, ultima_revisao, proxima_revisao, inspecao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dados)
        conexao.commit()
        conexao.close()
        return redirect(url_for("routes.listar_veiculos"))
    return render_template("add_vehicle.html")


@routes.route("/veiculos/editar/<int:id>", methods=["GET", "POST"])
def editar_veiculo(id):
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()
    if request.method == "POST":
        dados = (
            request.form["marca"], request.form["modelo"], request.form["categoria"],
            request.form["transmissao"], request.form["tipo"], request.form["capacidade"],
            request.form["placa"], request.form["diaria"], request.form["status"],
            request.form["ultima_revisao"], request.form["proxima_revisao"], request.form["inspecao"], id
        )
        cursor.execute("""
            UPDATE veiculos SET marca=?, modelo=?, categoria=?, transmissao=?, tipo=?, capacidade=?,
            placa=?, diaria=?, status=?, ultima_revisao=?, proxima_revisao=?, inspecao=? WHERE id=?
        """, dados)
        conexao.commit()
        conexao.close()
        return redirect(url_for("routes.listar_veiculos"))
    cursor.execute("SELECT * FROM veiculos WHERE id=?", (id,))
    veiculo = cursor.fetchone()
    conexao.close()
    return render_template("edit_vehicle.html", veiculo=veiculo)


@routes.route("/veiculos/deletar/<int:id>", methods=["POST"])
def deletar_veiculo(id):
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM veiculos WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("routes.listar_veiculos"))

# ------------------ CLIENTES ------------------
@routes.route("/clientes")
def listar_clientes():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()
    conexao.close()
    return render_template("users.html", clientes=clientes)


@routes.route("/clientes/novo", methods=["GET", "POST"])
def adicionar_cliente():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        telefone = request.form["telefone"]
        conexao = conectar_bd()
        cursor = conexao.cursor()
        cursor.execute("INSERT INTO clientes (nome, email, telefone) VALUES (?, ?, ?)", (nome, email, telefone))
        conexao.commit()
        conexao.close()
        return redirect(url_for("routes.listar_clientes"))
    return render_template("add_user.html")


@routes.route("/clientes/editar/<int:id>", methods=["GET", "POST"])
def editar_cliente(id):
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        telefone = request.form["telefone"]
        cursor.execute("UPDATE clientes SET nome=?, email=?, telefone=? WHERE id=?", (nome, email, telefone, id))
        conexao.commit()
        conexao.close()
        return redirect(url_for("routes.listar_clientes"))
    cursor.execute("SELECT * FROM clientes WHERE id=?", (id,))
    cliente = cursor.fetchone()
    conexao.close()
    return render_template("edit_user.html", cliente=cliente)


@routes.route("/clientes/deletar/<int:id>", methods=["POST"])
def deletar_cliente(id):
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM clientes WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("routes.listar_clientes"))


# ------------------ RESERVAS ------------------
@routes.route("/reservas")
def listar_reservas():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

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


@routes.route("/reservas/novo", methods=["GET", "POST"])
def adicionar_reserva():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        dados = (
            request.form["veiculo_id"],
            request.form["cliente_id"],
            request.form["data_inicio"],
            request.form["data_fim"],
            request.form["status"]
        )
        cursor.execute("""
            INSERT INTO reservas (veiculo_id, cliente_id, data_inicio, data_fim, status)
            VALUES (?, ?, ?, ?, ?)
        """, dados)
        conexao.commit()
        conexao.close()
        return redirect(url_for("routes.listar_reservas"))

    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    cursor.execute("SELECT id, modelo FROM veiculos")
    veiculos = cursor.fetchall()
    conexao.close()
    return render_template("add_reserva.html", clientes=clientes, veiculos=veiculos)


@routes.route("/reservas/editar/<int:id>", methods=["GET", "POST"])
def editar_reserva(id):
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        dados = (
            request.form["veiculo_id"],
            request.form["cliente_id"],
            request.form["data_inicio"],
            request.form["data_fim"],
            request.form["status"],
            id
        )
        cursor.execute("""
            UPDATE reservas SET veiculo_id=?, cliente_id=?, data_inicio=?, data_fim=?, status=? WHERE id=?
        """, dados)
        conexao.commit()
        conexao.close()
        return redirect(url_for("routes.listar_reservas"))

    cursor.execute("SELECT * FROM reservas WHERE id=?", (id,))
    reserva = cursor.fetchone()
    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    cursor.execute("SELECT id, modelo FROM veiculos")
    veiculos = cursor.fetchall()
    conexao.close()
    return render_template("edit_reserva.html", reserva=reserva, clientes=clientes, veiculos=veiculos)


@routes.route("/reservas/deletar/<int:id>", methods=["POST"])
def deletar_reserva(id):
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM reservas WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("routes.listar_reservas"))


# ------------------ PAGAMENTOS ------------------
@routes.route("/pagamentos", methods=["GET", "POST"])
def listar_pagamentos():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()

    query = """
        SELECT 
            p.id, 
            c.nome, 
            f.tipo, 
            p.valor, 
            p.data_pagamento, 
            p.status
        FROM pagamentos p
        JOIN reservas r ON p.reserva_id = r.id
        JOIN clientes c ON r.cliente_id = c.id
        JOIN formas_pagamento f ON p.forma_pagamento_id = f.id
    """

    cursor.execute(query)
    pagamentos = cursor.fetchall()
    conexao.close()
    return render_template("payments.html", pagamentos=pagamentos)


@routes.route("/pagamentos/novo", methods=["GET", "POST"])
def adicionar_pagamento():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        dados = (
            request.form["reserva_id"],
            request.form["forma_pagamento_id"],
            request.form["valor"],
            request.form["data_pagamento"],
            request.form["status"]
        )
        cursor.execute("""
            INSERT INTO pagamentos (reserva_id, forma_pagamento_id, valor, data_pagamento, status)
            VALUES (?, ?, ?, ?, ?)
        """, dados)
        conexao.commit()
        conexao.close()
        return redirect(url_for("routes.listar_pagamentos"))

    cursor.execute("SELECT id FROM reservas")
    reservas = cursor.fetchall()
    cursor.execute("SELECT id, tipo FROM formas_pagamento")
    formas = cursor.fetchall()
    conexao.close()
    return render_template("add_payment.html", reservas=reservas, formas=formas)


@routes.route("/pagamentos/editar/<int:id>", methods=["GET", "POST"])
def editar_pagamento(id):
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()

    if request.method == "POST":
        dados = (
            request.form["reserva_id"],
            request.form["forma_pagamento_id"],
            request.form["valor"],
            request.form["data_pagamento"],
            request.form["status"],
            id
        )
        cursor.execute("""
            UPDATE pagamentos SET reserva_id=?, forma_pagamento_id=?, valor=?, data_pagamento=?, status=?
            WHERE id=?
        """, dados)
        conexao.commit()
        conexao.close()
        return redirect(url_for("routes.listar_pagamentos"))

    cursor.execute("SELECT * FROM pagamentos WHERE id=?", (id,))
    pagamento = cursor.fetchone()
    cursor.execute("SELECT id FROM reservas")
    reservas = cursor.fetchall()
    cursor.execute("SELECT id, tipo FROM formas_pagamento")
    formas = cursor.fetchall()
    conexao.close()
    return render_template("edit_payment.html", pagamento=pagamento, reservas=reservas, formas=formas)


@routes.route("/pagamentos/deletar/<int:id>", methods=["POST"])
def deletar_pagamento(id):
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM pagamentos WHERE id=?", (id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("routes.listar_pagamentos"))


# ------------------ RELATÓRIO MANUTENÇÃO ------------------
@routes.route("/relatorio_manutencao")
def relatorio_manutencao():
    if "usuario" not in session:
        return redirect(url_for("routes.login"))

    conexao = conectar_bd()
    query = """
    SELECT v.modelo, v.placa, m.descricao, m.custo, m.data
    FROM manutencoes m
    JOIN veiculos v ON m.veiculo_id = v.id
    """
    df = pd.read_sql(query, conexao)
    conexao.close()

    file_path = "relatorio_manutencao.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)
