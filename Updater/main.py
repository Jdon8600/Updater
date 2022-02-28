# --------------------------- IMPORTS --------------------------- #
from asyncio.windows_events import proactor_events
from datetime import datetime
import os
import urllib
from flask import Blueprint, request, session, redirect, render_template, flash
from markupsafe import re
import requests
import requests.auth
from dotenv import load_dotenv
import json


session = {}
session['bool'] = False
# loads the environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
OAUTH_URL = os.getenv("OAUTH_URL")
BASE_URL = os.getenv("BASE_URL")



def gen_secret_key():
    """
    DESCRIPTION:
        Generates SECRET_KEY, used for existence session variables
    INPUT:
        N/A
    OUTPUT:
        return = randomly generated SECRET_KEY
    """
    return os.urandom(16)


def make_authorization_url():
    '''
    DESCRIPTION:
        Creates the authorization URL to obtain the authorization code from Procore.
    INPUTS:
        N/A
    OUTPUTS:
        url: the url used to obtain the authorization code from the application.
        '''
    # Generate a random string for the state parameter
    # Save it for use later to prevent xsrf attacks
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI
    }
    url = OAUTH_URL + "/authorize?" + urllib.parse.urlencode(params)
    return url


def update_date(created_at):
    '''
    DESCRIPTION:
        Turns unix time stamp into human readable time for the expire_date.Takes in unix created_at
            time value and adds 7200 (2 hours) to the created_at value before converting time.
    INPUTS:
        created_at = the unix date and time of the authorization token creation.
    OUTPUT:
        return     = returns the created_at unix date/time in a human-readable format
        '''
    return datetime.utcfromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')


def update_expire(created_at):
    '''
    DESCRIPTION:
        Turns unix time stamp into human readable time for the expire_date.Takes in unix created_at
            time value and adds 7200 (2 hours) to the created_at value before converting time.
    INPUTS:
        created_at = the unix date and time of the authorization token creation.
    OUTPUT:
        return     = returns the expires_at unix date/time in a human-readable format.
        '''
    return datetime.utcfromtimestamp(created_at+7200).strftime('%Y-%m-%d %H:%M:%S')



def get_token(code):
    """
    DESCRIPTION:
        Gets the access token by utilizating the authorization code that was
        previously obtained from the authorization_url call.
    INPUTS:
        code = authorization code
        OUTPUTS:
        response_json["access_token"]  = user's current access token
        response_json["refresh_token"] = user's current refresh token
        response_json['created_at']    = the date and time the user's access
        token was generated
    """

    client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    post_data = {"grant_type": "authorization_code",
                 "code": code,
                 "redirect_uri": REDIRECT_URI
                 }
    response = requests.post(BASE_URL+"/oauth/token",
                             auth=client_auth,
                             data=post_data)
    response_json = response.json()
    return response_json['access_token'], response_json['refresh_token'], response_json['created_at']


def get_company_id(access_token):
    """
    DESCRIPTION:
        Calls /rest/v1.0/companies and returns the name of the company
    Inputs:
        access_token
    OutPuts:
    company_json['id']
    """
    headers = {"Authorization": "Bearer " + access_token}
    response = requests.get(BASE_URL+"/rest/v1.0/companies", headers=headers)
    company_json = response.json()
    session['company_id'] = company_json[0]['id']
    return company_json[0]['id']

"""def get_checklist_template(access_token, project_id):
    headers = {"Authorization": "Bearer " + access_token}
    response = requests.get(
        BASE_URL+f"/rest/v1.0/projects/{project_id}/checklist/list_templates", headers=headers)
    checklist_template = response.json()
    return checklist_template
"""

def get_checklist_json(access_token, project_id, filters=[]):
    headers = {"Authorization": "Bearer " + access_token}
    response = requests.get(
        BASE_URL+f"/rest/v1.0/projects/{project_id}/checklist/lists?per_page=4000&filters%5Blocation_id%5D={filters}", headers=headers)
    checklist_json = response.json()
    return checklist_json


