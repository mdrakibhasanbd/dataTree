from flask import Flask, render_template, request, redirect
from flask_cors import CORS
import pymongo
import json
import routeros_api
from typing import Iterator
app = Flask(__name__)
cors = CORS(app)

client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['device']
collections = db['data1']
# Create a separate collection to store the latest ID value
id_collection = db["counters"]
mydb = client['RealTimeTraffic']
collection = mydb.device.find_one({'_id': 1})


def routerdata() -> Iterator[str]:

    connection = routeros_api.RouterOsApiPool(collection['address'],
                                              port=int(collection['port']),
                                              username=collection['name'],
                                              password=collection['password'],
                                              plaintext_login=True
                                              )
    api = connection.get_api()
    # list_address =  api.get_resource('/ip/firewall/address-list')
    list_address = api.get_resource('/ppp/active')
    routerDatas = list_address.get()
    return routerDatas


def get_next_sequence_value(sequence_name):
    sequence_document = id_collection.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER
    )
    return sequence_document["sequence_value"]


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/tree")
def tree():

    treeDataFind = collections.find()
    routerDatas = routerdata()
    online = {"type":"#00ff00"}
    for routerData in routerDatas:

        routerClientData = routerData['name']
        dbDatas1 = collections.find({"name":routerClientData})
        for dbData in dbDatas1:
                # collections.update_one(dbData, {"$set": online}, upsert=True)
                collections.update_many(dbData, {"$set": online}, upsert=True)
                # print("online")


    data = []

    for i in treeDataFind:
        data.append(i)
        # print(data)

    id_mapping = {}
    for i, el in enumerate(data):
        id_mapping[el['_id']] = i

    root = None
    for el in data:
        # Handle the root element
        # if el['parentId'] is "null":
        if el['rootId'] is None:
            root = el
            continue
        # Use our mapping to locate the parent element in our data array
        parent_el = data[id_mapping[el['rootId']]]
        # Add our current el to its parent's `children` list
        parent_el['children'] = parent_el.get('children', []) + [el]

    jsn = json.dumps(root, indent=4)
    # print(jsn)

    return jsn


@app.route("/addSplitterNode", methods=['GET', 'POST'])
def addSplitterNode():
    if request.method == "POST":
        nodeName = request.form.get("name")
        nodeColour = request.form.get("nodeColour")
        nodeCore = int(request.form.get("nodeCore"))
        nodeId = int(request.form.get("nodeId"))

        # print(nodeName)
        # print(nodeColour)
        # print(type(nodeId))
        # print(nodeId)

        # Create a function to generate the next ID value

        colour = {2: ['blue', 'orange'],
                  4: ['blue', 'orange', 'green', 'brown'],
                  8: ['blue', 'orange', 'green', 'brown', 'grey', 'white', 'red', 'black'],
                  16: ['blue', 'orange', 'green', 'brown', 'grey', 'white', 'red', 'black',
                       'blue', 'orange', 'green', 'brown', 'grey', 'white', 'red', 'black']}

        Port = {2: ["PORT-1", "PORT-2"],
                4: ["PORT-1", "PORT-2", "PORT-3", "PORT-4", ],
                8: ["PORT-1", "PORT-2", "PORT-3", "PORT-4", "PORT-5", "PORT-6", "PORT-7", "PORT-8"],
                16: ["PORT-1", "PORT-2", "PORT-3", "PORT-4", "PORT-5", "PORT-6", "PORT-7", "PORT-8",
                     "PORT-9", "PORT-10", "PORT-11", "PORT-12", "PORT-13", "PORT-14", "PORT-15", "PORT-16"]}

        # select the document you want to update
        myquery = {"_id": nodeId}
        myquery = collections.find_one(myquery)
        nodetype = myquery["nodetype"]
        ponname = myquery["addedName"]
        print(nodetype)
        if nodetype == "pon":
            print("ponSplitter")

            # set the new field value using $set
            ponValue = {"name": ponname, "icon": "static/image/pon.png",
                        "value": None, "searchable": None}

            collections.update_one(myquery, {"$set": ponValue}, upsert=True)
            collections.insert_one(
                {
                    "_id": get_next_sequence_value("my_collection_id"),
                    "rootId": nodeId,
                    "name": nodeName,
                    "addedName": nodeName,
                    "level": nodeColour,
                    "value": None,
                    "nodetype": "firstPlc",
                    "icon": "static/image/splitter.png",
                    "searchable": "YES"
                }
            )
            datafind = {"name": nodeName}
            myquery = collections.find_one(datafind)
            parrentNodeId = myquery["_id"]
            print(parrentNodeId)
            for i, (item1, item2) in enumerate(zip(colour[nodeCore], Port[nodeCore])):
                collections.insert_one(
                    {
                        "_id": get_next_sequence_value("my_collection_id"),
                        "rootId": parrentNodeId,
                        "name": item2,
                        "addedName": item2,
                        "level": item1,
                        "value": 8,
                        "nodetype": "core"
                    }
                )

        elif nodetype == "core":
            print("coreSplitter")
            # set the new field value using $set
            splitterValue = {"name": nodeName, "icon": "static/image/splitter.png",
                             "value": None, "nodetype": "splitter", "searchable": "YES"}

            collections.update_one(
                myquery, {"$set": splitterValue}, upsert=True)

            for i, (item1, item2) in enumerate(zip(colour[nodeCore], Port[nodeCore])):
                collections.insert_one(
                    {
                        "_id": get_next_sequence_value("my_collection_id"),
                        "rootId": nodeId,
                        "name": item2,
                        "addedName": item2,
                        "level": item1,
                        "value": 8,
                        "nodetype": "core"
                    }
                )

    return redirect("/")


