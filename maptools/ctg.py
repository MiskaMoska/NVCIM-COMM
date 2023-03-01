'''
TODO support for STMX
'''

import numpy as np
import networkx as nx
from graphviz import Digraph
from functools import cached_property
from typing import List, Dict, Tuple, Any, Generator
from typing import overload
from operator_graph import *
from utils import *

__all__ = ['CTG']

class CTG(object):

    def __init__(self, opgraph: OperatorGraph, 
                    match_dict: Dict[str, int],
                    map_list: List[np.array],
                    map_dict: Dict[Tuple[int, int, int, int], Dict[str, Any]],
                    arch: str = 'resnet') -> None:
        '''
        Communication Trace Graph
        TODO support first layer cast comm

        Parameters
        ----------
        opgraph : OperatorGraph
            Operator graph for the model

        match_dict : Dict[str, int]
            Matches each compute node in the operator graph to each layer in self.map_list
            For example, to find the corresponding mapping information of node "n1" of the operator graph, use:
            >>> idx = self.match_dict['n1']
            >>> map_info = self.map_list[idx]

        map_list : List[np.array[2]]
            Contains each layer's mapping information
            For example, self.map_list = [
            np.array([[1, 2, 3], [1, 2, 3]]),
            np.array([[2, 2], [2, 2], [2, 2]]),
            ...]
            Where each numpy array represent one layer's mapping information.
            Each element in the numpy array represents a block in current layer mapped xbars.
            The value of each element in the numpy array is the number of xbars the block contains.

        map_dict : Dict[Tuple[int, int, int, int], Dict[str, Any]]
            A look-up-table for each mapped xbar to get the corresponding configuration information.
            The Tuple key is organized as (layer, region, block, idx_in_block).
            For example, to get the configuration information of the second xbar in region 1, block 2 of the first layer, use:
            >>> key = (0, 1, 2, 1)
            >>> config_info = self.map_dict[key]

        kwargs : Dict
            arch : str = 'resnet'
                The architecture of the model (or backbone).
                The arch must be one of OnnxConverter.valid_archs.
        '''
        self.opgraph = opgraph
        self.match_dict = match_dict
        self.map_list = map_list
        self.dicts = map_dict

        self.xbar_nodes: List[Tuple[int, int, int, int]] = []
        self.cast_comms: List[str] = []
        self.merge_comms: List[str] = []
        self.collect_comms: List[str] = []

        if arch == 'resnet':
            self._build_ctg_resnet()

    @cached_property
    def regions(self) -> Generator:
        '''
        Returns all regions in turn
        A region is a set of xbars that execute the same range of output channels in Conv layer
        '''
        idx = 0
        base_idx = 0
        for i, mtx in enumerate(self.map_list):
            for j in range(mtx.shape[0]):
                base_idx += idx
                idx = 0
                region = []
                for k in range(mtx.shape[1]):
                    for t in range(mtx[j, k]):
                        region.append((i, j, k, t))
                        idx += 1
                yield base_idx, region

    def _build_ctg_resnet(self) -> None:
        self.graph = nx.MultiDiGraph()
        self.xbar_nodes = list(self.dicts.keys())
        self.graph.add_nodes_from(self.xbar_nodes)
        self._add_comms_resnet()

    def _add_comms_resnet(self) -> None: 
        # add cast and collect comms
        for e in self.opgraph.egdes: # for ResNet, every edge in opgraph corresponds to a communication
            p_lid = self.match_dict[e[0]]
            s_lid = self.match_dict[e[1]]
            p_mtx = self.map_list[p_lid] # source node map info matrix
            s_mtx = self.map_list[s_lid] # dst node map info matrix

            if self.opgraph.in_degree(e[1]) > 1 \
                and not is_subseq([e[0],e[1]],self.opgraph.trunk): # collect
                assert p_mtx.shape[0] == s_mtx.shape[0], "#regions not match for collect communication"
                for i in range(p_mtx.shape[0]): # for each region in the last layer
                    src_xbar = (p_lid, i, 0, 0) # source node of the collect path
                    dst_xbar = (s_lid, i, 0, 0) # dst node of the collect path
                    comm_name = 'colelct_from_'+str(src_xbar)
                    self.graph.add_node(comm_name)
                    self.collect_comms.append(comm_name)
                    self.graph.add_edge(src_xbar, comm_name)
                    self.graph.add_edge(comm_name, dst_xbar)

            else: # cast
                assert p_mtx.shape[0] == s_mtx.shape[1], "#regions in last later does not match #blocks in this layer"
                for i in range(p_mtx.shape[0]): # for each region in the last layer
                    src_xbar = (p_lid, i, 0, 0) # root node of the cast tree
                    comm_name = 'cast_from_'+str(src_xbar)
                    if comm_name not in self.cast_comms:
                        self.graph.add_node(comm_name)
                        self.graph.add_edge(src_xbar, comm_name)
                        self.cast_comms.append(comm_name)
                    for j in range(s_mtx.shape[0]):
                        for k in range(s_mtx[j, i]):
                            self.graph.add_edge(comm_name, (s_lid, j, i, k))
        
        # add merge comms
        for lid, mtx in enumerate(self.map_list):
            for i in range(mtx.shape[0]): # for each region in the current layer
                if np.sum(mtx[i]) > 1: # there are more than 1 xbar in the current region
                    dst_xbar = (lid, i, 0, 0) # root node of the merge tree
                    comm_name = 'merge_to_'+str(dst_xbar)
                    self.graph.add_node(comm_name)
                    self.graph.add_edge(comm_name, dst_xbar)
                    self.merge_comms.append(comm_name)
                    for j in range(mtx.shape[1]):
                        for k in range(mtx[i, j]):
                            node = (lid, i, j, k)
                            if node != dst_xbar:
                                self.graph.add_edge(node, comm_name)
    @cached_property
    def cast_num(self) -> int:
        return len(self.cast_comms)

    @cached_property
    def merge_num(self) -> int:
        return len(self.merge_comms)

    @cached_property
    def collect_num(self) -> int:
        return len(self.collect_comms)

    @cached_property
    @overload
    def cast_trees(self) -> Generator[Tuple, None, None]:
        for c in self.cast_comms:
            src = self.graph.predecessors(c)
            src = list(src)[0]
            dst = self.graph.successors(c)
            dst = list(dst)
            yield (src, dst)

    @cached_property
    def cast_trees(self) -> Generator[Tuple, None, None]:
        '''
        for test 
        '''
        for i, c in enumerate(self.cast_comms):
            if i >= 0:
                src = self.graph.predecessors(c)
                src = list(src)[0]
                dst = self.graph.successors(c)
                dst = list(dst)
                yield (src, dst)

    @cached_property
    def merge_trees(self) -> Generator[Tuple, None, None]:
        for m in self.merge_comms:
            src = self.graph.predecessors(m)
            src = list(src)
            dst = self.graph.successors(m)
            dst = list(dst)[0]
            yield (src, dst)

    @cached_property
    def collect_pairs(self) -> Generator[Tuple, None, None]:
        for p in self.collect_comms:
            src = self.graph.predecessors(p)
            src = list(src)[0]
            dst = self.graph.successors(p)
            dst = list(dst)[0]
            yield (src, dst)

    def plot_ctg(self) -> None:
        dot = Digraph('graph')
        dot.attr(rankdir='LR')
        # for n in self.graph.nodes:
        #     print(n)
        for n in self.graph.nodes:
            if n in self.cast_comms \
                or n in self.merge_comms \
                or n in self.collect_comms:
                shape = 'point'
            else:
                shape = 'rectangle'
            dot.node(str(n),str(n), fontname='Arial',shape=shape)
        for e in self.graph.edges:
            if e[0] in self.cast_comms or e[1] in self.cast_comms:
                color = 'red'
            elif e[0] in self.merge_comms or e[1] in self.merge_comms:
                color = 'blue'
            elif e[0] in self.collect_comms or e[1] in self.collect_comms:
                color = 'purple'
            dot.edge(str(e[0]),str(e[1]),color=color)
        dot.view()