import git
import json
import os
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from pydriller import Repository


class Miner():
    def __init__(self, rl, vl) -> None:
        self.version_list = vl
        self.local_repo_link = rl
    
    # extracting commits between the starting version to ending version using 
    # gitpython and local data
    def getCommitsList(self,ft,tt):
        repo = git.Repo(self.local_repo_link)

        commits = []
    
        tag1_obj = repo.tags[ft]
        tag2_obj = repo.tags[tt]

        # Iterate over commits between the two tags
        for commit in repo.iter_commits(rev=f"{tag1_obj}..{tag2_obj}"):
            commits.append(commit.hexsha)
        
        return commits

    # going through each commit and analyzing each file being affected in 
    # that commit
    def mineClasses(self):
        for i in range(1,len(self.version_list)):
            
            classes_data = {}

            from_tag = self.version_list[i-1]
            to_tag = self.version_list[i]
            
            commits_list = self.getCommitsList(from_tag,to_tag)

            # iterating over commit list
            for c_hash in commits_list:

                for c in Repository(self.local_repo_link, single=c_hash).traverse_commits():
                    # iterating over each files being impacted
                    for file in c.modified_files:
                        class_name = file.filename
                        if class_name.find(".java") != -1:
                            pattern = r'\bPDFBOX-\d+\b' # regular expression to extract the IssueIds from the commit message
                            issues = re.findall(pattern, c.msg)
                            counter = 0
                            for i in issues:
                                #  checking the mapped issue is buggy or not
                                if self.checkBuggy(i) :
                                    counter+=1

                            if class_name not in classes_data:
                                classes_data[class_name] = counter
                            else:
                                classes_data[class_name]+=1            
          
            # storing the data into json file so it can be processed efficiently
            file_name = f"{from_tag}-{to_tag}_classes.json"
            self.storeClassesToJson(file_name, classes_data)

    # function checks whether the issue mapped with commit is buggy or not using
    # beautifulsoup 
    def checkBuggy(self,issueId):
        url = f"https://issues.apache.org/jira/browse/{issueId}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        typed_value = soup.find(id='type-val').get_text()
        return typed_value.strip() == "Bug"

    # by analyzing json files data generating csv file
    def generateCSV(self, columns):
        for i in range(1,len(self.version_list)):
            f = open(f"./Data/ExtractedClasses/{self.version_list[i-1]}-{self.version_list[i]}_classes.json")
            commit_data = json.load(f)
            df = pd.read_excel(f"./Data/ClassMetrics/{self.version_list[i]}.xlsx")
            data = {}
            for c in columns:
                data[c] = []
            data["IsBuggy"] = []
            df = df[columns]
            for index,row in df.iterrows():
                class_name = f'{row["Name"]}.java' 
                if class_name in commit_data:
                    data["IsBuggy"].append(1 if commit_data[class_name] > 0 else 0)
                    row[columns[0]] = f"{row[columns[0]]}"
                    for key in data.keys():
                        if key != "IsBuggy":
                            data[key].append(row[key])     
            file_name = "training_data.csv" 
            data_df = pd.DataFrame(data)
            self.storeDataToCSV(file_name,data_df)  

    # storing the dictionary data to json file
    def storeClassesToJson(self,fileName, data):
        dir = "./Data/ExtractedClasses"
        os.makedirs(dir, exist_ok=True)
        file_path = os.path.join(dir, fileName)
        with open(file_path, "w") as outfile: 
            json.dump(data, outfile)
    
    # storing the analyzed data to CSV file as training data
    def storeDataToCSV(self, fileName, df):
        dir = "./Data/TrainingData"
        os.makedirs(dir, exist_ok=True)
        file_path = os.path.join(dir, fileName)
        df.to_csv(file_path, mode="a", index=False)
    

# creating object of miner using local cloned repository and version needs to
# be mined
miner = Miner("/Users/dhairyapatel/Documents/pdfbox",['2.0.25','2.0.26','2.0.27','2.0.28','2.0.29','2.0.30','2.0.31'])

# it will mine classes and will generate json files
miner.mineClasses()

# using json files, generate csv file on the mentioned attributes(columns)
miner.generateCSV(["Name","WMC","LCOM","DIT","CBO","RFC","LCAM","LOC"])



