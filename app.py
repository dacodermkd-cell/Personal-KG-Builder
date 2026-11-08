import streamlit as st
import networkx as nx
import json
from groq import Groq
from pyvis.network import Network
import streamlit.components.v1 as components

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ================= ONTOLOGY =================
# Each class points to its parent class ("Thing" is the root).
CLASSES = {
    "Thing": None,
    "Person": "Thing",
    "Place": "Thing",
    "City": "Place",
    "Region": "Place",
    "Country": "Place",
    "Organization": "Thing",
    "Company": "Organization",
    "University": "Organization",
    "Activity": "Thing",
    "Hobby": "Activity",
    "Sport": "Activity",
    "Skill": "Thing",
    "ProgrammingLanguage": "Skill",
    "Language": "Skill",
    "Topic": "Thing",
    "Occupation": "Thing",
    "Food": "Thing",
    "Instrument": "Thing",
    "Work": "Thing",  # books, films, music
}

# Each predicate: (domain = allowed subject class, range = allowed object class)
PREDICATES = {
    "livesIn": ("Person", "Place"),
    "grewUpIn": ("Person", "Place"),
    "bornIn": ("Person", "Place"),
    "worksAt": ("Person", "Organization"),
    "studiedAt": ("Person", "Organization"),
    "hasOccupation": ("Person", "Occupation"),
    "studied": ("Person", "Topic"),
    "knows": ("Person", "Person"),
    "hasFriend": ("Person", "Person"),
    "hasSibling": ("Person", "Person"),
    "hasParent": ("Person", "Person"),
    "hasRelative": ("Person", "Person"),
    "skilledIn": ("Person", "Skill"),
    "learning": ("Person", "Thing"),
    "plays": ("Person", "Thing"),
    "enjoys": ("Person", "Activity"),
    "likes": ("Person", "Thing"),
    "learnedFrom": ("Person", "Person"),
    "locatedIn": ("Place", "Place"),
}

TOP_COLORS = {
    "Person": "#e4572e", "Place": "#29a38f", "Organization": "#7b5ea7",
    "Activity": "#f2a541", "Skill": "#3a86ff", "Topic": "#5c7c99",
    "Occupation": "#8d6e63", "Food": "#c9406a", "Instrument": "#2e8b57",
    "Work": "#b8860b", "Thing": "#999999",
}


def is_a(cls, target):
    """True if cls is target or a subclass of it (walks up the hierarchy)."""
    while cls:
        if cls == target:
            return True
        cls = CLASSES.get(cls)
    return False


def top_class(cls):
    """The class just below Thing, e.g. City -> Place. Used for colour."""
    if cls not in CLASSES:
        return "Thing"
    while CLASSES.get(cls) not in (None, "Thing"):
        cls = CLASSES[cls]
    return cls


def check(t):
    """Return a problem message, or None if the triple fits the ontology."""
    p, s_type, o_type = t.get("predicate"), t.get("subjectType"), t.get("objectType")
    if p not in PREDICATES:
        return f"'{p}' is not an allowed predicate"
    if s_type not in CLASSES or o_type not in CLASSES:
        return "unknown type"
    domain, rng = PREDICATES[p]
    if not is_a(s_type, domain):
        return f"subject should be a {domain}, not {s_type}"
    if not is_a(o_type, rng):
        return f"object should be a {rng}, not {o_type}"
    return None


# ================= APP =================
st.title("My Knowledge Graph")

defaults = {"facts": [], "suggestions": [], "questions": [],
            "mode": None, "locked": False, "round": 0}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def extract(text):
    """Ask the LLM for triples + questions. Returns True on success, False on failure."""
    class_list = "\n".join(
        f"- {c} (a kind of {p})" if p else f"- {c}" for c, p in CLASSES.items())
    pred_list = "\n".join(
        f"- {p}: {d} -> {r}" for p, (d, r) in PREDICATES.items())
    known = "\n".join(
        f"{f['subject']} {f['predicate']} {f['object']}" for f in st.session_state.facts)

    prompt = f"""You build a personal knowledge graph about the user.

From the new text, extract triples. Then write 3 short follow-up questions
that would uncover NEW facts not already in the graph.

Allowed classes:
{class_list}

Allowed predicates (subject class -> object class):
{pred_list}

Return only JSON in this shape:
{{"triples": [{{"subject": "...", "subjectType": "...", "predicate": "...",
               "object": "...", "objectType": "..."}}],
  "questions": ["...", "...", "..."]}}

Rules:
- Use ONLY the predicates and classes listed above. If a fact doesn't fit, skip it.
- Pick the most specific class (City rather than Place).
- Use the user's name as the subject for facts about them.
- Entities are short names in Title Case, like Guitar, Pune.
- Skip plain numbers like ages and years for now.
- Don't repeat triples that are already in the graph.

Already in the graph:
{known or "(empty)"}

New text:
{text}"""

    # NEW: catch network/API failures instead of crashing
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    except Exception as e:
        st.error(f"Couldn't reach the AI service. Check your connection and try again. ({e})")
        return False

    # NEW: catch a reply that isn't valid JSON
    try:
        result = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        st.error("The AI gave a reply I couldn't read. Please try again.")
        return False

    st.session_state.suggestions = result.get("triples", [])
    st.session_state.questions = result.get("questions", [])
    st.session_state.round += 1
    return True


