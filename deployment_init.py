#!/usr/bin/env python
"""
部署模块初始化脚本
为现有项目创建默认部署脚本
"""

import os
import sys
import django

# 添加项目路径到系统路径
project_path = '/data/knowledge_system_test'
sys.path.append(project_path)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knowledge_system.settings')

try:
    django.setup()
except Exception as e:
    print(f"Django设置失败: {e}")
    sys.exit(1)

from kb.models import Project, DeploymentServer, DeploymentScript
from django.contrib.auth import get_user_model

User = get_user_model()

# 完整的 update.sh 脚本模板
DEFAULT_UPDATE_SCRIPT = """#!/bin/bash

# 部署脚本配置 - 这些变量将在运行时根据项目配置替换
UPBAKDIR="{backup_path}"
DCSDIR="{cpp_install_path}"
TOMCATDIR="{java_install_path}"

# 服务名称配置
TOMCAT_SERVICE_NAME="tomcat"
PCMS_SERVICE_NAME="pcms"
WATCH_SERVICE_NAME="watch_pcms"

# 数据库配置 - 从配置文件读取
dcsconfig_file="${DCSDIR}/config/config.conf"

if [ -f "$dcsconfig_file" ]; then
    DBHOST_IP=$(sed '/^Host=/!d;s/.*=//' "$dcsconfig_file" | sed -e 's/\\r//g')
    DBPORT=$(sed '/^Port=/!d;s/.*=//' "$dcsconfig_file" | sed -e 's/\\r//g')
    DBUSERNAME=$(sed '/^Username=/!d;s/.*=//' "$dcsconfig_file" | sed -e 's/\\r//g')
    DBPASSWORD=$(sed '/^Password=/!d;s/.*Password=//' "$dcsconfig_file" | sed -e 's/\\r//g')
    DBDATABASE=$(sed '/^Database=/!d;s/.*=//' "$dcsconfig_file" | sed -e 's/\\r//g')
else
    echo "警告: 数据库配置文件 $dcsconfig_file 不存在"
    DBHOST_IP="localhost"
    DBPORT="3306"
    DBUSERNAME="root"
    DBPASSWORD="root"
    DBDATABASE="pcms"
fi

DATE=$(date +"%Y%m%d%H%M")

# 创建备份目录
echo "创建备份目录..."
mkdir -p "${UPBAKDIR}/${DATE}/up/java/"
mkdir -p "${UPBAKDIR}/${DATE}/bak/java/"
mkdir -p "${UPBAKDIR}/${DATE}/up/H5/"
mkdir -p "${UPBAKDIR}/${DATE}/bak/H5/"
mkdir -p "${UPBAKDIR}/${DATE}/up/dcs/"
mkdir -p "${UPBAKDIR}/${DATE}/bak/dcs/"
mkdir -p "${UPBAKDIR}/${DATE}/bak/"

echo "开始执行部署..."

# ============ 数据库备份 ============
echo "步骤1: 备份数据库..."
if command -v mysqldump &> /dev/null; then
    if [ -n "$DBPASSWORD" ]; then
        mysqldump -u "$DBUSERNAME" -P"$DBPORT" -h "$DBHOST_IP" -p"$DBPASSWORD" \
            --databases "$DBDATABASE" --single-transaction --set-gtid-purged=off --hex-blob \
            > "${UPBAKDIR}/${DATE}/bak/pcms.sql"
        
        if [ $? -eq 0 ]; then
            echo "数据库备份成功: ${UPBAKDIR}/${DATE}/bak/pcms.sql"
        else
            echo "警告: 数据库备份失败"
        fi
    else
        echo "警告: 数据库密码为空，跳过数据库备份"
    fi
else
    echo "警告: mysqldump 命令未找到，跳过数据库备份"
fi

# ============ Java全量包部署 ============
if [ -f /opt/pcms.war ]; then
    echo "步骤2: 开始更新Java全量包..."
    
    # 移动更新文件
    mv /opt/pcms.war "${UPBAKDIR}/${DATE}/up/java/"
    
    # 停止服务
    echo "停止相关服务..."
    if systemctl list-units --full -all | grep -Fq "$WATCH_SERVICE_NAME.service"; then
        systemctl stop "$WATCH_SERVICE_NAME" || true
    fi
    
    if systemctl list-units --full -all | grep -Fq "$TOMCAT_SERVICE_NAME.service"; then
        systemctl stop "$TOMCAT_SERVICE_NAME" || true
    fi
    
    # 等待服务停止
    echo "等待服务停止..."
    sleep 5
    
    # 检查tomcat进程是否还在运行
    if ps aux | grep -v grep | grep -q tomcat; then
        echo "强制停止tomcat进程..."
        pkill -9 -f tomcat || true
        sleep 2
    fi
    
    # 备份当前版本
    echo "备份当前版本..."
    if [ -d "${TOMCATDIR}/webapps/pcms" ]; then
        mv "${TOMCATDIR}/webapps/pcms" "${UPBAKDIR}/${DATE}/bak/java/"
        echo "已备份pcms目录"
    fi
    
    if [ -f "${TOMCATDIR}/webapps/pcms.war" ]; then
        mv "${TOMCATDIR}/webapps/pcms.war" "${UPBAKDIR}/${DATE}/bak/java/"
        echo "已备份pcms.war文件"
    fi
    
    # 部署新版本
    echo "部署新版本..."
    cp "${UPBAKDIR}/${DATE}/up/java/pcms.war" "${TOMCATDIR}/webapps/"
    
    # 临时启动以解压war包
    echo "临时启动Tomcat解压war包..."
    if systemctl list-units --full -all | grep -Fq "$TOMCAT_SERVICE_NAME.service"; then
        systemctl start "$TOMCAT_SERVICE_NAME"
        sleep 15
        
        # 停止服务以恢复配置文件
        systemctl stop "$TOMCAT_SERVICE_NAME"
        sleep 5
    else
        echo "警告: Tomcat服务未找到，尝试直接解压"
        if [ -f "${TOMCATDIR}/bin/startup.sh" ]; then
            "${TOMCATDIR}/bin/startup.sh"
            sleep 15
            "${TOMCATDIR}/bin/shutdown.sh"
            sleep 5
        fi
    fi
    
    # 恢复配置文件和许可
    echo "恢复配置文件和许可..."
    if [ -f "${UPBAKDIR}/${DATE}/bak/java/pcms/license/pcmsLicense.li" ]; then
        cp "${UPBAKDIR}/${DATE}/bak/java/pcms/license/pcmsLicense.li" \
           "${TOMCATDIR}/webapps/pcms/license/"
        echo "已恢复许可文件"
    fi
    
    if [ -d "${UPBAKDIR}/${DATE}/bak/java/pcms/WEB-INF/classes/config/property" ]; then
        cp -r "${UPBAKDIR}/${DATE}/bak/java/pcms/WEB-INF/classes/config/property/"* \
              "${TOMCATDIR}/webapps/pcms/WEB-INF/classes/config/property/" 2>/dev/null || true
        echo "已恢复配置文件"
    fi
    
    # 恢复图片等静态文件
    echo "恢复静态文件..."
    if [ -d "${UPBAKDIR}/${DATE}/bak/java/pcms/roomPicture" ]; then
        rm -rf "${TOMCATDIR}/webapps/pcms/roomPicture/"
        cp -r "${UPBAKDIR}/${DATE}/bak/java/pcms/roomPicture/" \
              "${TOMCATDIR}/webapps/pcms/" 2>/dev/null || true
        echo "已恢复会议室图片"
    fi
    
    if [ -d "${UPBAKDIR}/${DATE}/bak/java/pcms/upload" ]; then
        rm -rf "${TOMCATDIR}/webapps/pcms/upload/"
        cp -r "${UPBAKDIR}/${DATE}/bak/java/pcms/upload/" \
              "${TOMCATDIR}/webapps/pcms/" 2>/dev/null || true
        echo "已恢复上传文件"
    fi
    
    # 清理缓存
    echo "清理Tomcat缓存..."
    rm -rf "${TOMCATDIR}/work/Catalina/" 2>/dev/null || true
    rm -rf "${TOMCATDIR}/temp/"* 2>/dev/null || true
    
    # 启动服务
    echo "启动服务..."
    if systemctl list-units --full -all | grep -Fq "$TOMCAT_SERVICE_NAME.service"; then
        systemctl start "$TOMCAT_SERVICE_NAME"
    else
        if [ -f "${TOMCATDIR}/bin/startup.sh" ]; then
            "${TOMCATDIR}/bin/startup.sh"
        fi
    fi
    
    if systemctl list-units --full -all | grep -Fq "$WATCH_SERVICE_NAME.service"; then
        systemctl start "$WATCH_SERVICE_NAME"
    fi
    
    echo "Java全量包更新完成！"
else
    echo "信息: 未找到Java全量包(pcms.war)，跳过此步骤"
fi

# ============ Java增量包部署 ============
if [ -f /opt/pcms.zip ]; then
    echo "步骤3: 开始更新Java增量包..."
    
    # 解压增量包
    unzip -o /opt/pcms.zip -d "${UPBAKDIR}/${DATE}/up/java/" 2>/dev/null || true
    rm -f /opt/pcms.zip
    
    # 停止服务
    echo "停止相关服务..."
    if systemctl list-units --full -all | grep -Fq "$WATCH_SERVICE_NAME.service"; then
        systemctl stop "$WATCH_SERVICE_NAME" || true
    fi
    
    if systemctl list-units --full -all | grep -Fq "$TOMCAT_SERVICE_NAME.service"; then
        systemctl stop "$TOMCAT_SERVICE_NAME" || true
    fi
    
    sleep 5
    
    # 检查tomcat进程是否还在运行
    if ps aux | grep -v grep | grep -q tomcat; then
        pkill -9 -f tomcat || true
        sleep 2
    fi
    
    # 备份当前版本
    echo "备份当前版本..."
    if [ -d "${TOMCATDIR}/webapps/pcms" ]; then
        cp -r "${TOMCATDIR}/webapps/pcms" "${UPBAKDIR}/${DATE}/bak/java/" 2>/dev/null || true
    fi
    
    # 更新文件
    echo "更新文件..."
    if [ -d "${UPBAKDIR}/${DATE}/up/java/pcms" ]; then
        cp -r "${UPBAKDIR}/${DATE}/up/java/pcms/"* "${TOMCATDIR}/webapps/pcms/" 2>/dev/null || true
    fi
    
    # 恢复许可和配置
    echo "恢复许可和配置..."
    if [ -f "${UPBAKDIR}/${DATE}/bak/java/pcms/license/pcmsLicense.li" ]; then
        cp "${UPBAKDIR}/${DATE}/bak/java/pcms/license/pcmsLicense.li" \
           "${TOMCATDIR}/webapps/pcms/license/"
    fi
    
    if [ -d "${UPBAKDIR}/${DATE}/bak/java/pcms/WEB-INF/classes/config/property" ]; then
        cp -r "${UPBAKDIR}/${DATE}/bak/java/pcms/WEB-INF/classes/config/property/"* \
              "${TOMCATDIR}/webapps/pcms/WEB-INF/classes/config/property/" 2>/dev/null || true
    fi
    
    # 清理缓存
    rm -rf "${TOMCATDIR}/work/Catalina/" 2>/dev/null || true
    
    # 启动服务
    echo "启动服务..."
    if systemctl list-units --full -all | grep -Fq "$TOMCAT_SERVICE_NAME.service"; then
        systemctl start "$TOMCAT_SERVICE_NAME"
    else
        if [ -f "${TOMCATDIR}/bin/startup.sh" ]; then
            "${TOMCATDIR}/bin/startup.sh"
        fi
    fi
    
    if systemctl list-units --full -all | grep -Fq "$WATCH_SERVICE_NAME.service"; then
        systemctl start "$WATCH_SERVICE_NAME"
    fi
    
    echo "Java增量包更新完成！"
else
    echo "信息: 未找到Java增量包(pcms.zip)，跳过此步骤"
fi

# ============ C++程序部署 ============
if [ -f /opt/pcms ]; then
    echo "步骤4: 开始更新C++程序..."
    
    # 移动更新文件
    mv /opt/pcms "${UPBAKDIR}/${DATE}/up/dcs/"
    
    # 停止服务
    echo "停止相关服务..."
    if systemctl list-units --full -all | grep -Fq "$WATCH_SERVICE_NAME.service"; then
        systemctl stop "$WATCH_SERVICE_NAME" || true
    fi
    
    if systemctl list-units --full -all | grep -Fq "$PCMS_SERVICE_NAME.service"; then
        systemctl stop "$PCMS_SERVICE_NAME" || true
    fi
    
    sleep 5
    
    # 检查pcms进程是否还在运行
    if ps aux | grep -v grep | grep -q pcms; then
        pkill -9 -f pcms || true
        sleep 2
    fi
    
    # 备份当前版本
    echo "备份当前版本..."
    if [ -f "${DCSDIR}/pcms" ]; then
        mv "${DCSDIR}/pcms" "${UPBAKDIR}/${DATE}/bak/dcs/"
    fi
    
    # 部署新版本
    echo "部署新版本..."
    cp "${UPBAKDIR}/${DATE}/up/dcs/pcms" "${DCSDIR}/"
    chmod 755 "${DCSDIR}/pcms"
    
    # 启动服务
    echo "启动服务..."
    if systemctl list-units --full -all | grep -Fq "$PCMS_SERVICE_NAME.service"; then
        systemctl start "$PCMS_SERVICE_NAME"
    else
        # 尝试直接启动
        if [ -f "${DCSDIR}/pcms" ]; then
            cd "${DCSDIR}"
            "./pcms" &
        fi
    fi
    
    if systemctl list-units --full -all | grep -Fq "$WATCH_SERVICE_NAME.service"; then
        systemctl start "$WATCH_SERVICE_NAME"
    fi
    
    echo "C++程序更新完成！"
else
    echo "信息: 未找到C++程序(pcms)，跳过此步骤"
fi

# ============ H5包部署 ============
if [ -f /opt/confApp.zip ]; then
    echo "步骤5: 开始更新H5包..."
    
    # 解压H5包
    unzip -o /opt/confApp.zip -d "${UPBAKDIR}/${DATE}/up/H5/" 2>/dev/null || true
    rm -f /opt/confApp.zip
    
    # 停止服务
    echo "停止相关服务..."
    if systemctl list-units --full -all | grep -Fq "$TOMCAT_SERVICE_NAME.service"; then
        systemctl stop "$TOMCAT_SERVICE_NAME" || true
    fi
    
    sleep 5
    
    # 检查tomcat进程是否还在运行
    if ps aux | grep -v grep | grep -q tomcat; then
        pkill -9 -f tomcat || true
        sleep 2
    fi
    
    # 备份当前版本
    echo "备份当前版本..."
    if [ -d "${TOMCATDIR}/webapps/confApp" ]; then
        mv "${TOMCATDIR}/webapps/confApp" "${UPBAKDIR}/${DATE}/bak/H5/"
    fi
    
    # 部署新版本
    echo "部署新版本..."
    if [ -d "${UPBAKDIR}/${DATE}/up/H5/confApp" ]; then
        cp -r "${UPBAKDIR}/${DATE}/up/H5/confApp" "${TOMCATDIR}/webapps/"
    fi
    
    # 清理缓存
    rm -rf "${TOMCATDIR}/work/Catalina/" 2>/dev/null || true
    
    # 启动服务
    echo "启动服务..."
    if systemctl list-units --full -all | grep -Fq "$TOMCAT_SERVICE_NAME.service"; then
        systemctl start "$TOMCAT_SERVICE_NAME"
    else
        if [ -f "${TOMCATDIR}/bin/startup.sh" ]; then
            "${TOMCATDIR}/bin/startup.sh"
        fi
    fi
    
    echo "H5包更新完成！"
else
    echo "信息: 未找到H5包(confApp.zip)，跳过此步骤"
fi

# ============ 服务验证 ============
echo "步骤6: 验证服务状态..."
sleep 10

# 验证Java服务
echo "验证Java服务(端口: {java_port})..."
if command -v curl &> /dev/null; then
    JAVA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:{java_port}/pcms" --connect-timeout 10 || echo "000")
    if [ "$JAVA_STATUS" = "200" ] || [ "$JAVA_STATUS" = "302" ]; then
        echo "✓ Java服务运行正常 (HTTP状态码: $JAVA_STATUS)"
    else
        echo "✗ Java服务异常 (HTTP状态码: $JAVA_STATUS)"
        # 尝试查看tomcat日志
        if [ -f "${TOMCATDIR}/logs/catalina.out" ]; then
            echo "查看Tomcat日志最后10行:"
            tail -10 "${TOMCATDIR}/logs/catalina.out"
        fi
    fi
else
    echo "警告: curl命令未找到，跳过HTTP验证"
    # 使用netstat检查端口
    if command -v netstat &> /dev/null; then
        if netstat -tlnp | grep -q ":{java_port}"; then
            echo "✓ Java端口 {java_port} 正在监听"
        else
            echo "✗ Java端口 {java_port} 未监听"
        fi
    fi
fi

# 验证C++服务
echo "验证C++服务(端口: {cpp_port})..."
if command -v nc &> /dev/null; then
    if nc -z localhost "{cpp_port}" &> /dev/null; then
        echo "✓ C++服务端口 {cpp_port} 可连接"
    else
        echo "✗ C++服务端口 {cpp_port} 不可连接"
    fi
elif command -v telnet &> /dev/null; then
    # 尝试telnet
    timeout 5 bash -c "echo > /dev/tcp/localhost/{cpp_port}" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ C++服务端口 {cpp_port} 可连接"
    else
        echo "✗ C++服务端口 {cpp_port} 不可连接"
    fi
else
    echo "警告: 未找到端口检测工具，跳过C++服务验证"
fi

echo ""
echo "========================================="
echo "部署完成！"
echo "备份文件保存在: ${UPBAKDIR}/${DATE}/"
echo "部署时间: $(date)"
echo "========================================="

# 清理临时文件
echo "清理临时文件..."
rm -f /opt/pcms.war 2>/dev/null || true
rm -f /opt/pcms.zip 2>/dev/null || true
rm -f /opt/confApp.zip 2>/dev/null || true
rm -f /opt/pcms 2>/dev/null || true
rm -f /opt/pcmsLog.war 2>/dev/null || true
rm -f /opt/pcmsLog.zip 2>/dev/null || true

echo "所有部署任务完成！"
"""


