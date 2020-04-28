from flask import Flask, render_template, request
app = Flask(__name__)
app.config["ENV"] = "development"
app.config["DEBUG"] = True


@app.route('/', methods=['GET', 'POST'])
def hello_world():
    return render_template("index.html")


if __name__ == "__main__":
    app.run()
