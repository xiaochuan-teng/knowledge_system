#!/bin/bash
echo "=== 完全重设 SSH 配置 ==="

# 1. 停止 SSH 代理
killall ssh-agent 2>/dev/null

# 2. 备份并删除旧配置
mkdir -p ~/.ssh/backup
mv ~/.ssh/id_rsa* ~/.ssh/backup/ 2>/dev/null
mv ~/.ssh/known_hosts ~/.ssh/backup/ 2>/dev/null
mv ~/.ssh/config ~/.ssh/backup/ 2>/dev/null

# 3. 生成新密钥（使用默认设置，不要设置密码）
echo "生成新密钥..."
#ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -C "github-$(date +%Y%m%d)"
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -C "984967819@qq.com"

# 4. 设置正确权限
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# 5. 创建 SSH 配置文件
cat > ~/.ssh/config << EOF
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_rsa
    IdentitiesOnly yes
    PreferredAuthentications publickey
EOF

chmod 600 ~/.ssh/config

# 6. 启动 SSH 代理并添加密钥
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa

# 7. 显示公钥
echo ""
echo "✅ 新密钥生成完成！"
echo "=== 请复制以下内容到 GitHub ==="
echo ""
cat ~/.ssh/id_rsa.pub
echo ""
echo "=== 以上内容结束 ==="
echo ""
echo "GitHub 设置地址: https://github.com/settings/ssh/new"
echo ""
echo "添加完成后，测试连接: ssh -T git@github.com"
