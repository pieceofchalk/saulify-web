from flask import request, render_template, redirect, url_for, Markup, \
    abort, jsonify, g, flash
from newspaper import Article
from flask.ext.login import login_user, logout_user, current_user, \
    login_required
from saulify import app, login_manager, db
from models import User
from xml.etree import ElementTree
import html2text
import markdown2
from functools import wraps
from api_key_gen import api_key_gen


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.before_request
def before_request():
    g.user = current_user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username']
    password = request.form['password']
    registered_user = User.query.filter_by(username=username,
                                           password=password).first()
    if registered_user is None:
        flash('Username or Password is invalid', 'error')
        return redirect(url_for('login'))
    login_user(registered_user)
    flash('Logged in successfully')
    return redirect(url_for('user'))


@app.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    user = g.user
    return render_template('user.html',
                           user=user)


@app.route('/createkey')
@login_required
def createkey():
    user = g.user
    user.api_key = api_key_gen()
    db.session.commit()
    return jsonify({"result": "succes"})


@app.route('/revokekey')
@login_required
def revokekey():
    user = g.user
    user.api_key = None
    db.session.commit()
    return jsonify({"result": "succes"})


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


# The actual decorator function
def require_appkey(function):
    @wraps(function)
    # the new, post-decoration function. Note *args and **kwargs here.
    def decorated_function(*args, **kwargs):
        if request.args.get('key') and User.query.filter_by(api_key=request.args.get('key')).first():
                return function(*args, **kwargs)
        else:
            abort(401)
    return decorated_function


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/clean')
def show_article():
    # TODO: Need to extract this to a module
    url_to_clean = request.args.get('u')
    if not url_to_clean:
        return redirect(url_for('index'))

    article = Article(url_to_clean)
    article.download()
    article.parse()
    html_string = ElementTree.tostring(article.clean_top_node)
    markdown = html2text.HTML2Text().handle(html_string)
    # TODO: Need to save the markdown, but just show it for now
    # Note: Markup marks it as html safe since we're rendering it from Markdown
    article_html = Markup(markdown2.markdown(markdown))
    a = {'html': article_html,
         'authors': str(', '.join(article.authors)),
         'title': article.title}
    return render_template('article/show.html',
                           article=a,
                           original=url_to_clean)


@app.route('/api')
@require_appkey
def api():
    # TODO: the same todo show_article() need to extract to a separate module
    url_to_clean = request.args.get('u')
    if not url_to_clean:
        return redirect(url_for('index'))

    article = Article(url_to_clean)
    article.download()
    article.parse()
    html_string = ElementTree.tostring(article.clean_top_node)
    markdown = html2text.HTML2Text().handle(html_string)
    # TODO: Need to save the markdown, but just show it for now
    # Note: Markup marks it as html safe since we're rendering it from Markdown
    article_html = Markup(markdown2.markdown(markdown))
    return jsonify({'title': article.title,
                    'authors': str(', '.join(article.authors)),
                    'html': article_html,
                    'plaintext': markdown.replace('\n', ' '),
                    'markdown': markdown})


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404