def get_default_script_for_project(project):
    """
    根据项目配置生成默认部署脚本
    """
    # 获取项目的第一个服务器配置（如果有的话）
    try:
        server = project.servers.first()
        if server:
            # 使用服务器的配置
            script = DEFAULT_UPDATE_SCRIPT.format(
                backup_path=server.backup_path,
                cpp_install_path=server.cpp_install_path,
                java_install_path=server.java_install_path,
                java_port=server.java_port,
                cpp_port=server.cpp_port
            )
        else:
            # 使用默认配置
            script = DEFAULT_UPDATE_SCRIPT.format(
                backup_path='/opt/upbak',
                cpp_install_path='/usr/local/PCMS/PCMS',
                java_install_path='/usr/local/PCMS/tomcat',
                java_port=80,
                cpp_port=8500
            )
    except Exception as e:
        print(f"获取项目 {project.name} 配置时出错: {e}")
        # 使用默认配置
        script = DEFAULT_UPDATE_SCRIPT.format(
            backup_path='/opt/upbak',
            cpp_install_path='/usr/local/PCMS/PCMS',
            java_install_path='/usr/local/PCMS/tomcat',
            java_port=80,
            cpp_port=8500
        )
    
    return script


def create_default_scripts():
    """为所有项目创建默认部署脚本"""
    print("开始为项目创建默认部署脚本...")
    
    # 获取管理员用户
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()
            print(f"警告: 未找到超级用户，使用第一个用户: {admin_user}")
    except Exception as e:
        print(f"获取用户时出错: {e}")
        admin_user = None
    
    projects = Project.objects.all()
    
    created_count = 0
    updated_count = 0
    
    for project in projects:
        print(f"处理项目: {project.name} (ID: {project.id})")
        
        try:
            # 检查是否已有部署脚本
            if hasattr(project, 'deployment_script'):
                script = project.deployment_script
                print(f"  项目已有部署脚本，版本: {script.version}")
                
                # 询问是否更新
                update = input(f"  是否更新项目 '{project.name}' 的部署脚本？(y/N): ").strip().lower()
                if update == 'y':
                    new_script = get_default_script_for_project(project)
                    script.content = new_script
                    script.version = f"{float(script.version) + 0.1:.1f}"
                    script.updated_at = django.utils.timezone.now()
                    script.save()
                    updated_count += 1
                    print(f"  已更新部署脚本到版本 {script.version}")
            else:
                # 创建新的部署脚本
                new_script = get_default_script_for_project(project)
                
                DeploymentScript.objects.create(
                    project=project,
                    name='update.sh',
                    content=new_script,
                    version='1.0',
                    is_active=True,
                    created_by=admin_user
                )
                created_count += 1
                print(f"  已创建默认部署脚本")
                
        except Exception as e:
            print(f"  处理项目 {project.name} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n脚本创建完成！")
    print(f"新创建脚本: {created_count} 个")
    print(f"更新脚本: {updated_count} 个")
    print(f"总处理项目: {projects.count()} 个")


