#!/usr/bin/env python

from keystoneclient.exceptions import ClientException
from keystoneclient.v2_0 import client
import logging
import argparse
from ConfigParser import SafeConfigParser
import sys

argument_parser  = argparse.ArgumentParser(description='Tool to quickly create keystone users and respective credentials.')
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
auth_url = config_parser.get('credentials', 'auth_url')
ec2_url = config_parser.get('credentials', 'ec2_url')


keystone = client.Client(username=username, password=password, tenant_name=tenant, auth_url=auth_url)




new_tenant=args['tenant']
new_user=args['user']
new_password=args['password']
new_email=args['email']
#new_role="Member"
new_role=args['role']

r = {}

# build tenant id-name mapping
for tenant in keystone.tenants.list():
	r[tenant.name] = tenant.id

#check for existing tenant name
try:
	r[new_tenant]
except KeyError:
	keystone.tenants.create(new_tenant)	


# rebuild tenant map
for tenant in keystone.tenants.list():
	r[tenant.name] = tenant.id 


new_tenant_id = r[new_tenant]

# build user id-name mapping
for user in keystone.users.list():
	r[user.name] = user.id
#"no handler could be found for logger" workaround
logging.disable(50)
try:
	keystone.users.create(name=new_user, password=new_password, email=new_email, tenant_id=new_tenant_id)
except	ClientException:
	print "That user already exists!"
	sys.exit(1)

#rebuild user mapping
for user in keystone.users.list():
	r[user.name] = user.id

new_user_id = r[new_user]

#build role id-name mapping
for role in keystone.roles.list():
	r[role.name] = role.id


#check for existing role name
try:
        r[new_role]
except KeyError:
        keystone.roles.create(new_role)

# rebuild role map
for role in keystone.roles.list():
        r[role.name] = role.id

new_role_id = r[new_role]

keystone.roles.add_user_role(user=new_user_id, role=new_role_id, tenant=new_tenant_id)

keystone.ec2.create(user_id=new_user_id, tenant_id=new_tenant_id)

ec2 = keystone.ec2.list(new_user_id)

for i in ec2:
	print "export EC2_URL=",ec2_url
	print "export EC2_ACCESS_KEY=",i.access
	print "export EC2_SECRET_KEY=",i.secret
