import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_cytoscape as cyto

# 路徑請改成你的檔案路徑
file_path = r'D:\Programmed Files\Python\GradProject\data\result.csv'
df = pd.read_csv(file_path)

# 轉換時間格式
df['TimeStamp'] = pd.to_datetime(df['TimeStamp'])
# 確保 layer 是整數型態，沒有的話自己補 0
if 'layer' not in df.columns:
    df['layer'] = 0
else:
    df['layer'] = df['layer'].astype(int)

# 篩選最大資料量，避免前端爆掉
MAX_TRANSACTIONS = 1000

def create_elements(dataframe):
    # 篩選前MAX_TRANSACTIONS筆資料避免過大
    dataframe = dataframe.head(MAX_TRANSACTIONS)

    nodes = {}
    edges = []

    for _, tx in dataframe.iterrows():
        # 累積節點資料
        for addr in [tx['From'], tx['To']]:
            if addr not in nodes:
                nodes[addr] = {
                    'id': addr,
                    'label': addr,
                    'total_value': 0,
                    'degree': 0,
                    'layer': int(tx['layer'])
                }

        # 累計總交易額與度數 (出入交易筆數)
        nodes[tx['From']]['total_value'] += tx['Value']
        nodes[tx['To']]['total_value'] += tx['Value']

        nodes[tx['From']]['degree'] += 1
        nodes[tx['To']]['degree'] += 1

        # 建立邊
        edges.append({
            'data': {
                'id': f"{tx['From']}-{tx['To']}",
                'source': tx['From'],
                'target': tx['To'],
                'weight': tx['Value'],
                'layer': int(tx['layer'])
            }
        })

    node_elements = [{
        'data': {
            'id': node['id'],
            'label': node['label'],
            'total_value': node['total_value'],
            'degree': node['degree'],
            'layer': node['layer']
        }
    } for node in nodes.values()]

    return node_elements + edges

elements = create_elements(df)

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Interactive Transaction Network", style={'textAlign': 'center'}),

    # 網路圖
    cyto.Cytoscape(
        id='network-graph',
        elements=elements,
        layout={'name': 'cose'},
        style={'width': '100%', 'height': '600px'},
        stylesheet=[
            {
                'selector': 'node',
                'style': {
                    'width': 'mapData(degree, 0, 20, 20, 50)',
                    'height': 'mapData(degree, 0, 20, 20, 50)',
                    'background-color': 'mapData(total_value, 0, 1e18, blue, red)',
                    'label': 'data(label)',
                    'color': '#222',
                    'font-size': '8px',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'text-opacity': 0
                }
            },
            {
                'selector': 'node:selected',
                'style': {
                    'text-opacity': 1,
                    'background-color': 'green'
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'curve-style': 'bezier',
                    'target-arrow-shape': 'triangle',
                    'line-color': '#888',
                    'width': 'mapData(weight, 0, 1e18, 1, 5)'
                }
            },
            {
                'selector': 'edge:selected',
                'style': {
                    'line-color': 'yellow',
                    'width': 5
                }
            }
        ]
    ),

    html.Div([
        html.Label('Select time range:'),
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date=df['TimeStamp'].min(),
            end_date=df['TimeStamp'].max(),
            display_format='YYYY-MM-DD'
        ),

        html.Br(),
        html.Label('Select layer range:'),
        dcc.RangeSlider(
            id='layer-range-slider',
            min=df['layer'].min(),
            max=df['layer'].max(),
            value=[df['layer'].min(), df['layer'].max()],
            marks={i: str(i) for i in range(df['layer'].min(), df['layer'].max() + 1)},
            step=1
        ),

        html.Br(),
        html.Button('Show Top 10 Transactions', id='show-top-10-btn', n_clicks=0),
        html.Button('Highlight High Frequency Nodes', id='highlight-high-freq-btn', n_clicks=0),
        html.Button('Reset Graph', id='reset-graph-btn', n_clicks=0),

        html.Div(id='top-10-list', style={'padding': '10px'}),
        html.Div(id='node-info', style={'padding': '10px'}),
        html.Div(id='edge-info', style={'padding': '10px'}),
    ], style={'width': '80%', 'margin': 'auto'})
])


@app.callback(
    Output('network-graph', 'elements'),
    [
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date'),
        Input('layer-range-slider', 'value'),
        Input('reset-graph-btn', 'n_clicks')
    ]
)
def update_graph(start_date, end_date, layer_range, reset_clicks):
    filtered_df = df[
        (df['TimeStamp'] >= pd.to_datetime(start_date)) &
        (df['TimeStamp'] <= pd.to_datetime(end_date)) &
        (df['layer'] >= layer_range[0]) &
        (df['layer'] <= layer_range[1])
    ]

    return create_elements(filtered_df)


