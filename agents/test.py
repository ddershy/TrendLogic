import sys
import os

# 将项目根目录加入到系统路径，解决相对导入报错
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.router_agent import RouterAgent
from agents.llm_client import LLMClient

llm_client = LLMClient()
# 因为 RouterAgent 内部自带了 LLMClient 的实例化，直接调用即可
agent = RouterAgent(llm_client=llm_client)

# 运行测试
result = agent.run("我想要开一个卖二次元周边的谷子店")
print(result)