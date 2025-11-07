import webview
import threading
from app import app  # importa teu Flask normalmente


def start_flask():
    app.run(debug=False, port=5005)  # Porta que o Flask vai rodar


if __name__ == '__main__':
    threading.Thread(target=start_flask).start()

    # Cria a janela do app
    webview.create_window(
        title='Luxury Wheels App',
        url='http://127.0.0.1:5005',
        width=1280,
        height=720,
        resizable=True,
        fullscreen=False,
        confirm_close=True,
        background_color='#FFFFFF'
    )

    webview.start()
