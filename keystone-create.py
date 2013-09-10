#!/usr/bin/env python

from keystoneclient.exceptions import ClientException
from keystoneclient.v2_0 import client as keyston_cl
from novaclient.v1_1 import client as nova_cl
import logging
import argparse
from ConfigParser import SafeConfigParser
import sys

argument_parser = argparse.ArgumentParser(description='Tool to quickly create keystone users and respective credentials.')
argument_parser.add_argument('-u','--user', help='Desired username', required=True)
argument_parser.add_argument('-p','--password', help='Desired pasword', required=True)
argument_parser.add_argument('-t','--tenant', help='Tenant for new user. If it does not exist, it will be created.', required=True)
argument_parser.add_argument('-e','--email', help='Contact email for new user.', required=True)
argument_parser.add_argument('-r','--role', help='Desired role for new user. If not specified, defaults to Member.', default="Member", required=False)
args = vars(argument_parser.parse_args())

config_parser = SafeConfigParser()
config_parser.read('config.ini')

username = config_parser.get('credentials', 'username')
password = config_parser.get('credentials', 'password')
tenant = config_parser.get('credentials', 'tenant')
ec2_url = config_parser.get('credentials', 'ec2_url')
os_tenant_name = config_parser.get('credentials', 'os_tenant_name')
os_username = config_parser.get('credentials', 'os_username')
os_password = config_parser.get('credentials', 'os_password')
os_auth_url = config_parser.get('credentials', 'os_auth_url')

#keystone client to create creds
keystone = keyston_cl.Client(username=username,
                             password=password,
                             tenant_name=tenant,
                             auth_url=os_auth_url)

#nova client to update quota to jds "standard"
nova = nova_cl.Client(username, password, tenant, os_auth_url)

new_tenant=args['tenant']
new_user=args['user']
new_password=args['password']
new_email=args['email']
new_role=args['role']

tenant_map = {}
user_map = {}
roles_map = {}

# build tenant id-name mapping
for tenant in keystone.tenants.list():
	tenant_map[tenant.name] = tenant.id

#check for existing tenant name
#replaced try-except with if statement so as not to rebuild tenant-id map
#every time even if tenant already exists
if new_tenant not in tenant_map:
    keystone.tenants.create(new_tenant)	
    # rebuild tenant map
    for tenant in keystone.tenants.list():
	    tenant_map[tenant.name] = tenant.id
	    
new_tenant_id = tenant_map[new_tenant]

# build user id-name mapping, is this necessary?
#for user in keystone.users.list():
#	user_map[user.name] = user.id
#"no handler could be found for logger" workaround
logging.disable(50)

try:
	keystone.users.create(name=new_user,
	                      password=new_password,
	                      email=new_email,
	                      tenant_id=new_tenant_id)
except	ClientException:
	print "That user already exists!"
	sys.exit(1)

#rebuild user mapping
for user in keystone.users.list():
	user_map[user.name] = user.id

new_user_id = user_map[new_user]

#build role id-name mapping
for role in keystone.roles.list():
	roles_map[role.name] = role.id

#replaced with if statement for same reason as above
if new_role not in roles_map:
	keystone.roles.create(new_role)
	for role in keystone.roles.list():
		roles_map[role.name] = role.id

new_role_id = roles_map[new_role]

keystone.roles.add_user_role(user=new_user_id,
                             role=new_role_id,
                             tenant=new_tenant_id)

keystone.ec2.create(user_id=new_user_id, tenant_id=new_tenant_id)

ec2 = keystone.ec2.list(new_user_id)
for i in ec2:
	print "export EC2_URL="+ec2_url
	print "export EC2_ACCESS_KEY="+i.access
	print "export EC2_SECRET_KEY="+i.secret
	print "export OS_AUTH_URL="+os_auth_url
	print "export OS_TENANT_NAME="+new_tenant
	print "export OS_USERNAME="+new_user
	print "export OS_PASSWORD="+new_password

#quota settings
nova.quotas.update(new_tenant_id, ram = 35000, floating_ips = 20, cores = 20)
tenant_quota = nova.quotas.get(new_tenant_id)
quota_dict = vars(tenant_quota)

for item in quota_dict:
	if (type(quota_dict[item]) == int) & (quota_dict[item] != -1):
		print item, quota_dict[item]

