"""
基本面指标模块
作为技术指标的一个子类别
"""

from .altman_z_score import AltmanZScore
from .dupont_analysis import DupontAnalysis

__all__ = ['AltmanZScore', 'DupontAnalysis']