def get_item_id(list_id):
    project_id = session.get('project_id')
    access_token = session.get('access_token')
    data = {"project_id": project_id}
    headers = {"Authorization": "Bearer " + access_token}
    response = requests.get(
        BASE_URL+f"/rest/v1.0/checklist/lists/{list_id}", data=data, headers=headers)
    to_json = response.json()
    section_json = to_json['sections']
    
    item_json = section_json[0]['items']
    value_id = [a_id['id'] for a_id in item_json]
    value_pos = [a_pos['position'] for a_pos in item_json]
    section_id = [a_sID["section_id"] for a_sID in item_json]
    session['itemPos'] = value_pos
    session['section_id'] = section_id
  
    return value_id

def update(result1, project_id, section_id, list_id, item_id, status, headers):

    if result1[0] != '':
                    for num in result1:
                        target_pos = num
                        target = int(target_pos)
                        
                        data = {
                                "project_id": project_id,
                                "section_id": section_id[target-1],
                                "item": {
                                    "position": target,
                                    "status": status,
                                    "response_id": None,
                                    "item_attachments_attributes": [
                                
                                    ]
                                },
                                "attachments": [
                                ]
                            }
                        json_data = json.dumps(data)
                        resp = requests.patch(
                            BASE_URL+f'/rest/v1.0/checklist/lists/{list_id}/items/{item_id[target-1]}', data=json_data, headers=headers)

                        print(resp.status_code)

def get_me(access_token):
    '''
    DESCRIPTION:
        Calls /rest/v1.0/me endpoint and returns user login/id.
    INPUTS:
        access_token =  access_token used as credentials to communicate with the API
    OUTPUTS:
        me_json['login'] = user's login name
        me_json['id']    = user's login ID
        '''
    headers = {"Authorization": "Bearer " + access_token}
    response = requests.get(BASE_URL+"/rest/v1.0/me", headers=headers)
    me_json = response.json()
    return me_json['login']


def callback():
    if request.method == "GET":
        if session.get('bool') is False:
            code = request.args.get('code')
            access_token, refresh_token = get_token(code)
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            session['bool'] = True
 
        return render_template('home.html')

#-------------------------------------------------App ROUTES-------------------------------------------------------------------------------#


bp = Blueprint('main', __name__, url_prefix='/')
bp.secret_key = gen_secret_key()


@bp.route('/', methods=["GET", "POST"])
def app_homepage():
    return render_template('auth/login.html')

# authenticates user via procore


@bp.route('/get_auth', methods=['POST'])
def app_auth():
    return redirect(make_authorization_url())


@bp.route('user/home', methods=['POST', 'GET'])
def app_callback():
    if request.method == "GET":
        if session.get('bool') is False:
            code = request.args.get('code')
            access_token, refresh_token, created_at = get_token(code)
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            session['created_at'] = update_date(created_at)
            session['expires_at'] = update_expire(created_at)
            session['bool'] = True
    login = get_me(session.get('access_token'))
    session['login'] = login

    return render_template('home.html', user=login)

# show the projects visible to the user logged in


@bp.route('user/projects', methods=['GET', "POST"])
def show_my_projects():
    if request.method == "GET":
        companyID = get_company_id(session.get('access_token'))
        data = {"company_id": companyID} 
        headers = {"Authorization": "Bearer " + session.get('access_token')}
        response = requests.get(
            BASE_URL + '/rest/v1.0/projects', data=data, headers=headers)
        projectJson = response.json()
        session['project_json'] = projectJson
        projectName = "name"
        value_name = [a_name[projectName] for a_name in projectJson]
        return render_template('projects.html', projectName=value_name, user=session.get('login'))
    result = request.form.get("projectName")
    session["projectName"] = result
    my_json = session.get('project_json')
    result_index = next((index for (index, d) in enumerate(
        my_json) if d['name'] == result), None)
    project_id = my_json[result_index]['id']
    session['project_id'] = project_id

    return redirect('/search')
