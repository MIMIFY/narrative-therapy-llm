import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from datetime import datetime
import pdb

class LLMAPI:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        engine: str = "gpt-4o-mini",
        max_retries: int = 3,
        initial_backoff: int = 30
    ):
        """
        初始化LLM API客户端
        
        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL
            engine: 使用的模型名称
            max_retries: 最大重试次数
            initial_backoff: 初始退避时间（秒）
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.engine = engine
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        
    def make_request(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.95,
        frequency_penalty: float = 0,
        presence_penalty: float = 0,
        stop_sequences: Optional[List[str]] = None,
        n: int = 1,
        history: Optional[List[Dict[str, str]]] = None  # 从外部传入历史记录
    ) -> Dict[str, Any]:
        """
        向大模型发送请求
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: top_p参数
            frequency_penalty: 频率惩罚
            presence_penalty: 存在惩罚
            stop_sequences: 停止序列
            n: 生成数量
            history: 对话历史记录，格式为 [{"role": "user/assistant", "content": "消息内容"}, ...]
            
        Returns:
            包含请求和响应的字典
        """
        retry_cnt = 0
        backoff_time = self.initial_backoff
        target_length = max_tokens
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史记录
        if history:
            messages.extend(history)
        
        # 添加当前提示
        messages.append({"role": "user", "content": prompt})
        
        while retry_cnt <= self.max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=self.engine,
                    messages=messages,
                    max_tokens=target_length,
                    temperature=temperature,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    stop=stop_sequences,
                    n=n
                )
                # print(response)
                # pdb.set_trace()
                # 转换响应为可序列化的字典
                response_dict = self._convert_response_to_dict(response)
                
                return {
                    "prompt": prompt,
                    "response": response_dict,
                    "created_at": str(datetime.now())
                }
                
            except Exception as e:
                print(f"Error: {str(e)}")
                if "Please reduce your prompt" in str(e):
                    target_length = int(target_length * 0.8)
                    print(f"Reducing target length to {target_length}, retrying...")
                else:
                    print(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    backoff_time *= 1.5
                retry_cnt += 1
                
        raise Exception("Maximum retries exceeded")
        
    def _convert_response_to_dict(self, response) -> Dict[str, Any]:
        """
        将OpenAI响应对象转换为可序列化的字典
        
        Args:
            response: OpenAI响应对象
            
        Returns:
            可序列化的字典
        """
        # 转换响应对象为字典
        response_dict = response.__dict__
        
        # 转换choices中的对象
        for i, choice in enumerate(response.choices):
            response_dict["choices"][i] = choice.__dict__
            response_dict["choices"][i]["message"] = choice.message.__dict__
            
        # 转换usage对象
        response_dict["usage"] = response.usage.__dict__
        
        return response_dict
        
    def batch_request(
        self,
        prompts: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量发送请求
        
        Args:
            prompts: 提示列表
            **kwargs: 传递给make_request的其他参数
            
        Returns:
            响应列表
        """
        results = []
        for prompt in prompts:
            result = self.make_request(prompt, **kwargs)
            results.append(result)
        return results

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # 加载.env文件
    load_dotenv()
    
    # 从环境变量中设置API密钥
    api_key = os.getenv('API_KEY')
    base_url = os.getenv('BASE_URL')
    
    # 初始化API
    llm_api = LLMAPI(
        api_key=api_key,
        base_url=base_url,
        engine="gpt-3.5-turbo",  # 使用较小的模型进行测试
        max_retries=2,
        initial_backoff=1
    )

    # 测试单个请求
    print("测试单个请求...")
    response = llm_api.make_request(
        prompt="你好，请介绍一下自己。",
        system_prompt="你是一个友好的AI助手。"
    )
    print("响应:", response)    
    
    # 测试批量请求
    print("\n测试批量请求...")
    prompts = ["你好", "再见"]
    responses = llm_api.batch_request(prompts=prompts)
    print("响应数量:", len(responses))
    print(responses)
    
    # 测试带历史记录的对话
    print("\n测试带历史记录的对话...")
    
    # 第一轮对话
    response1 = llm_api.make_request(
        prompt="你好，我是一个正在学习叙事疗法的学生。",
        system_prompt="你是一个专业的叙事治疗师。"
    )
    print("第一轮响应:", response1["response"]["choices"][0]["message"]["content"])
    
    # 构建历史记录
    history = [
        {"role": "user", "content": "你好，我是一个正在学习叙事疗法的学生。"},
        {"role": "assistant", "content": response1["response"]["choices"][0]["message"]["content"]}
    ]
    
    # 第二轮对话（使用历史记录）
    response2 = llm_api.make_request(
        prompt="你能告诉我叙事疗法的核心理念是什么吗？",
        history=history
    )
    print("\n第二轮响应:", response2["response"]["choices"][0]["message"]["content"])
    
    # 更新历史记录
    history.extend([
        {"role": "user", "content": "你能告诉我叙事疗法的核心理念是什么吗？"},
        {"role": "assistant", "content": response2["response"]["choices"][0]["message"]["content"]}
    ])
    
    # 第三轮对话（使用更新后的历史记录）
    response3 = llm_api.make_request(
        prompt="我之前提到我是学生，你觉得这对学习叙事疗法有什么影响？",
        history=history
    )
    print("\n第三轮响应:", response3["response"]["choices"][0]["message"]["content"])
    
    # 更新历史记录
    history.extend([
        {"role": "user", "content": "我之前提到我是学生，你觉得这对学习叙事疗法有什么影响？"},
        {"role": "assistant", "content": response3["response"]["choices"][0]["message"]["content"]}
    ])

    # 打印完整的历史记录
    print("\n完整的对话历史记录:")
    for msg in history:
        print(f"{msg['role']}: {msg['content']}")
