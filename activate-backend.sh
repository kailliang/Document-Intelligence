#!/bin/bash
# 激活后端conda环境并启动服务器
source ~/miniconda3/etc/profile.d/conda.sh
conda activate patent-backend
echo "后端环境已激活 (patent-backend)"
echo "当前目录: server/"
cd server
echo ""
echo "可用命令:"
echo "  uvicorn app.__main__:app --reload    # 启动开发服务器"
echo "  python -m pip list                  # 查看已安装包"
echo ""
# 启动一个保持环境激活的新shell
exec $SHELL