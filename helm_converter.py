import os
import json
import copy
from datetime import datetime, timezone
from tqdm import tqdm, trange
import jsonlines

OUT_DIR = 'test_out'
SCHEMA_VERSION = 'v0.1.0'


def generate_time():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def generate_item_id(dataset_name, time, idx):
    ds = dataset_name.replace('_', '-').replace(' ', '-').lower()
    return f'{ds}_{time}_{idx}'

def generate_response_id(item_id, model_name, idx):
    md = model_name.replace('_', '-').replace(' ', '-').lower()
    return f'{item_id}_{md}_{idx}'
    
def helm_to_benchmarks(root):
    '''
    Convert results from multiple HELM runs into the OpenEval schema (the benchmark table).
    Args:
        root: root directory of the result folders.
    '''
    out_path = os.path.join(OUT_DIR, 'helm_benchs.jsonl')
    if os.path.exists(out_path):
        with jsonlines.open(out_path, 'r') as f:
            collected_benchs = [b['benchmark_name'] for b in f]
    else:
        collected_benchs = []
    of = jsonlines.open(out_path, 'a')

    for folder in tqdm(os.listdir(root), desc=root):
        # read data
        res_path = os.path.join(root, folder)
        with open(os.path.join(res_path, 'scenario.json'), 'r') as f:
            scen = json.load(f)

        if scen['name'] in collected_benchs or 'http' not in scen['definition_path']:
            continue
        collected_benchs.append(scen['name'])
        # assemble benchmark
        source = {'benchmark_name': '', 'benchmark_version': '', 'benchmark_url': '', 'benchmark_tags': []}
        source['benchmark_name'] = scen['name']
        source['benchmark_tags'] += scen['tags']
        source['benchmark_version'] = ''
        source['benchmark_url'] = scen['definition_path']
        of.write(source)
        
    of.close()
    print(f'Converted {len(collected_benchs)} benchmarks from {root} to {out_path}.')


def helm_to_items(root, folder, name='Anonymous', email='', affiliation=''):
    '''
    Convert results from a HELM run into the OpenEval schema (the item table).
    Args:
        root: root directory of the result folders.
        folder: name of the HELM result folder, usually a HELM run entry.
        name, email, and affiliation: contributor's subfields in the OpenEval schema.
    Returns:
        mapping: a dict mapping from HELM item ids to OpenEval item ids
    '''
    # read data
    res_path = os.path.join(root, folder)
    with open(os.path.join(res_path, 'scenario.json'), 'r') as f:
        scen = json.load(f)
    with open(os.path.join(res_path, 'scenario_state.json'), 'r') as f:
        data = json.load(f)
        adapter = data['adapter_spec']
        reqs = data['request_states']

    # item metadata (shared)
    ingestion_time = generate_time()
    contributor = {'name': name, 'email': email, 'affiliation': affiliation}
    source = scen['name']

    out_path = os.path.join(OUT_DIR, f'helm_items_{folder}.jsonl')
    of = jsonlines.open(out_path, 'w')
    mapping = {}

    # unique fields, 1 req => 1 response/trial
    for idx in trange(len(reqs), desc=folder):
        req = reqs[idx]

        ## item id
        if req['instance']['id'] in mapping or 'perturbation' in req['instance']:
            continue    # multiple trials for a single item may exist
        item_id = generate_item_id(source, ingestion_time, len(mapping))

        ## item content
        item_content = {
            'input': [
                req['instance']['input']['text']
            ],
            'references': req['instance']['references']
        }

        ## assemble item
        item = {
            'item_id': item_id,
            'item_metadata': {
                'ingestion_time': ingestion_time,
                'contributor': contributor,
                'source': source
            },
            'item_content': item_content,
            'schema_version': SCHEMA_VERSION
        }
        of.write(item)
        mapping[req['instance']['id']] = item_id

    of.close()
    print(f'Converted {len(mapping)} items from {folder} to {OUT_DIR}.')

    return mapping


