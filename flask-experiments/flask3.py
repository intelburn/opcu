from flask import Flask, render_template, request
app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def dropdown():
    colours = ['Red', 'Blue', 'Black', 'Orange']
    if request.method == 'POST' :
        colour = request.form
        print(colour)
    return render_template('flask3.html', colours=colours)

if __name__ == "__main__":
    app.run(ssl_context='adhoc')
