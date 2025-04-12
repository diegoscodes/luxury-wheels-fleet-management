import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Obtém a pasta do script
DB_PATH = os.path.join(BASE_DIR, "luxurywheels.db")   # Junta com o banco de dados

def conectar_bd():
    return sqlite3.connect(DB_PATH)



def criar_tabelas():
    conexao = conectar_bd()
    cursor = conexao.cursor()

    # Tabela de usuários para login
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            senha TEXT NOT NULL
        )
        """)

    # Criar um usuário admin se não existir
    cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (nome, usuario, senha) VALUES (?, ?, ?)",
                       ("Administrador", "admin", "123"))  # Você pode mudar depois
        print("🛠️ Usuário admin criado: admin / 123")

    cursor.execute('''CREATE TABLE IF NOT EXISTS veiculos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        marca TEXT NOT NULL,
                        modelo TEXT NOT NULL,
                        categoria TEXT,
                        transmissao TEXT,
                        tipo TEXT,
                        capacidade INTEGER,
                        imagem TEXT,
                        diaria REAL,
                        ultima_revisao DATE,
                        proxima_revisao DATE,
                        inspecao DATE,
                        status TEXT,
                        placa TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL,
                        email TEXT NOT NULL,
                        telefone TEXT NOT NULL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS reservas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        veiculo_id INTEGER,
                        cliente_id INTEGER,
                        data_inicio DATE,
                        data_fim DATE,
                        status TEXT,
                        FOREIGN KEY (veiculo_id) REFERENCES veiculos(id),
                        FOREIGN KEY (cliente_id) REFERENCES clientes(id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS utilizadores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        senha TEXT NOT NULL,
                        tipo TEXT CHECK(tipo IN ('admin', 'cliente')) NOT NULL);''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS formas_pagamento (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tipo TEXT NOT NULL,descricao TEXT);''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS pagamentos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        reserva_id INTEGER NOT NULL,
                        forma_pagamento_id INTEGER NOT NULL,
                        valor REAL NOT NULL,
                        data_pagamento DATE NOT NULL,
                        status TEXT CHECK(status IN ('pendente', 'pago', 'cancelado')) NOT NULL,
                        FOREIGN KEY (reserva_id) REFERENCES reservas(id),
                        FOREIGN KEY (forma_pagamento_id) REFERENCES formas_pagamento(id));''')


    cursor.execute('''CREATE TABLE IF NOT EXISTS manutencoes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            veiculo_id INTEGER NOT NULL,
                            descricao TEXT NOT NULL,
                            custo REAL NOT NULL,
                            data DATE NOT NULL,
                            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id));''')

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT,
                telefone TEXT
            )
        """)

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    criar_tabelas()
