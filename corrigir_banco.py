import sqlite3

# Conecte ao banco de dados existente
con = sqlite3.connect("luxurywheels.db")
cur = con.cursor()

try:
    # Tenta adicionar a coluna "nome" se ainda não existir
    cur.execute("ALTER TABLE usuarios ADD COLUMN nome TEXT;")
    con.commit()
    print("✅ Coluna 'nome' adicionada com sucesso!")
except sqlite3.OperationalError as e:
    print("⚠️ Erro (possivelmente já existe a coluna):", e)

con.close()