@app.route("/addUserNode", methods=['GET', 'POST'])
def addUserNode():
    if request.method == "POST":
        nodeName = request.form.get("name")
        nodeId = int(request.form.get("userId"))
        print(nodeName)
        print(type(nodeId))
        print(nodeId)
        datafind = {"_id": nodeId}
        myquery = collections.find_one(datafind)
        userCoreColour = myquery["level"]
        print(userCoreColour)

        collections.insert_one(
            {
                "_id": get_next_sequence_value("my_collection_id"),
                "rootId": nodeId,
                "name": nodeName,
                "addedName": nodeName,
                "value": 8,
                "searchable": "YES",
                "type": "red",
                "icon": "static/image/router.png",
                "level": userCoreColour,
                "nodetype": "user"
            }
        )
    return redirect("/")


@app.route('/check', methods=['POST'])
def check_document():
    value = request.form['name']
    query = {'name': value}
    result = collections.find_one(query)
    if result:

        message = "<span style='color:red;'>Name already exists!</span>"

        return message
    else:
        message = "Name Available"

        return message


@app.route("/renameNode", methods=['GET', 'POST'])
def node_rename():
    if request.method == "POST":
        nodeName = request.form.get("name")
        nodeId = int(request.form.get("nodeId2"))
        print(nodeId)
        print(type(nodeId))
        print(nodeName)
        myquery = {"_id": nodeId}

        # set the new field value using $set
        newValue = {"name": nodeName, "type": "red"}
        collections.update_one(myquery, {"$set": newValue}, upsert=True)

    return redirect("/")


@app.route('/delete/<string:delete_id>', methods=['POST'])
def delete_item(delete_id):
    form_delete_id = int(request.form['delete_id'])
    print(form_delete_id)
    # select the document you want to update
    datafind = {"_id": form_delete_id}
    deleteNodefind = {'rootId': form_delete_id}
    myquery = collections.find_one(datafind)
    oldName = myquery["addedName"]
    nodetype = myquery["nodetype"]

    if nodetype == "user":
        print(nodetype)
        collections.delete_one(datafind)

    elif nodetype == "firstPlc":
        # print(nodetype)

        collections.delete_one(datafind)
        collections.delete_many(deleteNodefind)

        # return {"mes":"notdeleableNode"}
    elif nodetype == "core":
        # print(nodetype)

        return {"mes": "notdeleableCoreNode"}

    else:

        print(nodetype)

        # set the new field value using $set
        newValue = {"name": oldName, "icon": None, "value": 8, "searchable": None,
                    "type": None, "icon": None,  "level": None, "nodetype": "core"}
        collections.update_one(myquery, {"$set": newValue}, upsert=True)

        # # your code to delete the item from MongoDB here
        # collections.update_many(deleteNodefind, {"$set": deleteNodeValue}, upsert=True)
        collections.delete_many(deleteNodefind)

    # return ({"status":"200"})
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True, port=5008, host='0.0.0.0')
