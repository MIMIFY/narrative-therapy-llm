#!/usr/bin/env python3
"""
One-command initialisation script for the INT system:
  1. Check Python version
  2. Check / create .env file
  3. Initialise SQLite database
  4. Download BGE-M3 embedding model and build ChromaDB index
"""
import sys
import os
import asyncio
from pathlib import Path


def check_python_version():
    if sys.version_info < (3, 10):
        print("需要 Python 3.10+，当前版本:", sys.version)
        sys.exit(1)
    print(f"Python 版本: {sys.version_info.major}.{sys.version_info.minor}")


def check_env_file():
    env_path = Path(__file__).parent / ".env"
    example_path = Path(__file__).parent / ".env.example"
    if not env_path.exists():
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
            print("已从 .env.example 创建 .env，请填入你的 OpenRouter API key")
        else:
            print("未找到 .env 文件，请创建并填入配置")
    else:
        print(".env 文件存在")


def init_rag():
    print("\n正在初始化 RAG 引擎（首次运行会下载 BGE-M3 模型，约 600MB，请耐心等待）...")
    from backend.core.rag_engine import rag_engine
    rag_engine.initialize()
    print("RAG 索引初始化完成")


async def init_database():
    print("正在初始化数据库...")
    from backend.database import init_db
    await init_db()
    print("数据库初始化完成")


def main():
    print("=" * 50)
    print("INT 叙事疗法 AI 咨询师 - 初始化")
    print("=" * 50)

    check_python_version()
    check_env_file()

    # Switch to int_app directory so relative paths in config work correctly
    os.chdir(Path(__file__).parent)

    # Load .env before importing settings
    from dotenv import load_dotenv
    load_dotenv()

    asyncio.run(init_database())
    init_rag()

    print("\n" + "=" * 50)
    print("初始化完成！")
    print("\n启动服务：")
    print("  cd int_app")
    print("  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    print("\n然后打开浏览器访问：http://localhost:8000")
    print("=" * 50)


if __name__ == "__main__":
    main()
