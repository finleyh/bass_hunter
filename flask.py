from flask import Flask

app = Flask(__name__)


#define a connection string to your database
#db conn string here    #ignoreline


@app.route('/')
def index():
	return "Testing: Hello, World!"


if__name__=='__main__':
	app.run(debug=True)
