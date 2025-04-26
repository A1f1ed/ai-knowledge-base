#!/usr/bin/env python3
"""
依赖安装脚本，用于解决依赖冲突问题
在Streamlit Cloud中使用前，确保该文件存在于仓库根目录
"""
import subprocess
import sys
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def run_command(cmd):
    """运行shell命令并返回结果"""
    logging.info(f"执行命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                                capture_output=True, text=True)
        logging.info(f"命令成功: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"命令失败: {e}")
        logging.error(f"错误输出: {e.stderr}")
        return False

def install_dependencies():
    """按顺序安装依赖，解决冲突问题"""
    
    # 第1步：安装基础依赖
    steps = [
        # 更新pip
        "pip install --upgrade pip",
        
        # 安装基础依赖
        "pip install streamlit>=1.44.0 python-dotenv>=1.0.0",
        
        # 安装文件处理库
        "pip install pypdf>=3.0.0 docx2txt>=0.8",
        
        # 安装AI相关库
        "pip install sentence-transformers>=2.0.0",
        "pip install torch>=2.2.0",
        
        # 分步安装LangChain相关依赖
        "pip install langchain>=0.3.0",
        "pip install chromadb==0.4.18",
        
        # 最后安装可能有冲突的包
        "pip install langchain-chroma==0.1.0 --no-deps",
        "pip install langchain-huggingface==0.0.1 --no-deps",
        
        # Google API
        "pip install google-api-python-client>=2.0.0 google-auth-httplib2>=0.1.0 google-auth-oauthlib>=1.0.0"
    ]
    
    success = True
    for step in steps:
        if not run_command(step):
            logging.warning(f"步骤失败，但继续安装流程: {step}")
            success = False
    
    return success

if __name__ == "__main__":
    logging.info("开始安装依赖...")
    success = install_dependencies()
    if success:
        logging.info("所有依赖安装成功!")
    else:
        logging.warning("部分依赖安装失败，但应用可能仍能运行") 