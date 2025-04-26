#!/usr/bin/env python3
"""
Streamlit应用入口点
先运行依赖安装脚本，然后导入主应用
"""
import subprocess
import sys
import os
import logging
import importlib.util
import streamlit as st

def setup_logging():
    """设置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def run_setup_script():
    """运行安装脚本"""
    try:
        logger.info("尝试运行依赖安装脚本...")
        # 检查是否在Streamlit Cloud环境
        is_cloud = os.environ.get('STREAMLIT_SHARING', False) or os.environ.get('KUBERNETES_SERVICE_HOST', False)
        
        if is_cloud:
            logger.info("检测到Streamlit Cloud环境，运行依赖安装脚本...")
            import setup_deps
            setup_deps.install_dependencies()
        else:
            logger.info("本地环境，跳过依赖安装...")
        return True
    except Exception as e:
        logger.error(f"依赖安装失败: {str(e)}")
        st.error(f"依赖安装失败: {str(e)}")
        return False

def import_main_app():
    """导入主应用模块"""
    try:
        logger.info("导入主应用模块...")
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        return main_module
    except Exception as e:
        logger.error(f"导入主应用失败: {str(e)}")
        st.error(f"导入主应用失败: {str(e)}")
        return None

def main():
    """主函数"""
    # 设置页面标题
    st.set_page_config(
        page_title="Knowledge Base",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 运行设置脚本
    setup_success = run_setup_script()
    if not setup_success:
        st.error("应用初始化失败，请检查日志获取详细信息。")
        st.stop()
    
    # 导入并运行主应用
    main_module = import_main_app()
    if main_module:
        # 调用主模块的main函数
        if hasattr(main_module, 'main'):
            main_module.main()
        else:
            st.error("主模块中未找到main()函数")
    else:
        st.error("无法导入主应用模块")

if __name__ == "__main__":
    main() 