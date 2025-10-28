from flask import Flask, request
import google.generativeai as genai
from config import GEMINI_API_KEY

app = Flask(__name__)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

@app.route("/")
def index():
    return """
    <h2>ИИ-бухгалтер</h2>
    <form method="post" action="/chat">
      <label>Введите запрос:</label><br>
      <input type="text" name="message" style="width:300px">
      <input type="submit" value="Отправить">
    </form>
    """

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.form.get("message", "")
    response = model.generate_content(f"Ты бухгалтер. Ответь на запрос: {user_input}")
    return f"<p><b>Ответ:</b> {response.text}</p><a href='/'>Назад</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
