from .parameters import AGENTS, TRANSFER_OUT, co2_op_per_gb_month, co2_emb_per_gb_month


def q1_cost(agent_key, role):
    a = AGENTS[agent_key]
    transfer = a.get('transfer_override', TRANSFER_OUT[a['provider']])
    size = role.get('size_gb', 0) or 0
    reads = role.get('reads_gb_month', 0) or 0
    return a['price'] * size + (a['retrieval'] + transfer) * reads


def q2_latency(agent_key, role):
    reads = role.get('reads_gb_month', 0) or 0
    return reads * AGENTS[agent_key]['latency_s']


def q3_co2(agent_key, role):
    size = role.get('size_gb', 0) or 0
    return size * (co2_op_per_gb_month(agent_key) + co2_emb_per_gb_month(agent_key))


OBJ_FUNCS = {'Q1': q1_cost, 'Q2': q2_latency, 'Q3': q3_co2}
