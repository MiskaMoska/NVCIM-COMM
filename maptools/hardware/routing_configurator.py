
import os
import pickle
import networkx as nx
from copy import deepcopy
from functools import wraps
from typing import Dict, List, Any, Tuple, Mapping, Callable, Literal
from maptools.nlrt import RoutingTrail, LayoutResult
from maptools.utils import invoke_once, set_precall_method
from maptools.core import (
    MeshEdge, Connection, ROOT_DIR,
    ACG, CTG, RouterPort, PhysicalTile)

__all__ = ['RoutingConfigurator']

class RoutingConfigurator(object):

    # number of router input/output ports
    N_PORT = 5

    # input port name --> port ID mapping
    IP_MAP = {
        RouterPort.LOCAL_I      :0,
        RouterPort.WEST_I       :1,
        RouterPort.EAST_I       :2,
        RouterPort.NORTH_I      :3,
        RouterPort.SOUTH_I      :4
    }

    # output port name --> port ID mapping
    OP_MAP = {
        RouterPort.LOCAL_O      :0,
        RouterPort.WEST_O       :1,
        RouterPort.EAST_O       :2,
        RouterPort.NORTH_O      :3,
        RouterPort.SOUTH_O      :4
    }

    def __init__(
        self,
        cast_trails: Mapping[Connection, RoutingTrail],
        merge_trails: Mapping[Connection, RoutingTrail],
        acg: ACG,
        ctg: CTG,
        layout: LayoutResult,
        **kwargs: Any
    ) -> None:
        '''
        This class generates the NoC routing configuration information
        according to cast trails and merge trails generated by `NocMapper`.

        Parameters
        ----------
        cast_trails: Mapping[Connection, RoutingTrail]
            all cast trails with the connection name as keys and the routing trail as values.

        merge_trails: Mapping[Connection, RoutingTrail]
            all merge trails with the connection name as keys and the routing trail as values.

        acg: ACG
            architecture characterization graph.

        ctg: CTG
            communication trace graph.

        layout: LayoutResult
            layout result containing the physical-to-logical mapping information.

        Key Members
        -----------
        self._injects: Tuple[PhysicalTile, int, int]
            This member stores the injection information, which is a 3-elemnet tuple
            The first element is the first-layer tile through which data injects, the second element 
            is the input port index for injection, which follows the mapping relationship of 
            `self.IP_MAP`, the third element is the VC number that the injecting dataflow traverses on
        
        self._ejects: Tuple[List[PhysicalTile], List[int], List[int]]
            This member stores the ejection information, which is a 3-element tuple
            The first element is a list of ejection tiles through which data ejects, the second element 
            is a list of the corresponding ejecting ports in the ejection tiles, the third element is 
            a list of the corresponding ejecting VCs that the ejecting dataflow traverses on.
            
            Note that the order of the ejection list matters, it is the concatenating order for the 
            output vectors.

        self._crt: Mapping[PhysicalTile, List[List[List[int]]]]
            This is Cast Routing Tables, storing the routing table for each input VC of each 
            input port of each cast router

            Mapping[Key=(x, y), Value=Array[N_PORT] [N_VC] [N_PORT]]
            each element is either 1 or 0, indicating whether the corresponding output port is 
            requested or not.  
        
        self._mrt: Mapping[PhysicalTile, Dict[str, List[int]]]
            This is Merge Routing Tables, storing the input masking tables and output selecting 
            tables of each merge router

            Mapping[Key=(x, y), Value=router configuration dictionary]
            Where the router configuration dictionary follows the structure:
            Dict[Key='input_mask' or 'output_sel', Value=Array[N_PORT]]

            For example, if
            self._mrt[(3, 5)] = {'input_mask': [1, 0, 1, 0, 1], 'output_sel': [0, 1, 0, 0, 0]}
            it means the local, east, and south input ports merges data to the west output port 
            at router (3, 5)

        self._clic/_cloc: Mapping[PhysicalTile, Tuple[int, int]]
            This is Cast Local Input/Output Configuration, storing the input VC selecting information 
            for each router, where the VC selecting information is a 2-element tuple, where:

            The first element is the VC number for local-cast-in/out dataflow, defaulting to be 0 when 
            no cast_in/out, the third element is the VC number for local-gather-in/out dataflow, 
            defaulting to be 0 when no gather_in/out

            For example, if
            self._clic[(2, 4)] = (0, 3), it means the router (2, 4) has both cast-in and gather-in
            dataflow on its local input port, the cast-in dataflow should trasverse on VC0 and the 
            gather-in dataflow should traverse on VC3.
        '''
        self._cast_trails = cast_trails
        self._merge_trails = merge_trails
        self._w = acg.w
        self._h = acg.h
        self._ctg = ctg
        self._layout = layout
        self._minvc: int
        self._cvmap: Mapping[Connection, int]

        self.__dict__.update(kwargs)

    @invoke_once
    def run_config(self) -> None:
        self.vc_assignment()
        self.run_crt_config()
        self.run_mrt_config()
        self.run_local_port_config()

    @set_precall_method(method=run_config)
    def get_vcnumber(self) -> int:
        return self._minvc

    @set_precall_method(method=run_config)
    def get_crt(self
    ) -> Mapping[PhysicalTile, List[List[List[int]]]]:
        return self._crt

    @set_precall_method(method=run_config)
    def get_mrt(self
    ) -> Mapping[PhysicalTile, Dict[str, List[int]]]:
        return self._mrt

    @set_precall_method(method=run_config)
    def get_clic(self
    ) -> Mapping[PhysicalTile, Tuple[bool, int, int]]:
        return self._clic

    @set_precall_method(method=run_config)
    def get_cloc(self
    ) -> Mapping[PhysicalTile, Tuple[bool, int, int]]:
        return self._cloc
    
    @set_precall_method(method=run_config)
    def get_injects(self
    ) -> Tuple[PhysicalTile, int, int]:
        return self._injects

    @set_precall_method(method=run_config)
    def get_ejects(self
    ) -> Tuple[List[PhysicalTile], List[int], List[int]]:
        return self._ejects

    @staticmethod
    def has_intersection(list1: List, list2: List) -> bool:
        set1, set2 = set(list1), set(list2)
        common = set1.intersection(set2)
        return len(common) > 0

    def run_crt_config(self) -> None:
        '''
        This method generates the cast routing tables, which is then stored in `self._crt`.
        '''
        self.vc_assignment()
        self._crt = {(x, y): [[[0 for _ in range(self.N_PORT)] 
                        for _ in range(self._minvc)] 
                        for _ in range(self.N_PORT)]
                        for x in range(self._w) for y in range(self._h)}

        for conn, trail in self._cast_trails.items():
            for src, dst in trail.cast_transitions:
                if src[0] != dst[0] or src[1] != dst[1]:
                    raise AssertionError(
                        "the intra-router transition donnot share the same router ID")
                self._crt[src[0:2]] [self.IP_MAP[src[2]]] [self._cvmap[conn]] [self.OP_MAP[dst[2]]] = 1
        
        self.injection_allocation()
        self.ejection_allocation()
    
    def run_mrt_config(self) -> None:
        '''
        This method generates the merge routing tables, which is then stored in `self._mrt`.
        '''
        g = nx.DiGraph()
        self._mrt = {}
        g.add_nodes_from([(x, y) for x in range(self._w) for y in range(self._h)])
        merge_nodes = [trail.dst[0] for trail in self._merge_trails.values()]

        for trail in self._merge_trails.values():
            g.add_edges_from(trail.path)

        for node in g.nodes:
            x = node[0]
            y = node[1]
            neigh_nodes = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
            input_mask = []
            output_sel = []
            if node not in merge_nodes:
                input_mask.append(1) # non-merge node has local input
                output_sel.append(0) # non-merge node has no local output
            else:
                input_mask.append(0) # merge node has no local input
                output_sel.append(1) # merge node has local output

            for neigh_node in neigh_nodes:
                if neigh_node in g.predecessors(node):
                    input_mask.append(1)
                else:
                    input_mask.append(0)
                if neigh_node in g.successors(node):
                    output_sel.append(1)
                else:
                    output_sel.append(0)
            self._mrt[node] = {'input_mask': input_mask, 'output_sel': output_sel}

    @invoke_once
    def vc_assignment(self) -> None:
        '''
        This method assigns VCs to each cast connection,
        the connection --> VC mapping information is written to `self._cvmap`
        '''
        # constructing communication confliction dictionary
        confliction_dict: Mapping[MeshEdge, List[Connection]] = {}
        for conn, trail in self._cast_trails.items():
            for edge in trail.path:
                if edge not in confliction_dict:
                    confliction_dict[edge] = []
                confliction_dict[edge].append(conn)

        graph_list = []
        for connections in confliction_dict.values():
            graph_list.append(nx.complete_graph(connections))

        # constructing communication confliction graph
        confliction_graph: nx.Graph = nx.compose_all(graph_list)

        '''
        Apart from the link confliction, the confliction at local output port must be taken into
        consideration, too. Actually the essence of link confliction is the output-port-confliction,
        becasuse dataflows that conflict at an output port will then share the succeeding link,
        so when we find a link confliction, we found the corresponding output-port-confliction, too.
        However, the local output port is an exception whose succeeding link is invisible, and we cannot
        take it into consideration while doing link confliction analysis only, so it requires separate handling

        In addition, when two dataflows inject the NoC through the same local input port, it need no
        special handling, because they may head for different output ports and donnot form a confliction,
        or else if they head for the same output port, they definately share the same link then, which 
        can be detected through link confliction analysis only.
        '''
        # adding local-output-conflictions to the confliction graph
        for s_conn, s_trail in self._cast_trails.items():
            if trail.is_casted_gather():
                for d_conn, d_trail in self._cast_trails.items():
                    if d_conn != s_conn:
                        if self.has_intersection(s_trail.dst, d_trail.dst):
                            print(f"connection {s_conn} has confliction with connection {d_conn} at local output port")
                            confliction_graph.add_edge(s_conn, d_conn)

        # apply greedy coloring algorithm
        self._cvmap: Mapping[Connection, int] = nx.greedy_color(confliction_graph)

        # calculate the maximum confliction and the minimum VC
        max_confliction = max([len(c) for c in confliction_dict.values()])
        self._minvc = len(set(list(self._cvmap.values())))
        print('max confliction:', max_confliction, 'min vc:', self._minvc)

    def injection_allocation(self) -> None:
        '''
        This function allocates an available input port and VC for injecting dataflow,
        and writes the injection information into `self._injects`.
        '''
        inject_tile = self._layout[self._ctg.head_tile]
        for ip in range(1, 5): # search through west, east, north and south ports
            for vc in range(self._minvc): # search through all VCs
                if sum(self._crt[inject_tile][ip][vc]) == 0: # the input vc has no transfer request
                    self._injects = (inject_tile, ip, vc)

                    # update the cast routing table by adding request to local output port
                    self._crt[inject_tile][ip][vc][0] = 1
                    return
                
        # raise RuntimeError(f"failed to allocate the fucking injection port for tile {inject_tile}")
    
    def ejection_allocation(self) -> None:
        '''
        This function allocates available output ports and VCs for all ejecting dataflow,
        and writes the ejection information into `self._ejects`.
        '''
        eject_tiles = [self._layout[t] for t in self._ctg.tail_tiles]
        eject_ports = []
        for et in eject_tiles:
            # record whether an output port is occupied or not
            ocp_dict = {op: False for op in range(1, 5)} 
            for ip in range(1, 5):
                for vc in range(self._minvc):
                    for op in range(1, 5):
                        if bool(self._crt[et][ip][vc][op]):
                            ocp_dict[op] = True

            for op, flag in ocp_dict.items():
                if not flag:
                    eject_ports.append(op)
                    
                    # update the cast routing table by adding request from local input port
                    self._crt[et][0][0][op] = 1
                    break
            else:
                # raise RuntimeError(f"failed to allocate the fucking ejection port for tile {et}")
                pass
        # the output VCs donnot matter, so they are default to be 0
        self._ejects = (eject_tiles, eject_ports, [0]*len(eject_ports))

    def run_local_port_config(self) -> None:
        '''
        This method generates the cast local input/output configurations, then stores them into
        `self._clic` and `self._cloc`.
        Make sure to call this method after calling `self.run_crt_config()`
        '''
        self.vc_assignment()
        self._clic = {(x, y): (False, 0, 0) for x in range(self._w) for y in range(self._h)}
        self._cloc = deepcopy(self._clic)

        def get_config(
            has_cast: Callable, has_gather: Callable, 
            cast_comm: Callable, gather_comm: Callable,
            type: Literal['in', 'out'] = 'in'
        ) -> Tuple[bool, int, int]:
            is_cast = has_cast(tile)
            is_gather = has_gather(tile)
            cast_vc, gather_vc = 0, 0

            if is_cast:
                # if a tile has cast_in/out, then the tile may be head/tail
                # then it has no cast_in/out connection
                if type == 'in' and self._ctg.is_head_tile(tile):
                    cast_vc = self._injects[2]

                elif type == 'out' and self._ctg.is_tail_tile(tile):
                    cast_vc = 0
                    
                else:
                    cast_conn = cast_comm(tile)
                    cast_vc = self._cvmap[cast_conn]

            if is_gather:
                # if a tile has gather_out, it must have gather_out connection
                # if a tile has gather_in, it must have cast_in connection
                # so no special handling required for head/tail
                gather_conn = gather_comm(tile)
                gather_vc = self._cvmap[gather_conn]

            return (cast_vc, gather_vc)

        for tile in self._ctg.tile_nodes:
            router = self._layout[tile]

            # generate local input configuration
            self._clic[router] = get_config(
                self._ctg.has_cast_in, 
                self._ctg.has_gather_in,
                self._ctg.cast_pred_comm, 
                self._ctg.gather_pred_comm,
                type='in'
            )
            
            # generate local output configuration
            self._cloc[router] = get_config(
                self._ctg.has_cast_out, 
                self._ctg.has_gather_out,
                self._ctg.cast_succ_comm, 
                self._ctg.gather_succ_comm,
                type='out'
            )