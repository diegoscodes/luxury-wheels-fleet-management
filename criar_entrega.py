import os
import shutil

# Criação da estrutura
os.makedirs("entrega_final/static/imagens", exist_ok=True)
os.makedirs("entrega_final/templates", exist_ok=True)
os.makedirs("entrega_final/prints", exist_ok=True)

# Arquivos principais
shutil.copy("app.py", "entrega_final/app.py")
shutil.copy("luxurywheels.db", "entrega_final/luxurywheels.db")
shutil.copytree("static/imagens", "entrega_final/static/imagens", dirs_exist_ok=True)
shutil.copytree("templates", "entrega_final/templates", dirs_exist_ok=True)

print("✅ Estrutura inicial da entrega criada com sucesso.")
