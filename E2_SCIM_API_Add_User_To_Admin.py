# Databricks notebook source
import json, os, datetime, requests
import requests.packages.urllib3

global pprint_j

requests.packages.urllib3.disable_warnings()


# Helper to pretty print json
def pprint_j(i):
    print(json.dumps(i, indent=4, sort_keys=True))


class dbclient:
    """
    Rest API Wrapper for Databricks APIs
    """
    # set of http error codes to throw an exception if hit. Handles client and auth errors
    http_error_codes = (401, 403)

    def __init__(self, token, url):
        self._token = {'Authorization': 'Bearer {0}'.format(token)}
        self._url = url.rstrip("/")
        self._is_verbose = False
        self._verify_ssl = False
        if self._verify_ssl:
            # set these env variables if skip SSL verification is enabled
            os.environ['REQUESTS_CA_BUNDLE'] = ""
            os.environ['CURL_CA_BUNDLE'] = ""

    def is_aws(self):
        return self._is_aws

    def is_verbose(self):
        return self._is_verbose

    def is_skip_failed(self):
        return self._skip_failed

    def test_connection(self):
        # verify the proper url settings to configure this client
        if self._url[-4:] != '.com' and self._url[-4:] != '.net':
            print("Hostname should end in '.com'")
            return -1
        results = requests.get(self._url + '/api/2.0/clusters/spark-versions', headers=self._token,
                               verify=self._verify_ssl)
        http_status_code = results.status_code
        if http_status_code != 200:
            print("Error. Either the credentials have expired or the credentials don't have proper permissions.")
            print("If you have a ~/.netrc file, check those credentials. Those take precedence over passed input.")
            print(results.text)
            return -1
        return 0

    def get(self, endpoint, json_params=None, version='2.0', print_json=False):
        if version:
            ver = version
        full_endpoint = self._url + '/api/{0}'.format(ver) + endpoint
        if self.is_verbose():
            print("Get: {0}".format(full_endpoint))
        if json_params:
            raw_results = requests.get(full_endpoint, headers=self._token, params=json_params, verify=self._verify_ssl)
            http_status_code = raw_results.status_code
            if http_status_code in dbclient.http_error_codes:
                raise Exception("Error: GET request failed with code {}\n{}".format(http_status_code, raw_results.text))
            results = raw_results.json()
        else:
            raw_results = requests.get(full_endpoint, headers=self._token, verify=self._verify_ssl)
            http_status_code = raw_results.status_code
            if http_status_code in dbclient.http_error_codes:
                raise Exception("Error: GET request failed with code {}\n{}".format(http_status_code, raw_results.text))
            results = raw_results.json()
        if print_json:
            print(json.dumps(results, indent=4, sort_keys=True))
        if type(results) == list:
            results = {'elements': results}
        results['http_status_code'] = raw_results.status_code
        return results

    def http_req(self, http_type, endpoint, json_params, version='2.0', print_json=False, files_json=None):
        if version:
            ver = version
        full_endpoint = self._url + '/api/{0}'.format(ver) + endpoint
        if self.is_verbose():
            print("{0}: {1}".format(http_type, full_endpoint))
        if json_params:
            if http_type == 'post':
                if files_json:
                    raw_results = requests.post(full_endpoint, headers=self._token,
                                                data=json_params, files=files_json, verify=self._verify_ssl)
                else:
                    raw_results = requests.post(full_endpoint, headers=self._token,
                                                json=json_params, verify=self._verify_ssl)
            if http_type == 'put':
                raw_results = requests.put(full_endpoint, headers=self._token,
                                           json=json_params, verify=self._verify_ssl)
            if http_type == 'patch':
                raw_results = requests.patch(full_endpoint, headers=self._token,
                                             json=json_params, verify=self._verify_ssl)
                #print("patch")
                #print(raw_results)
            
            http_status_code = raw_results.status_code
            if http_status_code in dbclient.http_error_codes:
                raise Exception("Error: {0} request failed with code {1}\n{2}".format(http_type,
                                                                                      http_status_code,
                                                                                      raw_results.text))
            results = raw_results.json()
        else:
            print("Must have a payload in json_args param.")
            return {}
        if print_json:
            print(json.dumps(results, indent=4, sort_keys=True))
        # if results are empty, let's return the return status
        if results:
            results['http_status_code'] = raw_results.status_code
            return results
        else:
            return {'http_status_code': raw_results.status_code}

    def post(self, endpoint, json_params, version='2.0', print_json=False, files_json=None):
        return self.http_req('post', endpoint, json_params, version, print_json, files_json)

    def put(self, endpoint, json_params, version='2.0', print_json=False):
        #print("jso_param"+json_params)
        return self.http_req('put', endpoint, json_params, version, print_json)

    def patch(self, endpoint, json_params, version='2.0', print_json=False):
        print(json_params)
        return self.http_req('patch', endpoint, json_params, version, print_json)

    @staticmethod
    def my_map(F, items):
        to_return = []
        for elem in items:
            to_return.append(F(elem))
        return to_return

    def set_export_dir(self, dir_location):
        self._export_dir = dir_location

    def get_export_dir(self):
        return self._export_dir

    def get_latest_spark_version(self):
        versions = self.get('/clusters/spark-versions')['versions']
        v_sorted = sorted(versions, key=lambda i: i['key'], reverse=True)
        for x in v_sorted:
            img_type = x['key'].split('-')[1][0:5]
            if img_type == 'scala':
                return x


