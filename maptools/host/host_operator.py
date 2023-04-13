import torch
import torch.nn as nn
import torch.nn.functional as F
from functools import wraps
from  maptools.maptype import OperatorConfig

__all__ = ['HostOperator']

class GlobalAveragePool(nn.Module):

    def __init__(self) -> None:
        super().__init__()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.adaptive_avg_pool2d(x, 1)


class HostOperator(nn.Module):

    legal_ops = ['GlobalAveragePool', 'Flatten', 'Gemm']

    def __init__(self, config: OperatorConfig) -> None:
        super().__init__()
        self.op_type = config['op_type']
        self.build_operation(config)

    def build_operation(self, config: OperatorConfig):
        assert self.op_type in self.legal_ops, (
            f"usupported op_type {self.op_type} when building host operation")
        
        if self.op_type == 'GlobalAveragePool':
            self.operation = GlobalAveragePool()
        
        elif self.op_type == 'Flatten':
            self.operation = nn.Flatten()

        elif self.op_type == 'Gemm':
            self.operation = nn.Linear(config['fc_len_inv'], config['fc_len_outv'])
            self.operation.weight.data = torch.tensor(config['fc_weight'])
            self.operation.bias.data = torch.tensor(config['fc_bias'])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.operation(x)