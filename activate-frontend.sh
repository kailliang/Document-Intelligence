#!/bin/bash
# 激活前端conda环境并启动开发服务器
source ~/miniconda3/etc/profile.d/conda.sh
conda activate patent-frontend
echo "前端环境已激活 (patent-frontend)"
echo "当前目录: client/"
cd client
echo ""
echo "可用命令:"
echo "  npm run dev      # 启动开发服务器"
echo "  npm run build    # 构建生产版本"
echo "  npm run lint     # 运行代码检查"
echo ""
# 启动一个保持环境激活的新shell
exec $SHELL