@app.callback(
    Output('network-graph', 'stylesheet'),
    [
        Input('network-graph', 'tapNodeData'),
        Input('network-graph', 'tapEdgeData'),
        Input('show-top-10-btn', 'n_clicks'),
        Input('highlight-high-freq-btn', 'n_clicks'),
        Input('reset-graph-btn', 'n_clicks'),
    ],
    [State('network-graph', 'stylesheet')]
)
def update_stylesheet(tapped_node, tapped_edge, top10_clicks, highfreq_clicks, reset_clicks, current_stylesheet):
    base_style = [
        {
            'selector': 'node',
            'style': {
                'width': 'mapData(degree, 0, 20, 20, 50)',
                'height': 'mapData(degree, 0, 20, 20, 50)',
                'background-color': 'mapData(total_value, 0, 1e18, blue, red)',
                'label': 'data(label)',
                'color': '#222',
                'font-size': '8px',
                'text-valign': 'center',
                'text-halign': 'center',
                'text-opacity': 0
            }
        },
        {'selector': 'node:selected', 'style': {'text-opacity': 1, 'background-color': 'green'}},
        {'selector': 'edge', 'style': {'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'line-color': '#888'}},
        {'selector': 'edge:selected', 'style': {'line-color': 'yellow', 'width': 5}}
    ]

    ctx = dash.callback_context

    if not ctx.triggered:
        return base_style

    triggered_id = ctx.triggered[0]['prop_id']

    if 'reset-graph-btn' in triggered_id:
        return base_style

    if 'show-top-10-btn' in triggered_id:
        top_10_df = df.nlargest(10, 'Value')
        node_styles = []
        edge_styles = []
        for _, row in top_10_df.iterrows():
            node_styles.append({
                'selector': f'node[id = "{row["From"]}"]',
                'style': {'background-color': 'yellow', 'opacity': 1, 'font-weight': 'bold', 'text-opacity': 1}
            })
            node_styles.append({
                'selector': f'node[id = "{row["To"]}"]',
                'style': {'background-color': 'yellow', 'opacity': 1, 'font-weight': 'bold', 'text-opacity': 1}
            })
            edge_styles.append({
                'selector': f'edge[id = "{row["From"]}-{row["To"]}"]',
                'style': {'line-color': 'yellow', 'opacity': 1, 'width': 4}
            })
        return base_style + node_styles + edge_styles

    if 'highlight-high-freq-btn' in triggered_id:
        # 計算一天內交易數量大於5的節點
        tx_counts_from = df.groupby(['From', pd.Grouper(key='TimeStamp', freq='D')]).size().reset_index(name='count')
        tx_counts_to = df.groupby(['To', pd.Grouper(key='TimeStamp', freq='D')]).size().reset_index(name='count')

        high_freq_nodes = set(tx_counts_from[tx_counts_from['count'] > 5]['From']).union(
            set(tx_counts_to[tx_counts_to['count'] > 5]['To'])
        )

        node_styles = [{
            'selector': f'node[id = "{node}"]',
            'style': {'background-color': 'orange', 'opacity': 1, 'text-opacity': 1}
        } for node in high_freq_nodes]

        return base_style + node_styles

    if tapped_node:
        styles = [
            {'selector': 'node', 'style': {'opacity': 0.3, 'text-opacity': 0}},
            {'selector': 'edge', 'style': {'opacity': 0.1}},
            {'selector': f'node[id = "{tapped_node["id"]}"]', 'style': {'opacity': 1, 'text-opacity': 1, 'background-color': 'green'}}
        ]

        # 突顯相連邊與鄰接節點
        for style in current_stylesheet:
            if 'selector' in style and style['selector'].startswith('edge[id ='):
                edge_id = style['selector'][8:-2]  # 取出id字串
                source, target = edge_id.split('-')
                if source == tapped_node['id'] or target == tapped_node['id']:
                    styles.append({'selector': f'edge[id = "{edge_id}"]', 'style': {'opacity': 1, 'line-color': 'yellow', 'width': 4}})
                    other = target if source == tapped_node['id'] else source
                    styles.append({'selector': f'node[id = "{other}"]', 'style': {'opacity': 1, 'background-color': 'yellow', 'text-opacity': 1}})
        return base_style + styles

    if tapped_edge:
        styles = [
            {'selector': 'node', 'style': {'opacity': 0.3, 'text-opacity': 0}},
            {'selector': 'edge', 'style': {'opacity': 0.1}},
            {'selector': f'edge[id = "{tapped_edge["id"]}"]', 'style': {'opacity': 1, 'line-color': 'yellow', 'width': 5}},
            {'selector': f'node[id = "{tapped_edge["source"]}"]', 'style': {'opacity': 1, 'background-color': 'yellow', 'text-opacity': 1}},
            {'selector': f'node[id = "{tapped_edge["target"]}"]', 'style': {'opacity': 1, 'background-color': 'yellow', 'text-opacity': 1}},
        ]
        return base_style + styles
        return base_style


@app.callback(
    Output('node-info', 'children'),
    [Input('network-graph', 'tapNodeData')]
)
def display_node_info(node):
    if not node:
        return "Click on a node to see details"
    return f"Node: {node['label']}, Total Value: {node['total_value']:.2e}, Degree: {node['degree']}"


@app.callback(
    Output('edge-info', 'children'),
    [Input('network-graph', 'tapEdgeData')]
)
def display_edge_info(edge):
    if not edge:
        return "Click on an edge to see details"

    source_degree = df[(df['From'] == edge['source']) | (df['To'] == edge['source'])].shape[0]
    target_degree = df[(df['From'] == edge['target']) | (df['To'] == edge['target'])].shape[0]
    edge_count = df[
        ((df['From'] == edge['source']) & (df['To'] == edge['target'])) |
        ((df['From'] == edge['target']) & (df['To'] == edge['source']))
    ].shape[0]

    return f"Edge: {edge['source']} -> {edge['target']}, Value: {edge['weight']:.2e}, Edge Count: {edge_count}, Source Degree: {source_degree}, Target Degree: {target_degree}"


if __name__ == '__main__':
    app.run(debug=True)