if not st.session_state.locked:

    # --- 1. Write about yourself ---
    if not st.session_state.facts and not st.session_state.suggestions:
        about = st.text_area("Write about yourself (around 100 words)")
        if st.button("Extract triples") and about:
            with st.spinner("Reading your text..."):
                ok = extract(about)
            if ok:
                st.rerun()

    # --- 2. Review suggestions (checked against the ontology) ---
    if st.session_state.suggestions:
        st.subheader("Suggested triples")
        selected = []
        for i, t in enumerate(st.session_state.suggestions):
            problem = check(t)
            text = (f"{t['subject']} ({t.get('subjectType')}) → {t['predicate']} → "
                    f"{t['object']} ({t.get('objectType')})")
            if problem:
                text += f"  ⚠️ {problem}"
            if st.checkbox(text, value=problem is None,
                           key=f"sug{st.session_state.round}_{i}"):
                selected.append(t)

        if st.button("Add selected"):
            st.session_state.facts.extend(selected)
            st.session_state.suggestions = []
            st.session_state.mode = "choose"
            st.rerun()

    # --- 3. Continue or lock? ---
    if st.session_state.mode == "choose":
        st.subheader("What next?")
        col1, col2 = st.columns(2)
        if col1.button("Continue with follow-up questions"):
            st.session_state.mode = "continue"
            st.rerun()
        if col2.button("Lock my KG here"):
            st.session_state.locked = True
            st.session_state.mode = None
            st.rerun()

    # --- 4. Follow-up questions ---
    if st.session_state.mode == "continue":
        st.subheader("Tell me more")
        answers = []
        for i, q in enumerate(st.session_state.questions):
            a = st.text_input(q, key=f"ans{st.session_state.round}_{i}")
            if a:
                answers.append(f"Q: {q}\nA: {a}")
        extra = st.text_area("Anything else you'd like to add? (optional)",
                             key=f"extra{st.session_state.round}")
        if extra:
            answers.append(extra)
        if st.button("Extract from my answers") and answers:
            with st.spinner("Reading your answers..."):
                ok = extract("\n\n".join(answers))
            if ok:
                st.session_state.mode = None
                st.rerun()

    # --- 5. Add by hand (dropdowns from the ontology) ---
    with st.expander("Add a triple yourself"):
        c1, c2 = st.columns(2)
        subject = c1.text_input("Subject")
        s_type = c2.selectbox("Subject type", list(CLASSES), key="stype")
        predicate = st.selectbox("Predicate", list(PREDICATES))
        c3, c4 = st.columns(2)
        obj = c3.text_input("Object")
        o_type = c4.selectbox("Object type", list(CLASSES), key="otype")
        if st.button("Add") and subject and obj:
            t = {"subject": subject, "subjectType": s_type, "predicate": predicate,
                 "object": obj, "objectType": o_type}
            problem = check(t)
            if problem:
                st.error(f"Can't add this: {problem}.")
            else:
                st.session_state.facts.append(t)
                st.rerun()

else:
    st.success("Your knowledge graph is locked.")
    if st.button("Unlock to keep editing"):
        st.session_state.locked = False
        st.session_state.mode = "choose"
        st.rerun()


# ================= GRAPH =================
if st.session_state.facts:
    G = nx.DiGraph()
    types = {}
    for f in st.session_state.facts:
        G.add_edge(f["subject"], f["object"], label=f["predicate"])
        types[f["subject"]] = f.get("subjectType", "Thing")
        types[f["object"]] = f.get("objectType", "Thing")

    net = Network(height="600px", width="100%", directed=True)
    net.from_nx(G)
    for node in net.nodes:
        cls = types.get(node["id"], "Thing")
        node["size"] = 10 + G.degree(node["id"]) * 3
        node["color"] = TOP_COLORS.get(top_class(cls), "#999999")
        node["title"] = cls  # shown on hover

    components.html(net.generate_html(), height=620)

    # Legend: only the types actually in the graph
    used = sorted({top_class(c) for c in types.values()})
    legend = " &nbsp; ".join(
        f"<span style='color:{TOP_COLORS.get(c, '#999')}'>●</span> {c}" for c in used)
    st.markdown(legend, unsafe_allow_html=True)

    data = json.dumps(st.session_state.facts, indent=2)
    st.download_button("Download JSON", data, file_name="KnowledgeGraph.json")