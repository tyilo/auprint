from auprint import AUPrint, AUAuthenticationError
from flask import Flask, Response, session, request, abort

app = Flask(__name__)
app.secret_key = 'dooof'
app.config['UPLOAD_FOLDER'] = '/tmp'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024**2

@app.route('/list')
def list_printers():
	return Response()

@app.route('/login', methods=['POST'])
def login():
	session.pop('auid', None)
	session.pop('password', None)

	auid = request.form.get('auid', '')
	password = request.form.get('password', '')
	try:
		AUPrint(auid, password)
	except AUAuthenticationError:
		abort(401)

	session['auid'] = auid
	session['password'] = password

	return Response()

if __name__ == '__main__':
	app.run('0.0.0.0')