@bp.route('/search', methods=["GET", "POST"])
def get_search():
    projectName = session.get('projectName')
    if request.method == "POST":
        result = request.form.get("Search")
        session['search_result'] = result.lower()
        return redirect('/selectIns')
    return render_template('search.html', projectName=projectName, user=session.get('login'))


@bp.route('/selectIns', methods=["GET", "POST"])
def get_inspection():
    projectName = session.get("projectName")
    access_token = session.get('access_token')
    project_id = session .get('project_id')
    if request.method == "GET":
        check_json = get_checklist_json(access_token, project_id)
        session['checklist_json'] = check_json
        search_result = session.get('search_result')
        template_location = "location"
        value_location = [a_name[template_location] for a_name in check_json]
        session['value_location'] = value_location
        value_node = []
        value_id = []
        counter = 0
        for i in range(len(value_location)):
            if value_location[i] != None:
                value_location[i]['node_name'] = value_location[i]['node_name'].lower()
        for i in range(len(value_location)):
            if value_location[i] != None:
                value_node.append(value_location[i]['node_name'])
            else:
                continue
        matching = [s for s in value_node if search_result in s]
        
        for i in range(len(value_location)):
            if(counter < len(matching)):
                if value_location[i] != None and value_location[i]['node_name']  == matching[counter]:
                    value_id.append(value_location[i]['id'])
                    counter += 1
                else:
                    continue
                
            if counter == len(value_location):
                counter = 0

        session['value_id'] = value_id
        

        return render_template('selection.html', templateName=matching, projectName=projectName, user=session.get('login'))

    
    value_id = session.get('value_id')
    loc_checklist = get_checklist_json(access_token, project_id, value_id)
    result = request.form.getlist('templateName')
    list_id = []
    counter = 0
    for i in range(len(loc_checklist)):
        if loc_checklist[i] != None:
            loc_checklist[i]['location']['node_name'] = loc_checklist[i]['location']['node_name'].lower()
    for i in range(len(loc_checklist)):
        if(counter < len(result)):
            if loc_checklist[i]['location']['node_name'] == result[counter]:
                list_id.append(loc_checklist[i]['id'])
                counter += 1
            else:
                continue
        if counter == len(result):
                counter = 0
                
    session['list_id'] = list_id
    return redirect('/update')


@bp.route('/update', methods=['GET', 'POST'])
def update_ins():
    if request.method == "POST":
        list_id = session.get('list_id')
        statPass = request.form['Pass']
        statFail = request.form['Fail']
        statNa = request.form['N/A']
        result1 = statPass.split(',')
        result2 = statFail.split(',')
        result3 = statNa.split(',')
        access_token = session.get('access_token')
        project_id = int(session.get("project_id"))
        Pass = "yes"
        Fail = "no"
        Not_A = "n/a"
    
        
        headers = {"Authorization": "Bearer " + access_token, 'content-type': 'application/json'
        }

        for i in range(len(list_id)):
            item_id = get_item_id(list_id[i])
            section_id = session.get('section_id')
            
            update(result1, project_id, section_id, list_id[i], item_id, Pass, headers)
            update(result2, project_id, section_id, list_id[i], item_id, Fail, headers)
            update(result3, project_id, section_id, list_id[i], item_id, Not_A, headers)

    
        
        return render_template("fin.html")
    return render_template("update.html")

@bp.route('/refreshToken', methods=['POST'])
def app_refresh_token():
    access_token = session.get('access_token')
    refresh_token = session.get('refresh_token')
    headers = {"Authorization": "Bearer " + access_token}
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "redirect_uri": REDIRECT_URI,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token
    }

    response = requests.post(BASE_URL + '/oauth/token',
                             data=data, headers=headers)
    response_json = response.json()
    session['access_token'] = response_json["access_token"]
    session['refresh_token'] = response_json["refresh_token"]
    return redirect('user/home')


@bp.route('/logout', methods=["POST"])
def logout():
    access_token = session.get('access_token')
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "token": access_token
        }
    requests.post(BASE_URL+'/oauth/revoke', data=data)
    session.clear()
    session['bool'] = False
    return redirect('/')
    