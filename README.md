# PersonaMate
Open sourced personnal assistant based on LLM helping you with tasks and contact informations

# Current features

- Base LLM model interaction
- Markdown answers formatting (no syntax highlighting yet)
- Personal information storage system
- Web based realtime information with the use of [Tavily](https://tavily.com/)
- Graph based relations to manage information between people and subjects or between subjects themselves

# Requirements

* python 3.11+ (currently only tested on python 3.11.9), I recommend using conda environments
* Tavily api key, avaible for free with 1000 credits/mo at [Tavily.com](https://tavily.com/)
* OpenAI api key and credits (other models might work, as well as local models, llama3.1:70B might work if you want a local running LLM model)

# Installing

1. Install python modules 

```bash
pip install -r requirements.txt
```

2. Simply put your api key in a .env file on the root of the project.

```env
OPENAI_API_KEY=...
TAVILY_API_KEY=...
```

3. Run the bash file to write the empty personal_data.json file.

4. Then run `python src/python/app.py`

5. Your chatbot should be available at [127.0.0.1:5000](https://127.0.0.1:5000/)
