import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import plotly.graph_objs as go
import plotly.express as px
import locale
import networkx as nx
import time
import utils

st.set_page_config(
    page_title="Data - Gitcoin Networks",
    page_icon="favicon.png",
    layout="wide",
)

st.title('🕸 Gitcoin Grants Networks')
st.write('This network graph helps visualize the connections between donors and projects in the Gitcoin Grants Beta Rounds. The graph is interactive, so you can hover over a node to see who it is, zoom in and out and drag the graph around to explore it.')
st.write('One use for this graph is to identify interesting outliers such as grants who have their own distinct donor base.')

program_data = pd.read_csv("all_rounds.csv")
program_option = st.selectbox( 'Select Program', program_data['program'].unique())
st.title(program_option)

if "program_option" in st.session_state and st.session_state.program_option != program_option:
    st.session_state.data_loaded = False
st.session_state.program_option = program_option


if "data_loaded" in st.session_state and st.session_state.data_loaded:
    dfv = st.session_state.dfv
    dfp = st.session_state.dfp
    round_data = st.session_state.round_data
else:
    data_load_state = st.text('Loading data...')
    dfv, dfp, round_data = utils.load_round_data(program_option, "all_rounds.csv")
    data_load_state.text("")
    

# selectbox to select the round
option = st.selectbox(
    'Select Round',
    round_data['options'].unique())
option = option.split(' - ')[0]
dfv = dfv[dfv['round_name'] == option]
dfp = dfp[dfp['round_name'] == option]
round_data = round_data[round_data['round_name'] == option]


# sum amountUSD group by voter and grantAddress
dfv = dfv.groupby(['voter_id', 'grantAddress', 'title']).agg({'amountUSD': 'sum', 'block_timestamp': 'min'}).reset_index()


# Minimum donation amount to include, start at 10
min_donation = st.slider('Minimum donation amount', value=10, max_value=50, min_value=1, step=1)
# Minimum passport score to include, start at 20
#min_passport_score = st.slider('Minimum Passport Score', value=0, max_value=100, min_value=0, step=1)

# Filter the dataframe to include only rows with donation amounts above the threshold
dfv = dfv[dfv['amountUSD'] > min_donation]
# Filter the dataframe to include only rows with donation amounts above the threshold
#df = dfv[dfv['rawScore'] > min_passport_score]

count_connections = dfv.shape[0]
count_voters = dfv['voter_id'].nunique()
count_grants = dfv['title'].nunique()

# Sort the DataFrame by timestamp
dfv = dfv.sort_values(by='block_timestamp')

# Check if the number of connections exceeds 10,000
if dfv.shape[0] > 10000:
    # Calculate the fraction to sample
    frac_to_sample = 10000 / dfv.shape[0]
    dfv = dfv.sample(frac=frac_to_sample, random_state=42)

count_connections = dfv.shape[0]
count_voters = dfv['voter_id'].nunique()
count_grants = dfv['title'].nunique()


color_toggle = st.checkbox('Toggle colors', value=True)

if color_toggle:
    grants_color = '#00433B'
    grantee_color_string = 'moss'
    voters_color = '#C4F092'
    voter_color_string = 'lightgreen'
    line_color = '#6E9A82'
else:
    grants_color = '#FF7043'
    grantee_color_string = 'orange'
    voters_color = '#B3DE9F'
    voter_color_string = 'green'
    line_color = '#6E9A82'

note_string = '**- Note: ' + str(count_grants) + ' Grantees are in ' + grantee_color_string + ' and ' + str(count_voters) + ' donors/voters are in ' + voter_color_string + ' forming ' + str(count_connections) + ' connections. **'
st.markdown(note_string)
st.markdown('**- Tip: Go fullscreen with the arrows in the top-right for a better view.**')
# Initialize a new Graph
B = nx.Graph()

# Create nodes with the bipartite attribute
B.add_nodes_from(dfv['voter_id'].unique(), bipartite=0, color=voters_color) 
B.add_nodes_from(dfv['title'].unique(), bipartite=1, color=grants_color) 



# Add edges with amountUSD as an attribute
for _, row in dfv.iterrows():
    B.add_edge(row['voter_id'], row['title'], amountUSD=row['amountUSD'])



# Compute the layout
current_time = time.time()
pos = nx.spring_layout(B, dim=3, k = .09, iterations=50)
new_time = time.time()


    
# Extract node information
node_x = [coord[0] for coord in pos.values()]
node_y = [coord[1] for coord in pos.values()]
node_z = [coord[2] for coord in pos.values()] # added z-coordinates for 3D
node_names = list(pos.keys())
# Compute the degrees of the nodes 
degrees = np.array([B.degree(node_name) for node_name in node_names])
# Apply the natural logarithm to the degrees 
log_degrees = np.log(degrees + 1)
# Min-Max scaling manually
#min_size = 10  # minimum size
#max_size = 50  # maximum size
#node_sizes = ((log_degrees - np.min(log_degrees)) / (np.max(log_degrees) - np.min(log_degrees))) * (max_size - min_size) + min_size
node_sizes = log_degrees * 10

# Extract edge information
edge_x = []
edge_y = []
edge_z = []  
edge_weights = []

for edge in B.edges(data=True):
    x0, y0, z0 = pos[edge[0]]
    x1, y1, z1 = pos[edge[1]]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])
    edge_z.extend([z0, z1, None])  
    edge_weights.append(edge[2]['amountUSD'])

# Create the edge traces
edge_trace = go.Scatter3d(
    x=edge_x, y=edge_y, z=edge_z, 
    line=dict(width=1, color=line_color),
    hoverinfo='none',
    mode='lines',
    marker=dict(opacity=0.5))


# Create the node traces
node_trace = go.Scatter3d(
    x=node_x, y=node_y, z=node_z,
    mode='markers',
    hoverinfo='text',
    marker=dict(
        color=[data['color'] for _, data in B.nodes(data=True)],  # color is now assigned based on node data
        size=node_sizes,
        opacity=1,
        sizemode='diameter'
    ))


node_adjacencies = []
for node, adjacencies in enumerate(B.adjacency()):
    node_adjacencies.append(len(adjacencies[1]))
node_trace.marker.color = [data[1]['color'] for data in B.nodes(data=True)]


# Prepare text information for hovering
node_trace.text = [f'{name}: {adj} connections' for name, adj in zip(node_names, node_adjacencies)]

# Create the figure
fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    title='3D Network graph of voters and grants',
                    titlefont=dict(size=20),
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    annotations=[ dict(
                        showarrow=False,
                        text="This graph shows the connections between voters and grants based on donation data.",
                        xref="paper",
                        yref="paper",
                        x=0.005,
                        y=-0.002 )],
                    scene = dict(
                        xaxis_title='X Axis',
                        yaxis_title='Y Axis',
                        zaxis_title='Z Axis')))
                        
st.plotly_chart(fig, use_container_width=True)
st.caption('Time to compute layout: ' + str(round(new_time - current_time, 2)) + ' seconds')