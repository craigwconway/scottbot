import json
from flask import Flask, render_template, request

from chatbot import ScottBot

application = Flask(__name__)
bot = ScottBot()


@application.route('/')
def index():
    return render_template('index.html')


@application.route('/chatbot')
def chatbot():
    user_input = request.args.get('user_input')
    res = json.dumps(bot.respond(user_input))
    print(user_input, '||', res)
    return res


@application.route('/greet')
def greet():
    return bot.greet()


if __name__ == "__main__":
    application.run(debug=True)
