from flask import Flask, request, render_template
from core import graph, config, _print_event

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    print(f"User input received: {user_input}")  # Debugging log
    events = graph.stream(
        {"messages": ("user", user_input)}, config, stream_mode="values"
    )
    responses = []
    _printed = set()
    for event in events:
        response = _print_event(event, _printed)
        if response:  # Ensure that only non-null responses are added
            last_response = response
    return last_response  # Return the concatenated responses as a single string

if __name__ == '__main__':
    app.run(debug=True)