def helm_to_responses(root, folder, id_map):
    '''
    Convert results from a HELM run into the OpenEval schema (the response table).
    Args:
        root: root directory of the result folders.
        folder: name of the HELM result folder, usually a HELM run entry.
        id_map: output of `helm_to_items`, mapping from HELM item ids to OpenEval item ids.
    '''
    # read data
    res_path = os.path.join(root, folder)
    with open(os.path.join(res_path, 'scenario_state.json'), 'r') as f:
        data = json.load(f)
        adapter = data['adapter_spec']
        reqs = data['request_states']
    with open(os.path.join(res_path, 'per_instance_stats.json'), 'r') as f:
        stats = json.load(f)

    # model (shared fields)
    model_base = {'name': '', 'size': None, 'model_adaptation': {}} 
    model_base['name'] = adapter['model'].split('/')[-1]
    model_base['size'] = None   # TODO: manual check before every run
    model_base['model_adaptation']['system_instruction'] = adapter.get('instructions', '')
    model_base['model_adaptation']['generation_parameters'] = {
        "temperature": adapter['temperature'],
        "do_sample": False, # TODO: manual check before every run
        "top_k": None,
        "top_p": None,
        "max_tokens": adapter['max_tokens']
    }
    model_base['model_adaptation']['tools'] = []    # helm dosen't involve tools

    # metrics (shared)
    metric_names = [
        "exact_match",
        "quasi_exact_match",
        "prefix_exact_match",
        "quasi_prefix_exact_match"
    ]   # TODO: manual check before every run

    res_cnt = {iid: 0 for iid in id_map}
    out_path = os.path.join(OUT_DIR, f'helm_res_{folder}.jsonl')
    of = jsonlines.open(out_path, 'w')

    # unique fields, 1 req => 1 response/trial
    for idx in trange(len(reqs), desc=folder):
        req = reqs[idx]
        helm_id = req['instance']['id']

        ## response id (consider multi-trial items in helm)
        response_id = generate_response_id(id_map[helm_id], model_base['name'], res_cnt[helm_id])
        res_cnt[helm_id] += 1

        ## model (deep copy base then fill per-request fields)
        model = copy.deepcopy(model_base)
        model['model_adaptation']['generation_parameters']['top_k'] = req['request']['top_k_per_token']
        model['model_adaptation']['generation_parameters']['top_p'] = req['request']['top_p']

        ## item adaptation
        prompt = req['request']['prompt']
        separator = adapter['input_prefix']
        demonstrations = [demo.strip() for demo in prompt.split(req['instance']['input']['text'])[0].split(separator) if len(demo.strip()) > 1]
        item_adaptation = {
            'request_input': [prompt],  # TODO: manual check before every run
            'demonstrations': demonstrations,  # TODO: manual check before every run
            'external_resources': []    # helm dosen't involve external resources
        }

        ## response content
        assert type(req['result']['completions']) == list
        response_content = req['result']['completions']

        ## scores
        scores = []
        req_stats = [st for st in stats if st['instance_id'] == helm_id and st['train_trial_index'] == req['train_trial_index']]
        if 'perturbation' in req['instance']:
            req_stats = [st for st in req_stats if 'perturbation' in st and st['perturbation'] == req['instance']['perturbation']]
        else:
            req_stats = [st for st in req_stats if 'perturbation' not in st]

        for req_stat in req_stats:
            for rs in req_stat['stats']:
                if rs['name']['name'] in metric_names:
                    assert rs['count'] == 1
                    scores.append({
                        'metric': {
                            'name': rs['name']['name'],
                            'models': [],           # TODO: manual check before every run
                            'extra_artifacts': []   # TODO: manual check before every run
                        },
                        'value': rs['mean']
                    })

        ## assemble response
        response = {
            'response_id': response_id,
            'model': model,
            'item_adaptation': item_adaptation,
            'response_content': response_content,
            'scores': scores
        }
        of.write(response)
    
    of.close()
    print(f'Converted {sum(res_cnt.values())} responses for {len(res_cnt)} items from {folder} to {OUT_DIR}.')


if __name__ == '__main__':
    root_dir = 'test_data'
    run_dir = 'imdb,model=meta_llama-30b,data_augmentation=canonical'

    # mapping = helm_to_items(root_dir, run_dir)
    # helm_to_responses(root_dir, run_dir, mapping)

    helm_to_benchmarks(root_dir)
