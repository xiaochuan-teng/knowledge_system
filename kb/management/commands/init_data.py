from django.core.management.base import BaseCommand
from kb.models import CustomUser, Article, HostMachine, VirtualMachine
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = '初始化测试数据'

    def handle(self, *args, **options):
        # 创建测试用户
        if not CustomUser.objects.filter(username='testuser').exists():
            user = CustomUser.objects.create(
                username='testuser',
                password=make_password('Test123!'),
                email='test@example.com',
                role='user',
                department='交付部'
            )
            self.stdout.write(self.style.SUCCESS(f'创建测试用户: {user.username}'))

        # 创建测试宿主机
        if not HostMachine.objects.exists():
            host = HostMachine.objects.create(
                name='宿主机-01',
                ip_address='192.168.1.10',
                location='机房A-机架1',
                description='主要开发环境宿主机'
            )
            self.stdout.write(self.style.SUCCESS(f'创建宿主机: {host.name}'))

        self.stdout.write(self.style.SUCCESS('数据初始化完成'))