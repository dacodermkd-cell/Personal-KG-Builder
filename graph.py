
import networkx as nx
import matplotlib.pyplot as plt
facts = [
    {"subject": "Mitul", "predicate": "isA", "object": "Person"},
    {"subject": "Mitul", "predicate": "studies", "object": "AI"},
    {"subject": "Mitul", "predicate": "eats", "object": "Rajma Chawal"},
    {"subject": "Mitul", "predicate": "plays", "object": "Guitar"},
    {"subject": "Mitul", "predicate": "likes", "object": "Claude"},
    {"subject": "Rajma Chawal", "predicate": "isA", "object": "Food"},
    {"subject": "Guitar", "predicate": "isA", "object": "MusicalInstrument"},
    {"subject": "Claude", "predicate": "isA", "object": "LLM"},
]

def node_and_edges_extractor(facts):
  nodes = set()
  edges = []
  for fact in facts:
    nodes.add(fact["subject"])
    nodes.add(fact["object"])
    edges.append({"from": fact["subject"], "to": fact["object"], "label": fact["predicate"]})

  return nodes,edges

nodes, edges = node_and_edges_extractor(facts)
print(len(nodes), "nodes")
print(len(edges), "edges")

G = nx.DiGraph()

for node in nodes:
   G.add_node(node)

for edge in edges:
  G.add_edge(edge["from"], edge["to"], label=edge["label"])

pos = nx.spring_layout(G)
labels = nx.get_edge_attributes(G, "label")

nx.draw(G, pos, with_labels=True)
nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
plt.show()