def list_projects():
    """列出所有项目及其部署脚本状态"""
    print("项目列表:")
    print("-" * 80)
    print(f"{'ID':<5} {'项目名称':<20} {'项目代号':<15} {'部署脚本':<10} {'版本':<10}")
    print("-" * 80)
    
    projects = Project.objects.all().order_by('id')
    
    for project in projects:
        has_script = hasattr(project, 'deployment_script')
        script_version = project.deployment_script.version if has_script else '无'
        
        print(f"{project.id:<5} {project.name:<20} {project.code:<15} "
              f"{'有':<10} {script_version:<10}" if has_script else
              f"{project.id:<5} {project.name:<20} {project.code:<15} "
              f"{'无':<10} {'-':<10}")
    
    print("-" * 80)
    print(f"总计: {projects.count()} 个项目")


def main():
    """主函数"""
    print("=" * 60)
    print("部署模块初始化脚本")
    print("=" * 60)
    print(f"项目路径: {project_path}")
    print(f"Django设置: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print()
    
    while True:
        print("\n请选择操作:")
        print("1. 列出所有项目")
        print("2. 为所有项目创建/更新部署脚本")
        print("3. 为指定项目创建部署脚本")
        print("4. 查看脚本模板")
        print("5. 退出")
        
        choice = input("请输入选项 (1-5): ").strip()
        
        if choice == '1':
            list_projects()
        
        elif choice == '2':
            confirm = input("确定要为所有项目创建/更新部署脚本吗？(y/N): ").strip().lower()
            if confirm == 'y':
                create_default_scripts()
            else:
                print("操作取消")
        
        elif choice == '3':
            list_projects()
            try:
                project_id = input("请输入项目ID: ").strip()
                project = Project.objects.get(id=int(project_id))
                
                # 获取管理员用户
                admin_user = User.objects.filter(is_superuser=True).first()
                
                if hasattr(project, 'deployment_script'):
                    print(f"项目 '{project.name}' 已有部署脚本")
                    update = input("是否更新？(y/N): ").strip().lower()
                    if update == 'y':
                        new_script = get_default_script_for_project(project)
                        script = project.deployment_script
                        script.content = new_script
                        script.version = f"{float(script.version) + 0.1:.1f}"
                        script.save()
                        print(f"已更新部署脚本到版本 {script.version}")
                else:
                    new_script = get_default_script_for_project(project)
                    DeploymentScript.objects.create(
                        project=project,
                        name='update.sh',
                        content=new_script,
                        version='1.0',
                        is_active=True,
                        created_by=admin_user
                    )
                    print(f"已为项目 '{project.name}' 创建部署脚本")
                    
            except ValueError:
                print("错误: 请输入有效的数字ID")
            except Project.DoesNotExist:
                print(f"错误: 未找到ID为 {project_id} 的项目")
            except Exception as e:
                print(f"错误: {e}")
        
        elif choice == '4':
            print("\n脚本模板预览 (前50行):")
            print("=" * 60)
            lines = DEFAULT_UPDATE_SCRIPT.split('\n')[:50]
            for i, line in enumerate(lines, 1):
                print(f"{i:3}: {line}")
            print("... (完整脚本内容请查看源码)")
        
        elif choice == '5':
            print("退出脚本")
            break
        
        else:
            print("无效选项，请重新选择")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"运行出错: {e}")
        import traceback
        traceback.print_exc()
