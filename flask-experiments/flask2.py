from flask import Flask, render_template
app = Flask(__name__)
@app.route('/')
def yo(name=None):
    return render_template('flask2.html')

if __name__ == "__main__":
    app.run(ssl_context='adhoc')

