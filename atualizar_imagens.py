import os
import sqlite3

# Caminho para o banco de dados
CAMINHO_DB = "luxurywheels.db"  # Altere se estiver em outro lugar

# Caminho para a pasta de imagens
PASTA_IMAGENS = os.path.join("static", "imagens")

# Conecta ao banco
con = sqlite3.connect(CAMINHO_DB)
cur = con.cursor()

# Lista todos os veículos
cur.execute("SELECT id, modelo FROM veiculos")
veiculos = cur.fetchall()

# Para cada veículo, verifica se existe uma imagem correspondente
for v in veiculos:
    veiculo_id, modelo = v
    nome_arquivo = modelo.lower().replace(" ", "") + ".jpg"
    caminho_imagem = os.path.join(PASTA_IMAGENS, nome_arquivo)

    if os.path.exists(caminho_imagem):
        cur.execute("UPDATE veiculos SET imagem=? WHERE id=?", (nome_arquivo, veiculo_id))
        print(f"✅ Atualizado: {modelo} -> {nome_arquivo}")
    else:
        print(f"❌ Imagem não encontrada para: {modelo}")

con.commit()
con.close()
print("✅ Atualização finalizada.")
