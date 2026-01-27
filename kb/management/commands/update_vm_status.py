# kb/management/commands/update_vm_status.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from kb.models import HostMachine, VirtualMachine
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '更新所有宿主机上虚拟机的运行状态'

    def handle(self, *args, **kwargs):
        self.stdout.write(f"{timezone.now()}: 开始更新虚拟机状态...")
        
        total_updated_count = 0
        total_new_vm_count = 0  # 新增虚拟机计数器
        total_error_count = 0
        
        # 获取所有宿主机
        host_machines = HostMachine.objects.all()
        
        for host in host_machines:
            host_updated_count = 0
            host_new_vm_count = 0
            host_error_count = 0
            
            try:
                self.stdout.write(f"正在连接宿主机: {host.name} ({host.ip_address})")
                
                # 更新宿主机状态
                try:
                    # 尝试连接宿主机
                    si = self.connect_to_host(host)
                    
                    # 连接成功，更新宿主机状态为正常
                    if host.status != 'normal':
                        host.status = 'normal'
                        self.stdout.write(f"  宿主机 {host.name} 连接成功，状态: {host.status} -> normal")
                    
                    # 更新最后检查时间
                    host.last_check_time = timezone.now()
                    host.save()
                    
                    # 更新该宿主机上的所有虚拟机状态
                    updated_count, new_vm_count = self.update_vms_for_host(host, si)
                    host_updated_count = updated_count
                    host_new_vm_count = new_vm_count
                    
                    # 断开连接
                    Disconnect(si)
                    
                except Exception as e:
                    # 连接失败，设置宿主机状态为故障
                    if host.status != 'fault':
                        old_status = host.status
                        host.status = 'fault'
                        self.stdout.write(f"  宿主机 {host.name} 连接失败，状态: {old_status} -> fault")
                    
                    # 更新最后检查时间
                    host.last_check_time = timezone.now()
                    host.save()
                    
                    # 连接失败，将该宿主机下所有虚拟机状态设置为故障
                    fault_vms = self.set_all_vms_to_fault(host)
                    host_updated_count = fault_vms
                    host_error_count = 1
                    
                    logger.error(f"宿主机 {host.name} 连接失败: {e}")
                    self.stdout.write(self.style.WARNING(f"  宿主机 {host.name} 连接失败: {e}"))
                
                total_updated_count += host_updated_count
                total_new_vm_count += host_new_vm_count
                
                # 输出本次处理结果
                if host_new_vm_count > 0:
                    self.stdout.write(self.style.SUCCESS(f"  宿主机 {host.name}: 新增 {host_new_vm_count} 台虚拟机"))
                
            except Exception as e:
                total_error_count += 1
                logger.error(f"处理宿主机 {host.name} 时发生严重错误: {e}")
                self.stdout.write(self.style.ERROR(f"处理宿主机 {host.name} 时发生严重错误: {e}"))
        
        self.stdout.write(
            self.style.SUCCESS(
                f"虚拟机状态更新完成！成功更新: {total_updated_count} 台虚拟机，新增: {total_new_vm_count} 台虚拟机，失败: {total_error_count} 台主机"
            )
        )

    def connect_to_host(self, host):
        """连接到 ESXi/vCenter 主机"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        port = int(host.port) if host.port else 443
        
        si = SmartConnect(
            host=host.ip_address,
            user=host.username,
            pwd=host.password,
            port=port,
            sslContext=context
        )
        
        return si

    def get_vms_from_host(self, si):
        """从宿主机获取虚拟机列表"""
        content = si.RetrieveContent()
        
        container_view = content.viewManager.CreateContainerView(
            container=content.rootFolder,
            type=[vim.VirtualMachine],
            recursive=True
        )
        
        vms = container_view.view
        container_view.Destroy()
        
        return vms

    def map_vmware_status_to_local(self, vmware_status):
        """将 VMware 状态映射到本地状态"""
        status_mapping = {
            'poweredOn': 'running',
            'poweredOff': 'stopped',
            'suspended': 'stopped',  # 暂停状态也视为停止
            'poweringOn': 'running',
            'poweringOff': 'stopped',
        }
        return status_mapping.get(vmware_status, 'maintenance')

    def set_all_vms_to_fault(self, host):
        """将宿主机下所有虚拟机设置为故障状态"""
        vms = VirtualMachine.objects.filter(host_machine=host)
        updated_count = 0
        
        for vm in vms:
            if vm.status != 'fault':
                old_status = vm.status
                vm.status = 'fault'
                vm.updated_at = timezone.now()
                vm.save()
                
                self.stdout.write(
                    f"    虚拟机 {vm.name} 因宿主机连接失败，状态: {old_status} -> fault"
                )
                
                logger.info(
                    f"虚拟机状态更新: {vm.name} 因宿主机连接失败，状态从 {old_status} 改为 fault"
                )
                updated_count += 1
            else:
                # 如果已经是故障状态，只更新时间戳
                vm.updated_at = timezone.now()
                vm.save()
        
        return updated_count

    def update_vms_for_host(self, host, si):
        """更新指定宿主机上的虚拟机状态"""
        updated_count = 0
        new_vm_count = 0
        
        try:
            # 获取所有虚拟机
            vms = self.get_vms_from_host(si)
            
            self.stdout.write(f"在宿主机 {host.name} 上找到 {len(vms)} 台虚拟机")
            
            # 获取数据库中该宿主机的所有虚拟机
            db_vms = VirtualMachine.objects.filter(host_machine=host)
            
            # 创建宿主机上虚拟机名称的集合，用于快速查找
            host_vm_names = {vm.name for vm in vms}
            
            # 更新宿主机上存在的虚拟机
            for vm in vms:
                try:
                    # 查找数据库中是否已存在该虚拟机
                    try:
                        db_vm = VirtualMachine.objects.get(
                            name=vm.name,
                            host_machine=host
                        )
                        # 如果存在，更新状态
                        self.update_single_vm(vm, host)
                        updated_count += 1
                    except VirtualMachine.DoesNotExist:
                        # 如果不存在，创建新的虚拟机记录
                        self.create_virtual_machine(vm, host)
                        new_vm_count += 1
                        self.stdout.write(f"  新增虚拟机: {vm.name} (宿主机: {host.name})")
                        
                except Exception as e:
                    logger.warning(f"处理虚拟机 {vm.name} 时发生错误: {e}")
            
            # 处理宿主机上不存在的虚拟机（设置为故障状态）
            for db_vm in db_vms:
                if db_vm.name not in host_vm_names:
                    # 检查当前状态是否已经是故障，避免不必要的更新
                    if db_vm.status != 'fault':
                        old_status = db_vm.status
                        db_vm.status = 'fault'
                        db_vm.updated_at = timezone.now()
                        db_vm.save()
                        
                        self.stdout.write(
                            f"  虚拟机 {db_vm.name} 在宿主机上不存在，状态: {old_status} -> fault"
                        )
                        
                        logger.info(
                            f"虚拟机状态更新: {db_vm.name} 在宿主机上不存在，状态从 {old_status} 改为 fault"
                        )
                        updated_count += 1
                    else:
                        # 如果已经是故障状态，只更新时间戳
                        db_vm.updated_at = timezone.now()
                        db_vm.save()
                        self.stdout.write(
                            f"  虚拟机 {db_vm.name} 在宿主机上不存在，保持故障状态"
                        )
            
            # 输出新增虚拟机统计
            if new_vm_count > 0:
                self.stdout.write(f"  新增了 {new_vm_count} 台虚拟机到数据库")
                
        except Exception as e:
            logger.error(f"处理宿主机 {host.name} 时发生错误: {e}")
            raise
        
        return updated_count, new_vm_count

    def update_single_vm(self, vmware_vm, host):
        """更新单个虚拟机的状态"""
        # 查找对应的数据库记录
        try:
            db_vm = VirtualMachine.objects.get(
                name=vmware_vm.name,
                host_machine=host
            )
        except VirtualMachine.DoesNotExist:
            # 虚拟机在 VMware 中存在但在数据库中不存在，已经在上面的流程中处理
            return
        except VirtualMachine.MultipleObjectsReturned:
            # 如果有多个同名虚拟机，取第一个
            db_vm = VirtualMachine.objects.filter(
                name=vmware_vm.name,
                host_machine=host
            ).first()
        
        # 获取 VMware 状态并映射
        vmware_status = vmware_vm.runtime.powerState
        local_status = self.map_vmware_status_to_local(vmware_status)
        
        # 获取 IP 地址（如果可用）
        ip_address = vmware_vm.guest.ipAddress if vmware_vm.guest else None
        
        # 记录是否需要更新
        needs_update = False
        
        # 检查状态是否变化
        if db_vm.status != local_status:
            old_status = db_vm.status
            db_vm.status = local_status
            needs_update = True
            
            self.stdout.write(
                f"  更新虚拟机: {db_vm.name} 状态: {old_status} -> {local_status}"
            )
            
            # 记录日志
            logger.info(
                f"虚拟机状态更新: {db_vm.name} ({db_vm.ip_address}) "
                f"状态从 {old_status} 改为 {local_status}"
            )
        
        # 检查 IP 地址是否变化（如果提供了新的 IP 地址）
        if ip_address and db_vm.ip_address != ip_address:
            old_ip = db_vm.ip_address
            db_vm.ip_address = ip_address
            needs_update = True
            
            self.stdout.write(
                f"  更新虚拟机: {db_vm.name} IP: {old_ip} -> {ip_address}"
            )
            
            logger.info(
                f"虚拟机IP更新: {db_vm.name} IP从 {old_ip} 改为 {ip_address}"
            )
        
        # 更新更新时间戳（无论是否有状态变化，都记录这次检查）
        db_vm.updated_at = timezone.now()
        needs_update = True
        
        # 如果有任何变化，保存
        if needs_update:
            db_vm.save()

    def create_virtual_machine(self, vmware_vm, host):
        """
        创建新的虚拟机记录
        根据VMware虚拟机信息创建数据库记录
        """
        # 映射VMware状态到本地状态
        vmware_status = vmware_vm.runtime.powerState
        local_status = self.map_vmware_status_to_local(vmware_status)
        
        # 获取IP地址（如果可用）
        ip_address = vmware_vm.guest.ipAddress if vmware_vm.guest else ""
        
        # 尝试获取虚拟机配置信息
        config = vmware_vm.config
        hardware = config.hardware if config else None
        
        # 获取CPU、内存信息
        cpu_info = ""
        memory_info = ""
        
        if hardware:
            # CPU信息
            num_cpu = hardware.numCPU
            cpu_mhz = hardware.numCoresPerSocket * hardware.cpuMhz if hasattr(hardware, 'cpuMhz') else ""
            cpu_info = f"{num_cpu}核"
            if cpu_mhz:
                cpu_info += f" {cpu_mhz/1000:.1f}GHz"
            
            # 内存信息（转换为GB）
            memory_mb = hardware.memoryMB
            if memory_mb >= 1024:
                memory_info = f"{memory_mb/1024:.1f}GB"
            else:
                memory_info = f"{memory_mb}MB"
        
        # 获取磁盘信息
        disk_info = ""
        if hasattr(vmware_vm, 'layout') and vmware_vm.layout and hasattr(vmware_vm.layout, 'disk'):
            disk_count = len(vmware_vm.layout.disk)
            if disk_count > 0:
                disk_info = f"{disk_count}个磁盘"

        # 获取东八区时间（北京时间）
        import pytz
        from django.utils import timezone
        # 创建东八区时区对象
        beijing_tz = pytz.timezone('Asia/Shanghai')
        # 获取当前UTC时间并转换为北京时间
        utc_now = timezone.now()
        beijing_now = utc_now.astimezone(beijing_tz)       
 
        # 创建虚拟机记录
        vm = VirtualMachine.objects.create(
            name=vmware_vm.name,
            ip_address=ip_address,
            host_machine=host,
            owner=None,  # 责任人设为空，后续可以手动分配
            cpu=cpu_info,
            memory=memory_info,
            disk=disk_info,
            os='other',  # 默认为"其他"操作系统
            os_version='',  # 系统版本为空
            status=local_status,
            purpose='从VMware自动发现并添加',
            notes=f'自动发现时间: {beijing_now.strftime("%Y-%m-%d %H:%M:%S")} (北京时间)',
        )
        
        # 记录日志
        logger.info(
            f"自动创建虚拟机: {vm.name} ({vm.ip_address}) "
            f"宿主机: {host.name}, 状态: {vm.status}"
        )
        
        return vm
