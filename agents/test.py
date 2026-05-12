import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.graph import TrendLogicGraph

graph = TrendLogicGraph()
result = graph.run("我想要开一个卖二次元周边的谷子店")
print(result)
