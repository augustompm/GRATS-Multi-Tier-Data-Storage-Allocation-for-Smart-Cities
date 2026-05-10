AGENTS = {
    'Toronto-OnPrem-SSD-Hot':   {'price': 0.10,    'retrieval': 0.00,   'transfer_override': 0.00, 'media': 'SSD',  'latency_s': 0.005,    'provider': 'Toronto-OnPrem', 'region_grid': 'IESO_ON'},
    'Toronto-OnPrem-HDD-Warm':  {'price': 0.04,    'retrieval': 0.00,   'transfer_override': 0.00, 'media': 'HDD',  'latency_s': 0.020,    'provider': 'Toronto-OnPrem', 'region_grid': 'IESO_ON'},
    'Toronto-OnPrem-Tape-Cold': {'price': 0.005,   'retrieval': 0.00,   'transfer_override': 0.00, 'media': 'Tape', 'latency_s': 600.0,    'provider': 'Toronto-OnPrem', 'region_grid': 'IESO_ON'},

    'AWS-Canada-Standard':   {'price': 0.025,   'retrieval': 0.00,   'media': 'SSD', 'latency_s': 0.05,     'provider': 'AWS',   'region_grid': 'IESO_ON'},
    'AWS-Canada-IA':         {'price': 0.0138,  'retrieval': 0.01,   'media': 'SSD', 'latency_s': 0.05,     'provider': 'AWS',   'region_grid': 'IESO_ON'},
    'AWS-Canada-GlacierIR':  {'price': 0.005,   'retrieval': 0.0033, 'media': 'HDD', 'latency_s': 0.001,    'provider': 'AWS',   'region_grid': 'IESO_ON'},
    'AWS-Canada-DeepArch':   {'price': 0.00099, 'retrieval': 0.02,   'media': 'HDD', 'latency_s': 12*3600,  'provider': 'AWS',   'region_grid': 'IESO_ON'},

    'Azure-Canada-Hot':      {'price': 0.0184,  'retrieval': 0.00,   'media': 'SSD', 'latency_s': 0.05,     'provider': 'Azure', 'region_grid': 'IESO_ON'},
    'Azure-Canada-Cool':     {'price': 0.01,    'retrieval': 0.005,  'media': 'SSD', 'latency_s': 0.05,     'provider': 'Azure', 'region_grid': 'IESO_ON'},
    'Azure-Canada-Cold':     {'price': 0.0036,  'retrieval': 0.01,   'media': 'SSD', 'latency_s': 0.05,     'provider': 'Azure', 'region_grid': 'IESO_ON'},
    'Azure-Canada-Archive':  {'price': 0.00099, 'retrieval': 0.02,   'media': 'HDD', 'latency_s': 12*3600,  'provider': 'Azure', 'region_grid': 'IESO_ON'},

    'GCP-Canada-Standard':   {'price': 0.020,   'retrieval': 0.00,   'media': 'SSD', 'latency_s': 0.05,     'provider': 'GCP',   'region_grid': 'IESO_ON'},
    'GCP-Canada-Nearline':   {'price': 0.013,   'retrieval': 0.001,  'media': 'SSD', 'latency_s': 0.05,     'provider': 'GCP',   'region_grid': 'IESO_ON'},
    'GCP-Canada-Coldline':   {'price': 0.007,   'retrieval': 0.005,  'media': 'SSD', 'latency_s': 0.05,     'provider': 'GCP',   'region_grid': 'IESO_ON'},
    'GCP-Canada-Archive':    {'price': 0.0012,  'retrieval': 0.05,   'media': 'HDD', 'latency_s': 0.05,     'provider': 'GCP',   'region_grid': 'IESO_ON'},

    'AWS-US-DeepArch':       {'price': 0.00099, 'retrieval': 0.02,   'media': 'HDD', 'latency_s': 12*3600,  'provider': 'AWS',   'region_grid': 'RFCW'},
}

TRANSFER_OUT = {'AWS': 0.09, 'Azure': 0.087, 'GCP': 0.12, 'Toronto-OnPrem': 0.00}

PUE = {'AWS': 1.15, 'Azure': 1.16, 'GCP': 1.10, 'Toronto-OnPrem': 1.58}

GRID_CO2 = {'RFCW': 0.4155, 'MROW': 0.4203, 'IESO_ON': 0.071}

KWH_PER_GB_MONTH = {'SSD': 0.000156, 'HDD': 0.000216, 'Tape': 0.0001}

EMBODIED_KG_PER_GB = {'SSD': 0.16, 'HDD': 0.02, 'Tape': 0.0014}

LIFETIME_MONTHS = {'SSD': 60, 'HDD': 60, 'Tape': 360}

EMBODIED_PER_GB_MONTH = {m: EMBODIED_KG_PER_GB[m] / LIFETIME_MONTHS[m] for m in ['SSD', 'HDD', 'Tape']}


def co2_op_per_gb_month(agent_key):
    a = AGENTS[agent_key]
    return PUE[a['provider']] * KWH_PER_GB_MONTH[a['media']] * GRID_CO2[a['region_grid']]


def co2_emb_per_gb_month(agent_key):
    return EMBODIED_PER_GB_MONTH[AGENTS[agent_key]['media']]


SUB_TIERS = ['Live', 'Recent', 'Archive']
ALPHA = {'Live': 0.05, 'Recent': 0.18, 'Archive': 0.77}
BETA = {'Live': 3.0, 'Recent': 0.10, 'Archive': 0.001}
C4_MAX_LATENCY_S = {'Live': 60.0, 'Recent': 3600.0, 'Archive': float('inf')}

TPS_OPERATIONAL_VOLUME_PB = 5.0
TPS_PROGRAM_NAME = 'Toronto Police Service'
