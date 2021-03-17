#!/usr/bin/env python3
import torch
import math
import GNNAdvisor as GNNA
from param import *

class GNNAFunction(torch.autograd.Function):
    @staticmethod
    def forward(ctx, X, weight, inputInfo):
        ctx.save_for_backward(X, weight)
        ctx.inputInfo = inputInfo

        X_prime = GNNA.forward(X, weight, inputInfo.row_pointers, inputInfo.column_index, 
                                inputInfo.degrees, inputInfo.partPtr, inputInfo.part2Node, inputInfo.threadPerBlock)[0]
        return X_prime

    @staticmethod
    def backward(ctx, d_output):
        X, weight = ctx.saved_tensors
        inputInfo = ctx.inputInfo

        d_input, d_weight = GNNA.backward(d_output, X, weight, inputInfo.row_pointers, inputInfo.column_index, 
                                        inputInfo.degrees, inputInfo.partPtr, inputInfo.part2Node, inputInfo.threadPerBlock)

        return d_input, d_weight, None

class GCNConv(torch.nn.Module):
    def __init__(self, input_dim, output_dim):
        super(GCNConv, self).__init__()
        self.weights = torch.nn.Parameter(torch.randn(input_dim, output_dim))
        self.reset_parameters()

    def reset_parameters(self):
        stdv = 1. / math.sqrt(self.weights.size(1))
        self.weights.data.uniform_(-stdv, stdv)

    def forward(self, X, inputInfo):
        '''
        @param:
        X:  the input tensor of the graph node embedding, shape: [n_nodes, n_dim].
        A:  the CSR node pointer of the graph, shape: [node, 1].
        edges: the CSR edge list of the graph, shape: [edge, 1].
        partitioin: for the graph with the part-based optimziation.
        '''
        return GNNAFunction.apply(X, self.weights, inputInfo)


class GAccFunction_GIN(torch.autograd.Function):
    @staticmethod
    def forward(ctx, X, weights, inputInfo):
        ctx.threadPerBlock = inputInfo.threadPerBlock

        X = GNNA.forward(X, inputInfo)[0]
        ctx.save_for_backward(X, inputInfo)
        X_prime = torch.mm(X, weights)

        return X_prime

    @staticmethod
    def backward(ctx, d_output):
        X, row_pointers, column_index, weights, degrees, partPtr, part2Node = ctx.saved_tensors

        d_weights = torch.mm(X.transpose(0,1), d_output)
        d_input_prime = torch.mm(d_output, weights.transpose(0,1))
        d_input = GNNA.backward(d_input_prime, row_pointers, column_index, degrees, partPtr, part2Node, ctx.threadPerBlock)[0]
        
        return d_input, d_weights, None, None, None, None, None, None

class GINConv(torch.nn.Module):
    def __init__(self, input_dim, output_dim):
        super(GINConv, self).__init__()
        self.weights = torch.nn.Parameter(torch.randn(input_dim, output_dim))
        self.reset_parameters()

    def reset_parameters(self):
        stdv = 1. / math.sqrt(self.weights.size(1))
        self.weights.data.uniform_(-stdv, stdv)

    def forward(self, X, inputInfo):
        '''
        @param:
        X:  the input tensor of the graph node embedding, shape: [n_nodes, n_dim].
        A:  the CSR node pointer of the graph, shape: [node, 1].
        edges: the CSR edge list of the graph, shape: [edge, 1].
        partitioin: for the graph with the part-based optimziation.
        '''
        return GAccFunction_GIN.apply(X, self.weights, inputInfo)
