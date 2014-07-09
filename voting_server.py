from flask import Flask, jsonify, request, redirect, render_template

# object instance for frontend
app = Flask(__name__)

# object instance for for backend
import voting_backend
backend = voting_backend.backend()

# decorators are switchboard functions which take a request
# serve the correct page, or send a command to the backend
@app.route('/')
def serve_landing():
    # check if we're in a voting window. this changes
    # how the template is rendered and enables/disables
    # the voting redirect
    voting_open = backend.w.voting_open()
    return render_template("landing.html",voting=voting_open)

# normal commands: voting, serving pages, etc
@app.route('/<cmd>',methods=['POST', 'GET'])
def dispatch_cmd(cmd):

    # now send the command
    try:
        returned = backend.cmds[cmd](request.json)
    except KeyError:
        returned = {}

    # now return the result from the backend. sometimes, this is a
    # template. other times we just return a json
    if 'redirect' in returned.keys():
        return redirect(returned['redirect'])

    if 'template' in returned.keys():
        return render_template(returned['template'],**returned['kwargs'])

    else:
        return jsonify(**returned)

if __name__ == "__main__":
    app.run()