# COMMAND ----------

class migrateclient(dbclient):
    
    def get_num_defined_jobs(self):
      jobs_list = self.get('/jobs/list').get('jobs', [])
      return len(jobs_list)
    
    def get_list_jobs(self):
      jobs_list = self.get('/jobs/list').get('jobs', [])
      return (jobs_list)
    
    #clusters/list
    def get_cluster_list(self):
      clusters_list = self.get('/clusters/list').get('clusters', [])
      return (clusters_list)
    
    def get_cluster_DBR_versions(self):
      versions_list = self.get('/clusters/spark-versions').get('versions', [])
      return (versions_list)
    
    
    def get_num_external_jobs(self):
      job_runs = self.get('/jobs/runs/list').get('runs', [])
      job_ids_list = set(map(lambda x: x.get('job_id', None), self.get('/jobs/list').get('jobs', [])))
      job_ids_from_runs = set(map(lambda x: x.get('job_id', None), job_runs))
      ephemeral_job_ids = job_ids_from_runs - job_ids_list 
      return len(ephemeral_job_ids)
    
    def get_num_users(self):
      users = self.get('/preview/scim/v2/Users').get('Resources', [])
      return len(users)
    
    def get_num_groups(self):
      groups = self.get('/preview/scim/v2/Groups').get('Resources', [])
      return len(groups)
    
    #get Group id of Admin group
    def get_admin_group_id(self):
      groups = self.get('/preview/scim/v2/Groups?filter=displayName+eq+admins').get('Resources', [])
      return groups
    
      #get user id of needs to be added to 
    def get_user_id(self,useremail):
      users = self.get('/preview/scim/v2/Users?filter=userName+eq+'+useremail).get('Resources', [])
      return users
    
    def add_user_admingrp(self,userid,grpid):
      body={
              "schemas":[
                "urn:ietf:params:scim:api:messages:2.0:PatchOp"
              ],
              "Operations":[
                {
                "op":"add",
                "value":{
                    "members":[
                       {
                          "value":userid
                       }
                    ]
                  }
                }
              ]
            }
      #print('/api/2.0/preview/scim/v2/Groups/'+grpid)
      user=self.patch('/preview/scim/v2/Groups/'+grpid,json_params=body).get('members',[])
      #print(user)
      return user
    
    def get_num_notebooks(self, second_level=False):
      users = self.get('/preview/scim/v2/Users').get('Resources', [])
      total_nbs = 0 
      second_level_dirs = []
      for user in users:
        path = '/Users/' + user['userName']
        ls = self.get('/workspace/list', {'path' : path}).get('objects', [])
        nbs = list(filter(lambda x: x.get('object_type', None) == 'NOTEBOOK', ls))
        total_nbs += len(nbs) 
        dirs = list(filter(lambda x: x.get('object_type', None) == 'DIRECTORY', ls))
        for p in dirs:
          dir_path = p.get('path')
          ls_dir = self.get('/workspace/list', {'path' : dir_path}).get('objects', [])
          dir_nbs = list(filter(lambda x: x.get('object_type', None) == 'NOTEBOOK', ls_dir))
          second_level_dirs.extend(filter(lambda x: x.get('object_type', None) == 'DIRECTORY', ls_dir))
          total_nbs += len(dir_nbs) 
      # search 2 levels deep only to get an approximate notebook count
      if second_level:
        for p in second_level_dirs:
          dir_path = p.get('path')
          ls_dir = self.get('/workspace/list', {'path' : dir_path}).get('objects', [])
          dir_nbs = list(filter(lambda x: x.get('object_type', None) == 'NOTEBOOK', ls_dir))
          total_nbs += len(dir_nbs) 
      return total_nbs 
        
    def get_num_databases(self):
      dbs = spark.catalog.listDatabases()
      return len(dbs)
    
    def get_num_tables(self):
      dbs = spark.catalog.listDatabases()
      table_count = 0
      for db in dbs:
        tables = spark.catalog.listTables(db.name)
        table_count += len(tables)
      return table_count 
      

# COMMAND ----------

# MAGIC %md
# MAGIC ###Script to Audit DBR versions of all clusters in given enviornment ( Interactive as well as Automated/job clusters)

# COMMAND ----------


url = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiUrl().getOrElse(None) 
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().getOrElse(None)

client = migrateclient(token, url)

# COMMAND ----------

# this function adds user id to admin group
def add_user_to_admin_grp(useremail):
  admingrpid=client.get_admin_group_id()
  userid=client.get_user_id(useremail)
  userresult=client.add_user_admingrp(userid=userid[0]['id'],grpid=admingrpid[0]['id'])
  return userresult

# COMMAND ----------

#### pass email id of user who needs to added to admin group
res=add_user_to_admin_grp('***pass emaid id of user***') #pass userid to function here
print(res)