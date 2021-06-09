# Generated by Django 3.1 on 2020-08-09 02:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(default='Stop', max_length=255)),
                ('status', models.CharField(default='Active', max_length=255)),
                ('idstr', models.CharField(default='0', max_length=255)),
            ],
            options={
                'db_table': 'Server',
            },
        ),
        migrations.CreateModel(
            name='ServerType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'ServerType',
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.CharField(max_length=255)),
                ('start_date', models.DateTimeField(null=True)),
                ('end_date', models.DateTimeField(null=True)),
                ('term_subscription', models.CharField(max_length=255)),
                ('service_type', models.CharField(default='Ipg', max_length=255)),
                ('subscription', models.CharField(max_length=255)),
                ('server_name_prefix', models.CharField(max_length=255)),
                ('package', models.CharField(max_length=255)),
                ('trunk_service_provider', models.CharField(max_length=255)),
                ('extra_call_record_package', models.CharField(max_length=255)),
                ('demo', models.CharField(max_length=255)),
                ('extra_duration_package', models.CharField(max_length=255)),
                ('exp20_dss_module_ip1141', models.CharField(default='0', max_length=255)),
                ('exp40_dss_module_ip136_ip138', models.CharField(default='0', max_length=255)),
                ('ip1111_poe_no_adapter', models.CharField(default='0', max_length=255)),
                ('ip1131_poe_gigabit_no_adapter', models.CharField(default='0', max_length=255)),
                ('ip1141_poe_no_adapter', models.CharField(default='0', max_length=255)),
                ('ip1141_ip131_ip132_adapter', models.CharField(default='0', max_length=255)),
                ('ip1181_ip136_ip138_adapter', models.CharField(default='0', max_length=255)),
                ('ip1211_w_adapter', models.CharField(default='0', max_length=255)),
                ('ip1211_poe_no_adapter', models.CharField(default='0', max_length=255)),
                ('ip1211_ip1211p_ip1111_ip1131_adapter', models.CharField(default='0', max_length=255)),
                ('ip131_poe_no_adapter', models.CharField(default='0', max_length=255)),
                ('ip132_gigabit_no_adapter', models.CharField(default='0', max_length=255)),
                ('ip136_poe_no_adapter', models.CharField(default='0', max_length=255)),
                ('ip138_poe_no_adapter', models.CharField(default='0', max_length=255)),
                ('karel_mobile', models.CharField(default='0', max_length=255)),
                ('vp128', models.CharField(default='0', max_length=255)),
                ('yt510', models.CharField(default='0', max_length=255)),
                ('yt520', models.CharField(default='0', max_length=255)),
                ('yt530', models.CharField(default='0', max_length=255)),
                ('state', models.CharField(default='Not Initialized ', max_length=255, null=True)),
            ],
            options={
                'db_table': 'subscription',
            },
        ),
        migrations.CreateModel(
            name='WebcmServer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=255, null=True)),
                ('local_ip', models.CharField(max_length=255, null=True)),
                ('internal_ip', models.CharField(max_length=255, null=True)),
                ('server_name', models.CharField(max_length=255, null=True)),
                ('state', models.IntegerField(default=1, null=True)),
                ('fqdn', models.CharField(max_length=255, null=True)),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cloud.server')),
            ],
            options={
                'db_table': 'WebcmServer',
            },
        ),
        migrations.AddField(
            model_name='server',
            name='server_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cloud.servertype'),
        ),
        migrations.AddField(
            model_name='server',
            name='subscription',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cloud.subscription'),
        ),
        migrations.CreateModel(
            name='IpgServer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cpu', models.CharField(max_length=255, null=True)),
                ('ram', models.CharField(max_length=255, null=True)),
                ('disc', models.CharField(max_length=255, null=True)),
                ('widea_address', models.CharField(max_length=255, null=True)),
                ('local_ip', models.CharField(max_length=255, null=True)),
                ('internal_ip', models.CharField(max_length=255, null=True)),
                ('external_ip', models.CharField(max_length=255, null=True)),
                ('server_name', models.CharField(max_length=255, null=True)),
                ('state', models.IntegerField(default=1, null=True)),
                ('fqdn', models.CharField(max_length=255, null=True)),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cloud.server')),
            ],
            options={
                'db_table': 'IpgServer',
            },
        ),
    ]