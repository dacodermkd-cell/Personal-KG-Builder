import streamlit as st
import networkx as nx
import json
from groq import Groq
from pyvis.network import Network
import streamlit.components.v1 as components

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("My Knowledge Graph")

# Memory that survives reruns
if "facts" not in st.session_state:
    st.session_state.facts = []
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []

# --- 1. User writes about themselves ---
about = st.text_area("Write about yourself (around 100 words)")

if st.button("Extract triples") and about:
    prompt = f"""Extract knowledge graph triples from this text about the user.
Return only JSON in this shape:
{{"triples": [{{"subject": "...", "predicate": "...", "object": "..."}}]}}

Rules:
- Use the user's name as the subject for facts about them.
- Predicates are short camelCase verbs, like livesIn, plays, knows.
- Entities are short names in Title Case, like Guitar, Pune.
- Put one idea per triple. Don't put opinions inside an entity name.

Text:
{about}"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    st.session_state.suggestions = result["triples"]

# --- 2. Review suggestions ---
if st.session_state.suggestions:
    st.subheader("Suggested triples")
    selected = []
    for i, t in enumerate(st.session_state.suggestions):
        text = f"{t['subject']} → {t['predicate']} → {t['object']}"
        if st.checkbox(text, value=True, key=f"sug{i}"):
            selected.append(t)

    if st.button("Add selected"):
        st.session_state.facts.extend(selected)
        st.session_state.suggestions = []
        st.rerun()

# --- 3. Add a triple by hand ---
st.subheader("Add your own")
subject = st.text_input("Subject")
predicate = st.text_input("Predicate")
obj = st.text_input("Object")

if st.button("Add") and subject and predicate and obj:
    st.session_state.facts.append({"subject": subject, "predicate": predicate, "object": obj})

# --- 4. Draw the graph (NEW: interactive with pyvis) ---
if st.session_state.facts:
    G = nx.DiGraph()
    for fact in st.session_state.facts:
        G.add_edge(fact["subject"], fact["object"], label=fact["predicate"])

    net = Network(height="600px", width="100%", directed=True)
    net.from_nx(G)
    for node in net.nodes:
      node["size"] = 10 + G.degree(node["id"]) * 3  
    html = net.generate_html()
    components.html(html, height=620)

    # --- 5. Download ---
    data = json.dumps(st.session_state.facts, indent=2)
    st.download_button("Download JSON", data, file_name="KnowledgeGraph.json")