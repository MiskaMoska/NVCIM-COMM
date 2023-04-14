import os
import pickle
from typing import List, Tuple, Dict
import networkx as nx
import logging
from maptools.core import ROOT_DIR

__all__ = [
    'dec2bin',
    'is_subseq',
    'build_mesh',
    'read_params',
    'read_quantparams',
    'read_mapinfo',
    'read_cfginfo',
    'read_results',
    'get_logger'
]

def dec2bin(dec_num, bit_wide: int = 16) -> str:    
    _, bin_num_abs = bin(dec_num).split('b')    
    if len(bin_num_abs) > bit_wide:        
        raise ValueError   
    else:        
        if dec_num >= 0:            
            bin_num = bin_num_abs.rjust(bit_wide, '0')        
        else:            
            _, bin_num = bin(2**bit_wide + dec_num).split('b')    
    return bin_num 

def is_subseq(a: List, b: List) -> bool:
    '''
    This function judges if is the susequence of b, where a must be a 2-element list.
    '''
    for i in range(len(b)-1):
        if a[0] == b[i]:
            if b[i+1] == a[1]:
                return True
    return False

def build_mesh(eager_nodes: List[Tuple[int, int]]) -> nx.Graph:
    '''
    This function returns a mesh graph from given range of nodes.
    This function is designed for constructing steiner tree for cast routing plan.
    '''
    xs, ys = zip(*eager_nodes)
    sx = min(xs)
    dx = max(xs)
    sy = min(ys)
    dy = max(ys)
    g = nx.Graph()
    for x in range(sx, dx+1):
        for y in range(sy, dy):
            g.add_edge((x,y),(x,y+1))
    for y in range(sy, dy+1):
        for x in range(sx, dx):
            g.add_edge((x,y),(x+1,y))
    return g

def read_params(mapname: str) -> Dict:
    file_dir = os.path.join(ROOT_DIR, 'mapsave', mapname, 'params.pkl')
    with open(file_dir, 'rb') as f:
        params = pickle.load(f)
    return params

def read_quantparams(mapname: str) -> Dict:
    file_dir = os.path.join(ROOT_DIR, 'mapsave', mapname, 'quantparams.pkl')
    with open(file_dir, 'rb') as f:
        params = pickle.load(f)
    return params

def read_mapinfo(mapname: str) -> Dict:
    file_dir = os.path.join(ROOT_DIR, 'mapsave', mapname, 'mapinfo.pkl')
    with open(file_dir, 'rb') as f:
        mapinfo = pickle.load(f)
    return mapinfo

def read_cfginfo(mapname: str) -> Dict:
    file_dir = os.path.join(ROOT_DIR, 'mapsave', mapname, 'cfginfo.pkl')
    with open(file_dir, 'rb') as f:
        cfginfo = pickle.load(f)
    return cfginfo

def read_results(mapname: str, quantize: bool = False) -> Dict:
    file_name = 'quantres.pkl' if quantize else 'res.pkl'
    file_dir = os.path.join(ROOT_DIR, 'mapsave', mapname, 'calcusim', file_name)
    with open(file_dir, 'rb') as f:
        results = pickle.load(f)
    return results

def get_logger(name: str, dir: str) -> logging.Logger:
    filename = os.path.join(dir, f'{name}.log')
    logger = logging.getLogger(name)
    fh = logging.FileHandler(filename, mode='w', encoding='utf-8')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    return logger