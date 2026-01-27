#!/bin/bash
echo "=== SSH 连接问题完整诊断 ==="
echo ""

# 1. 检查 SSH 目录和文件
echo "1. 检查 SSH 目录和权限:"
ls -la ~/.ssh/
echo ""

# 2. 检查密钥文件内容
echo "2. 检查公钥内容:"
if [ -f ~/.ssh/id_rsa.pub ]; then
    echo "公钥前100字符:"
    head -c 100 ~/.ssh/id_rsa.pub
    echo -e "\n"
    echo "公钥行数: $(wc -l < ~/.ssh/id_rsa.pub)"
else
    echo "❌ 未找到 id_rsa.pub"
fi
echo ""

# 3. 检查 SSH 代理
echo "3. 检查 SSH 代理:"
eval "$(ssh-agent -s)" 2>/dev/null
ssh-add -l
echo ""

# 4. 检查 GitHub SSH 配置
echo "4. 检查 ~/.ssh/config:"
if [ -f ~/.ssh/config ]; then
    cat ~/.ssh/config
else
    echo "没有找到 config 文件"
fi
echo ""

# 5. 详细测试连接
echo "5. 测试连接 (详细模式):"
echo "运行: ssh -vT git@github.com"
echo "按 Ctrl+C 停止"
ssh -vT git@github.com
