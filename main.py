'''
#################################################################################################################################################################
# This script was created to make easier the migration process between an ACI+Openstack setup integrated with legacy ML2 plugin, 
# and the new ML2 in unified mode.
#
# This script gathers a list of OS projects and other elements and saves its corresponding ACI objects, with the following highlines:
#
# -Each OS project is saved in a separate XML file, with the name of the project
# -Each project's router is represented as an ACI contract in tenant common
# -The external networks in OS, are represented as a combination of EPGs + Contracts in ACI, in tenant common
# -The two types of elements above will be kept in a seàrate file dedicatd to tenant common, only keeping these objects.
###########################################################################################################################################################
'''
#IMPORTS

import os;
import requests;
import json;
import datetime;
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


#GLOBAL VARIABLES
list_all_tenants_cfg=[]


#VARIABLES

APIC_URL="https://10.50.2.59"
APIC_LOGIN_JSON='{"aaaUser":{"attributes":{"name":"admin","pwd":"C1sc0123"}}}'

#
BASE_URL="http://controller:5000/v3"
#REMEMBER TO ADD THE LEADING AND TRAILING UNDERSCORE "_" TO THE VMM DOMAIN NAME BELOW. THIS IS ADDED BY THE ML2 LEGACY PLUGIN
OS_VMM_DOMAIN="_pmathame-ML2_"
AUTH_KEYSTONE_JSON="""
{
    "auth": {
        "identity": {
            "methods": [
                "password"
            ],
            "password": {
                "user": {
                	"domain": {
                    "id": "default"
                },
                    "name": "admin",
                    "password": "C1sc0123."
                }
            }
        },
        "scope": {
            "project": {
                "domain": {
                    "id": "default"
                },
                "name": "admin"
            }
        }
    }
}
"""



#This function retrieves a OS authentication token from keystone and returns it.

def os_get_authtoken():
    try:
        return requests.post(BASE_URL+"/auth/tokens", data=None, json=json.loads(AUTH_KEYSTONE_JSON)).headers.get(
        "x-subject-token")
    except:
        print ("Error retrieving authentication token")
        exit(1)


def os_get_project_list(auth_token):
    try:
        return requests.get(BASE_URL+"/projects", headers={"X-Auth-Token":auth_token}).json()
    except:
        print("Error retrieving project list")
        exit(1)


def APIC_get_authtoken():
    try:
        return requests.post(APIC_URL+"/api/aaaLogin.json", verify=False, data=APIC_LOGIN_JSON).cookies.items()[0][1]
    except:
        print("Error login into APIC")
        exit(1)

def APIC_save_tenant(tenant_name,APIC_token):
    global list_all_tenants_cfg
    try:

        get_tenant_URL=APIC_URL+"/api/mo/uni/tn-"+tenant_name+".json?rsp-subtree=full&rsp-prop-include=config-only"
        tmp=json.loads(requests.get(get_tenant_URL, verify=False, cookies={"APIC-cookie":APIC_token}).content)
        if tmp['totalCount']!='0':
            if tenant_name!='common':
                txt=tmp["imdata"][0]
                list_all_tenants_cfg.append(txt)
            file = open("tn-"+tenant_name + ".json", "w")
            json.dump(tmp, file, sort_keys=True, indent=4)
            file.close()
            print ("Saving tenant "+tenant_name+" in "+os.getcwd())
        else:
            print ("WARNING: Tenant "+tenant_name+" not found in the APIC")
    except:
        print("Error saving tenants from APIC")
        exit(1)

def APIC_delete_old_cfg():
    print("WIP")


def main():

    global list_all_tenants_cfg
    time_str = datetime.datetime.strptime(str(datetime.datetime.now()),"%Y-%m-%d %H:%M:%S.%f")
    new_dir=time_str.strftime("%Y")+time_str.strftime("%m")+time_str.strftime("%d")+'_'+time_str.strftime("%H")+time_str.strftime("%M")+time_str.strftime("%S")
    os.mkdir(new_dir)
    os.chdir(new_dir)
    token=APIC_get_authtoken()
    # SAVE OS TENANTS
    for i in os_get_project_list(os_get_authtoken())["projects"]:
        APIC_save_tenant(OS_VMM_DOMAIN+i['id'],token)
    # SAVE COMMON TENANT
    APIC_save_tenant("common",token)
    # SAVE ALL TENANT'S CONFIG IN A SINGLE FILE
    all_tenants_cfg={"polUni":{"attributes":{"dn":"uni"},"children":[]}}
    all_tenants_cfg["polUni"]["children"]=list_all_tenants_cfg
    file = open("all_os_tenants.json", "w")
    json.dump(all_tenants_cfg, file, sort_keys=True, indent=4)
    file.close()



main()
